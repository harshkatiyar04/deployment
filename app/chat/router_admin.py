from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, cast, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from typing import List, Optional
from datetime import datetime, timezone
from uuid import UUID

from app.db.session import get_db
from app.chat.models import ChatBan, ChatChannel, ChatMessage, GamifiedPersona, SOSReport, AdminAccessLog
from app.chat.access_control import set_admin_audit_actor
from app.core.admin_deps import require_admin_api_key, resolve_admin_actor_id
from app.chat.services import manager
from app.chat.schemas import (
    BanCreate,
    BanResponse,
    BanListResponse,
    ActivityResponse,
    WarnedMessageOut,
    SOSReportOut,
    AdminRecentMessageOut,
)

router = APIRouter(
    prefix="/admin/chat",
    tags=["admin_chat"],
    dependencies=[Depends(require_admin_api_key)],
)


@router.post("/bans", response_model=BanResponse, status_code=status.HTTP_201_CREATED)
async def create_ban(
    data: BanCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Ban a user from a specific circle. Supports UUID or Email as identifier.
    Audit trigger will automatically log this action.
    """
    admin_id = await resolve_admin_actor_id(db)
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

    await set_admin_audit_actor(db, admin_id)

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
async def list_bans(db: AsyncSession = Depends(get_db)):
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
    db: AsyncSession = Depends(get_db),
):
    """
    Revoke a ban by its ID.
    Audit trigger will log this DELETE.
    """
    admin_id = await resolve_admin_actor_id(db)
    res = await db.execute(select(ChatBan).where(ChatBan.id == ban_id))
    ban = res.scalar_one_or_none()

    if not ban:
        raise HTTPException(status_code=404, detail="Ban not found")

    await set_admin_audit_actor(db, admin_id)
    await db.delete(ban)
    await db.commit()

    return None


@router.get("/activity", response_model=List[ActivityResponse])
async def list_activity(db: AsyncSession = Depends(get_db)):
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


@router.get("/sos-reports", response_model=List[SOSReportOut])
async def list_sos_reports(db: AsyncSession = Depends(get_db)):
    """Return unresolved SOS reports for the admin dashboard."""
    SenderPersona = aliased(GamifiedPersona)
    ReporterPersona = aliased(GamifiedPersona)

    result = await db.execute(
        select(SOSReport, ChatMessage, SenderPersona, ChatChannel, ReporterPersona)
        .join(ChatMessage, SOSReport.message_id == ChatMessage.id)
        .join(
            SenderPersona,
            ChatMessage.gamified_persona_id == SenderPersona.id,
            isouter=True,
        )
        .join(ChatChannel, ChatMessage.channel_id == ChatChannel.id)
        .join(
            ReporterPersona,
            SOSReport.reporter_persona_id == ReporterPersona.id,
            isouter=True,
        )
        .where(SOSReport.resolved_at.is_(None))
        .order_by(SOSReport.created_at.desc())
    )
    rows = result.all()

    output = []
    for sos, msg, sender, channel, reporter in rows:
        output.append(
            SOSReportOut(
                id=sos.id,
                message_id=sos.message_id,
                reporter_persona_id=sos.reporter_persona_id,
                reporter_nickname=reporter.nickname if reporter else "Unknown Reporter",
                hidden_at=sos.hidden_at,
                admin_notified_at=sos.admin_notified_at,
                resolved_at=sos.resolved_at,
                notes=sos.notes,
                created_at=sos.created_at,
                message_content=msg.content_text,
                media_url=msg.media_url,
                sender_user_id=sender.user_id if sender else None,
                sender_nickname=sender.nickname if sender else "Unknown Sender",
                circle_id=channel.circle_id,
            )
        )
    return output


@router.patch("/sos-reports/{report_id}/resolve")
async def resolve_sos_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Mark an SOS report as resolved."""
    admin_id = await resolve_admin_actor_id(db)
    result = await db.execute(select(SOSReport).where(SOSReport.id == report_id))
    report = result.scalar_one_or_none()
    if report is None:
        raise HTTPException(status_code=404, detail="SOS report not found")

    report.resolved_at = datetime.now(timezone.utc)

    log = AdminAccessLog(
        admin_id=admin_id,
        action="RESOLVE_REPORT",
        target_table="sos_reports",
        target_id=str(report_id),
        changes_json={"resolved": True},
    )
    db.add(log)
    await db.commit()
    return {"id": report_id, "resolved_at": report.resolved_at.isoformat()}


@router.get("/circles/{circle_id}/recent-messages", response_model=List[AdminRecentMessageOut])
async def circle_recent_messages(
    circle_id: str,
    limit: int = 3,
    db: AsyncSession = Depends(get_db),
):
    """Last N chat messages in a circle (all channels) for admin ban context."""
    cap = max(1, min(limit, 10))
    stmt = (
        select(ChatMessage, ChatChannel, GamifiedPersona)
        .join(ChatChannel, ChatMessage.channel_id == ChatChannel.id)
        .join(
            GamifiedPersona,
            ChatMessage.gamified_persona_id == GamifiedPersona.id,
            isouter=True,
        )
        .where(
            ChatChannel.circle_id == circle_id,
            ChatMessage.hidden_at.is_(None),
            ChatMessage.deleted_at.is_(None),
        )
        .order_by(ChatMessage.created_at.desc())
        .limit(cap)
    )
    res = await db.execute(stmt)
    rows = res.all()
    out: list[AdminRecentMessageOut] = []
    for msg, channel, persona in rows:
        out.append(
            AdminRecentMessageOut(
                id=str(msg.id),
                channel_name=channel.name or "general",
                sender_nickname=persona.nickname if persona else "Unknown",
                sender_user_id=str(persona.user_id) if persona and persona.user_id else None,
                content_text=msg.content_text,
                created_at=msg.created_at,
            )
        )
    return out


@router.get("/warned-messages", response_model=List[WarnedMessageOut])
async def list_warned_messages(db: AsyncSession = Depends(get_db)):
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
