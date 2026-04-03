from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, text, cast, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime
from uuid import UUID

from app.db.session import get_db
from app.chat.models import ChatBan
from app.core.jwt_auth import get_current_user
from app.chat.services import manager
from app.chat.schemas import BanCreate, BanResponse, BanListResponse, ActivityResponse, WarnedMessageOut

router = APIRouter(prefix="/admin/chat", tags=["admin_chat"])


@router.post("/bans", response_model=BanResponse, status_code=status.HTTP_201_CREATED)
async def create_ban(
    data: BanCreate,
    admin_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Ban a user from a specific circle. Supports UUID or Email as identifier.
    Audit trigger will automatically log this action.
    """
    admin_id = admin_user.id
    target_user_id = None
    target_email = None

    # Resolve user identifier
    try:
        # Try if it's a valid UUID
        target_user_id = str(UUID(data.user_identifier))
    except ValueError:
        # Handle as email
        target_email = data.user_identifier
        from app.models.signup import SignupRequest  # noqa: PLC0415

        user_res = await db.execute(
            select(SignupRequest).where(SignupRequest.email == target_email)
        )
        user_obj = user_res.scalar_one_or_none()
        if not user_obj:
            raise HTTPException(
                status_code=404, detail=f"User with email '{target_email}' not found"
            )
        target_user_id = user_obj.id
        target_email = user_obj.email

    # Check existing
    existing = await db.execute(
        select(ChatBan).where(
            ChatBan.circle_id == str(data.circle_id), ChatBan.user_id == target_user_id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="User is already banned from this circle"
        )

    await db.execute(text(f"SET LOCAL zenk.current_admin_id = '{admin_id}';"))

    ban = ChatBan(
        circle_id=str(data.circle_id),
        user_id=target_user_id,
        banned_by_admin_id=admin_id,
        reason=data.reason,
        reported_message_content=data.reported_message_content,
    )
    db.add(ban)
    await db.commit()
    await db.refresh(ban)

    await manager.kick_user(str(data.circle_id), target_user_id, data.reason)

    # Attach email for response
    ban_dict = {c.name: getattr(ban, c.name) for c in ban.__table__.columns}
    if not target_email:
        from app.models.signup import SignupRequest  # noqa: PLC0415

        user_res = await db.execute(
            select(SignupRequest).where(SignupRequest.id == target_user_id)
        )
        user_obj = user_res.scalar_one_or_none()
        target_email = user_obj.email if user_obj else None

    ban_dict["user_email"] = target_email
    return BanResponse(**ban_dict)


@router.get("/bans", response_model=BanListResponse)
async def list_bans(
    admin_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """List all active chat bans with joined user emails."""
    from app.models.signup import SignupRequest  # noqa: PLC0415

    stmt = select(ChatBan, SignupRequest.email).join(
        SignupRequest, ChatBan.user_id == SignupRequest.id, isouter=True
    )
    res = await db.execute(stmt)

    bans_out = []
    for ban, email in res.all():
        ban_dict = {c.name: getattr(ban, c.name) for c in ban.__table__.columns}
        ban_dict["user_email"] = email
        bans_out.append(BanResponse(**ban_dict))

    return BanListResponse(bans=bans_out)


@router.delete("/bans/{ban_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_ban(
    ban_id: str,
    admin_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Revoke a ban by its ID.
    Audit trigger will log this DELETE.
    """
    admin_id = admin_user.id
    res = await db.execute(select(ChatBan).where(ChatBan.id == ban_id))
    ban = res.scalar_one_or_none()

    if not ban:
        raise HTTPException(status_code=404, detail="Ban not found")

    await db.execute(text(f"SET LOCAL zenk.current_admin_id = '{admin_id}';"))
    await db.delete(ban)
    await db.commit()

    return None


@router.get("/activity", response_model=List[ActivityResponse])
async def list_activity(
    admin_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Fetch the latest 50 admin audit logs."""
    from app.chat.models import AdminAccessLog
    from app.models.signup import SignupRequest

    stmt = (
        select(AdminAccessLog, SignupRequest.email)
        .join(
            SignupRequest,
            AdminAccessLog.admin_id == cast(SignupRequest.id, String),
            isouter=True,
        )
        .order_by(AdminAccessLog.created_at.desc())
        .limit(50)
    )
    res = await db.execute(stmt)

    out = []
    for log, email in res.all():
        out.append(ActivityResponse(
            id=log.id,
            admin_id=log.admin_id,
            admin_email=email,
            action=log.action,
            target_table=log.target_table,
            target_id=log.target_id,
            changes_json=log.changes_json,
            created_at=log.created_at
        ))
    return out


@router.get("/warned-messages", response_model=List[WarnedMessageOut])
async def list_warned_messages(
    admin_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Fetch recent messages that were warned/flagged by the AI shield."""
    from app.chat.models import ChatMessage, GamifiedPersona, ChatChannel

    stmt = (
        select(ChatMessage, GamifiedPersona, ChatChannel)
        .join(GamifiedPersona, ChatMessage.gamified_persona_id == GamifiedPersona.id, isouter=True)
        .join(ChatChannel, ChatMessage.channel_id == ChatChannel.id)
        .where(ChatMessage.shield_action == 'warn')
        .order_by(ChatMessage.created_at.desc())
        .limit(50)
    )
    res = await db.execute(stmt)

    out = []
    for msg, persona, channel in res.all():
        out.append(WarnedMessageOut(
            id=str(msg.id),
            channel_id=str(msg.channel_id),
            gamified_persona_id=str(msg.gamified_persona_id),
            persona_nickname=persona.nickname if persona else "Unknown",
            content_text=msg.content_text,
            media_url=msg.media_url,
            shield_reason=msg.shield_reason,
            created_at=msg.created_at,
            sender_user_id=str(persona.user_id) if persona else None,
            circle_id=str(channel.circle_id)
        ))
    return out
