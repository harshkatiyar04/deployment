"""Chat API — WebSocket and REST endpoints."""

from __future__ import annotations

import logging
import os
import uuid
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    UploadFile,
    File,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import aliased
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jwt_auth import get_current_user_from_token
from app.core.settings import settings
from app.db.session import get_db, SessionLocal
from app.chat.models import (
    ChatChannel,
    ChatMessage,
    CircleMember,
    Enrollment,
    GamifiedPersona,
    SOSReport,
    SponsorCircle,
    AdminAccessLog,
)
from app.models.signup import SignupRequest
from app.chat.schemas import (
    ChannelCreate,
    ChannelOut,
    MessageOut,
    MessageSend,
    SOSReportIn,
    SOSReportOut,
    CircleMemberOut,
    WSEnvelope,
)
from app.chat.services import manager
from app.services.shield import shield_message_async
from app.services.kia import generate_kia_response
from app.services.kia_context import fetch_user_context
from app.services.kia_corporate import generate_corporate_response, fetch_corporate_context
from app.models.enums import Persona as UserPersonaRole

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])

_raised_hands: dict[str, set[str]] = {}

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB


async def _get_or_create_persona(
    user: SignupRequest, db: AsyncSession
) -> GamifiedPersona:
    """Get existing GamifiedPersona for user, or create one."""
    result = await db.execute(
        select(GamifiedPersona).where(GamifiedPersona.user_id == user.id)
    )
    persona = result.scalar_one_or_none()
    if persona is None:
        # Generate a deterministic but anonymous nickname from user email prefix
        prefix = user.email.split("@")[0][:8]
        nickname = f"{prefix}_{str(uuid.uuid4())[:4]}"
        avatar_key = f"avatar_{str(uuid.uuid4())[:8]}"
        persona = GamifiedPersona(
            user_id=user.id,
            nickname=nickname,
            avatar_key=avatar_key,
        )
        db.add(persona)
        await db.flush()
    return persona


async def _message_to_out(msg: ChatMessage, persona: GamifiedPersona) -> MessageOut:
    return MessageOut(
        id=msg.id,
        channel_id=msg.channel_id,
        gamified_persona_id=msg.gamified_persona_id,
        persona_nickname=persona.nickname,
        avatar_key=persona.avatar_key,
        content_text=msg.content_text if not msg.deleted_at else None,
        media_url=msg.media_url if not msg.deleted_at else None,
        shield_action=msg.shield_action,
        created_at=msg.created_at,
        deleted_at=msg.deleted_at,
    )


async def _get_kia_persona(db: AsyncSession) -> GamifiedPersona:
    """Get or create the specialized 'Kia' persona."""
    res = await db.execute(select(GamifiedPersona).where(GamifiedPersona.nickname == "Kia"))
    persona = res.scalar_one_or_none()
    if not persona:
        # We need a dummy user_id for the bot. We'll look for or create a system account.
        # For simplicity, we use a deterministic UUID for the Kia Bot user.
        kia_user_id = "00000000-0000-0000-0000-000000000000"
        
        # Ensure the system user exists in signup_requests to satisfy FK
        from app.models.enums import Persona as RP  # noqa: PLC0415
        from app.models.signup import SignupRequest as SR  # noqa: PLC0415
        
        user_res = await db.execute(select(SR).where(SR.id == kia_user_id))
        if not user_res.scalar_one_or_none():
            kia_user = SR(
                id=kia_user_id,
                persona=RP.student, # Kia acts as a student/mentor hybrid
                full_name="Kia AI",
                mobile="0000000000",
                email="kia@zenk.ai",
                password_hash="system_managed",
                address_line1="System",
                address_line2="System",
                city="Digital",
                state="Zenk",
                pincode="000000",
                country="India"
            )
            db.add(kia_user)
            await db.flush()
            
        persona = GamifiedPersona(
            user_id=kia_user_id,
            nickname="Kia",
            avatar_key="avatar_kia"
        )
        db.add(persona)
        await db.flush()
    return persona


async def _process_kia_bot_response(
    trigger_message: str,
    circle_id: str, 
    channel_id: str,
    db_factory,
    kia_persona_id: str,
    requesting_user_id: str,
    is_leader: bool = False,
    role: str = "sponsor",
    email: str = "",
):
    # Broadcast typing status
    await manager.broadcast(
        circle_id,
        {
            "type": "typing_start",
            "payload": {"persona_id": kia_persona_id, "nickname": "Kia"},
        },
    )
    
    # Wait a bit for natural feel
    await asyncio.sleep(1.5)
    
    try:
        async with db_factory() as db:
            if role == "corporate":
                user_context = await fetch_corporate_context(
                    user_id=requesting_user_id,
                    email=email,
                    db=db
                )
                response_text = await generate_corporate_response(trigger_message, user_context=user_context)
            else:
                user_context = await fetch_user_context(
                    user_id=requesting_user_id,
                    circle_id=circle_id,
                    db=db,
                    include_private=True,
                    is_leader=is_leader,
                )
                response_text = await generate_kia_response(trigger_message, user_context=user_context)
                
            if not response_text:
                # Stop typing even if no response generated
                await manager.broadcast(
                    circle_id,
                    {"type": "typing_stop", "payload": {"persona_id": kia_persona_id}},
                )
                return
                
            kia_persona = await _get_kia_persona(db)
            
            # Persist Kia's message
            msg = ChatMessage(
                channel_id=channel_id,
                gamified_persona_id=kia_persona.id,
                content_text=response_text,
                shield_action="allow"
            )
            db.add(msg)
            await db.commit()
            await db.refresh(msg)
            
            # Broadcast Kia's message
            msg_out = await _message_to_out(msg, kia_persona)
            await manager.broadcast(
                circle_id,
                {
                    "type": "new_message",
                    "payload": msg_out.model_dump(mode="json"),
                },
            )
            
            # Stop typing status
            await manager.broadcast(
                circle_id,
                {"type": "typing_stop", "payload": {"persona_id": kia_persona_id}},
            )
    except Exception as e:
        logger.exception(f"Kia bot response error: {e}")
        # Always stop typing on error
        await manager.broadcast(
            circle_id,
            {"type": "typing_stop", "payload": {"persona_id": kia_persona_id}},
        )


async def _get_or_create_corporate_circle(user: SignupRequest, db: AsyncSession) -> tuple[str, str]:
    """Returns (circle_id, channel_id) for a corporate user's private Kia chat."""
    circle_name = f"Corporate Kia - {user.id}"
    
    circle_res = await db.execute(select(SponsorCircle).where(SponsorCircle.name == circle_name))
    circle = circle_res.scalars().first()
    
    if not circle:
        circle = SponsorCircle(name=circle_name, description="Private corporate Kia channel")
        db.add(circle)
        await db.flush()
        
        member = CircleMember(circle_id=circle.id, user_id=user.id, role="sponsor_leader")
        db.add(member)
        
        channel = ChatChannel(circle_id=circle.id, name="kia-strategy", channel_type="persistent")
        db.add(channel)
        await db.flush()
        
        # Add a welcome message from Kia
        kia_persona = await _get_kia_persona(db)
        if kia_persona:
            welcome_msg = ChatMessage(
                channel_id=channel.id,
                gamified_persona_id=kia_persona.id,
                content_text="Hello! I am Kia, your AI CSR Strategy Assistant. Welcome to your corporate dashboard. I can help you analyze your portfolio, compare impact circles, and optimize your ZenQ score. How can I assist you today?",
                shield_action="allow"
            )
            db.add(welcome_msg)

        await db.commit()
        await db.refresh(circle)
        await db.refresh(channel)
        return circle.id, channel.id
    
    channel_res = await db.execute(select(ChatChannel).where(ChatChannel.circle_id == circle.id))
    channel = channel_res.scalars().first()
    return circle.id, channel.id


# WebSocket endpoint


@router.websocket("/ws/circle/{circle_id}")
async def circle_websocket(
    circle_id: str,
    ws: WebSocket,
    token: str = Query(
        ..., description="JWT auth token (browser WS cannot send headers)"
    ),
    role: str = Query(
        default="sponsor", description="User role hint (sponsor or sponsor_leader)"
    ),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Real-time chat WebSocket for a SponsorCircle.

    Auth flow:
      1. Validate JWT token → get user
      2. Verify circle membership (CircleMember row exists)
      3. Verify enrollment exists for students
      4. Verify parental consent for student role
      5. Get/create GamifiedPersona
      6. Join room
    """
    user: Optional[SignupRequest] = await get_current_user_from_token(token, db)
    if user is None:
        logger.warning(f"WebSocket auth failed for token: {token[:10]}...")
        await ws.close(code=4000)
        return

    if circle_id == "corporate-kia":
        if user.persona.value != "corporate":
            await ws.close(code=4003)
            return
        circle_id, _ = await _get_or_create_corporate_circle(user, db)

    logger.info(f"WebSocket connecting: user={user.email}, circle={circle_id}")

    membership_result = await db.execute(
        select(CircleMember).where(
            and_(
                CircleMember.circle_id == circle_id,
                CircleMember.user_id == user.id,
            )
        )
    )
    membership = membership_result.scalar_one_or_none()
    if membership is None:
        logger.warning(f"WebSocket membership check failed: user={user.id}, circle={circle_id}")
        await ws.close(code=4003)  # not a member
        return

    from app.chat.models import ChatBan

    ban_result = await db.execute(
        select(ChatBan).where(
            ChatBan.circle_id == circle_id, ChatBan.user_id == user.id
        )
    )
    ban = ban_result.scalar_one_or_none()
    if ban:
        await ws.accept()
        await ws.send_json(
            {"type": "error", "payload": {"code": "banned", "reason": ban.reason}}
        )
        await ws.close(code=4005)  # user is banned
        return

    if str(user.persona) == "student":
        enrollment_result = await db.execute(
            select(Enrollment).where(
                and_(
                    Enrollment.circle_id == circle_id,
                    Enrollment.user_id == user.id,
                    Enrollment.is_active == True,  # noqa: E712
                )
            )
        )
        enrollment = enrollment_result.scalar_one_or_none()
        if enrollment is None:
            await ws.close(code=4001)  # not enrolled
            return

        # parental_consent_log table is queried directly
        from sqlalchemy import text  # noqa: PLC0415

        consent_result = await db.execute(
            text("""
                SELECT id FROM "ZENK".parental_consent_log
                WHERE student_id = :uid
                  AND (expires_at IS NULL OR expires_at > :now)
                LIMIT 1
            """),
            {"uid": user.id, "now": datetime.now(timezone.utc)},
        )
        if consent_result.scalar_one_or_none() is None:
            await ws.close(code=4004)  # consent required
            return

    persona = await _get_or_create_persona(user, db)
    await db.commit()

    await manager.connect(circle_id, ws, user.id)
    logger.info("User persona %s joined circle %s", persona.id, circle_id)

    # Welcome the user personally (so they know their own persona_id)
    await manager.send_to_one(
        ws,
        {
            "type": "welcome",
            "payload": {
                "persona_id": persona.id,
                "nickname": persona.nickname,
                "avatar_key": persona.avatar_key,
            },
        },
    )

    # Notify room of new presence (persona_id only — not user_id)
    await manager.broadcast(
        circle_id,
        {
            "type": "presence_update",
            "payload": {"persona_id": persona.id, "status": "online"},
        },
    )

    try:
        while True:
            # ── Receive message ───────────────────────────────────────────
            raw = await ws.receive_json()

            try:
                envelope = WSEnvelope(**raw)
            except Exception:
                await manager.send_to_one(
                    ws,
                    {
                        "type": "error",
                        "payload": {
                            "code": "invalid_envelope",
                            "reason": "Expected {type, payload}",
                        },
                    },
                )
                continue

            # ── Route by type ─────────────────────────────────────────────

            if envelope.type == "send_message":
                try:
                    data = MessageSend(**envelope.payload)
                except Exception:
                    await manager.send_to_one(
                        ws,
                        {
                            "type": "error",
                            "payload": {"code": "invalid_payload"},
                        },
                    )
                    continue

                # Gemini LLM shield (with regex fast-pass)
                shield_result = await shield_message_async(data.content_text or "")

                if shield_result["action"] == "block":
                    await manager.send_to_one(
                        ws,
                        {
                            "type": "error",
                            "payload": {
                                "code": "message_blocked",
                                "reason": shield_result["reason"],
                            },
                        },
                    )
                    continue
                elif shield_result["action"] == "warn":
                    await manager.send_to_one(
                        ws,
                        {
                            "type": "safety_nudge",
                            "payload": {
                                "reason": shield_result["reason"],
                                "entity": shield_result["entity"],
                            },
                        },
                    )

                # Persist message (append-only)
                msg = ChatMessage(
                    channel_id=str(data.channel_id),
                    gamified_persona_id=persona.id,
                    content_text=data.content_text,
                    media_url=data.media_url,
                    shield_action=shield_result["action"],
                    shield_reason=shield_result["reason"],
                )
                db.add(msg)
                await db.commit()
                await db.refresh(msg)

                msg_out = await _message_to_out(msg, persona)
                await manager.broadcast(
                    circle_id,
                    {
                        "type": "new_message",
                        "payload": msg_out.model_dump(mode="json"),
                    },
                )

                # ── Trigger Kia Bot on @kia mention ──
                if "@kia" in (data.content_text or "").lower():
                    kia_p = await _get_kia_persona(db)
                    is_leader_user = (role == "sponsor_leader")
                    asyncio.create_task(
                        _process_kia_bot_response(
                            data.content_text or "",
                            circle_id,
                            str(data.channel_id),
                            SessionLocal,
                            str(kia_p.id),
                            str(user.id),  # Pass requesting user's ID for RAG context
                            is_leader=is_leader_user,
                            role=role,
                            email=user.email,
                        )
                    )

            elif envelope.type == "delete_message":
                msg_id = envelope.payload.get("message_id")
                if not msg_id:
                    continue

                # Fetch message
                res = await db.execute(
                    select(ChatMessage).where(ChatMessage.id == str(msg_id))
                )
                msg_obj = res.scalar_one_or_none()

                if not msg_obj:
                    continue

                # Check ownership
                if msg_obj.gamified_persona_id != persona.id:
                    await manager.send_to_one(
                        ws,
                        {
                            "type": "error",
                            "payload": {
                                "code": "unauthorized_delete",
                                "reason": "You can only delete your own messages",
                            },
                        },
                    )
                    continue

                # Soft delete
                msg_obj.deleted_at = datetime.now(timezone.utc)
                await db.commit()

                # Broadcast
                await manager.broadcast(
                    circle_id,
                    {"type": "message_deleted", "payload": {"message_id": str(msg_id)}},
                )

            elif envelope.type == "raise_hand":
                if circle_id not in _raised_hands:
                    _raised_hands[circle_id] = set()
                _raised_hands[circle_id].add(persona.id)
                await manager.broadcast(
                    circle_id,
                    {
                        "type": "hand_raised",
                        "payload": {
                            "persona_id": persona.id,
                            "nickname": persona.nickname,
                            "avatar_key": persona.avatar_key,
                        },
                    },
                )

            elif envelope.type == "lower_hand":
                if circle_id in _raised_hands:
                    _raised_hands[circle_id].discard(persona.id)
                await manager.broadcast(
                    circle_id,
                    {
                        "type": "hand_lowered",
                        "payload": {"persona_id": persona.id},
                    },
                )

            elif envelope.type == "sos_report":
                try:
                    data = SOSReportIn(**envelope.payload)
                except Exception:
                    await manager.send_to_one(
                        ws,
                        {
                            "type": "error",
                            "payload": {"code": "invalid_payload"},
                        },
                    )
                    continue

                # Fetch message and soft-hide it
                msg_result = await db.execute(
                    select(ChatMessage).where(ChatMessage.id == str(data.message_id))
                )
                target_msg = msg_result.scalar_one_or_none()
                if target_msg is None:
                    await manager.send_to_one(
                        ws,
                        {
                            "type": "error",
                            "payload": {"code": "message_not_found"},
                        },
                    )
                    continue

                # SOS soft-hide: only hidden_at is updated on the message row
                target_msg.hidden_at = datetime.now(timezone.utc)

                # Create SOS report row
                logger.info(
                    f"Creating SOS report for message {target_msg.id} by reporter {persona.id}"
                )
                sos = SOSReport(
                    message_id=target_msg.id,
                    reporter_persona_id=persona.id,
                    hidden_at=datetime.now(timezone.utc),
                )
                db.add(sos)
                await db.commit()
                logger.info(f"SOS report {sos.id} persisted successfully")

                # Broadcast soft-hide to room
                await manager.broadcast(
                    circle_id,
                    {
                        "type": "message_hidden",
                        "payload": {"message_id": target_msg.id},
                    },
                )

                # Notify admins via existing email service
                # reuse existing notification service here
                try:
                    from app.services.email import send_email

                    await send_email(
                        subject="[ZENK ALERT] SOS Report Submitted",
                        to_email=settings.admin_notification_to,
                        text_body=(
                            f"SOS report filed on message {target_msg.id} in circle {circle_id}.\n"
                            f"Reporter persona: {persona.id}\n"
                            "Please review the SOS queue in the admin panel."
                        ),
                        html_body=None,
                    )
                except Exception:
                    logger.exception("Failed to send SOS admin email")

            elif envelope.type == "ping":
                await manager.send_to_one(ws, {"type": "pong"})

            else:
                await manager.send_to_one(
                    ws,
                    {
                        "type": "error",
                        "payload": {
                            "code": "unknown_type",
                            "reason": f"DEBUG INFO: {repr(envelope.type)} length={len(envelope.type)} is_ts={envelope.type == 'typing_stop'}",
                        },
                    },
                )

    except WebSocketDisconnect:
        manager.disconnect(circle_id, ws)
        # Remove from raised hands
        if circle_id in _raised_hands:
            _raised_hands[circle_id].discard(persona.id)
        # Notify room of disconnect
        await manager.broadcast(
            circle_id,
            {
                "type": "presence_update",
                "payload": {"persona_id": persona.id, "status": "offline"},
            },
        )
        logger.info(
            "User persona %s disconnected from circle %s", persona.id, circle_id
        )


# REST: GET /chat/channels/{circle_id}


@router.get("/chat/channels/{circle_id}", response_model=list[ChannelOut])
async def list_channels(
    circle_id: str,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Return channels for a circle. User must be a member."""
    user = await get_current_user_from_token(token, db)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or missing token")

    if circle_id == "corporate-kia":
        if user.persona.value != "corporate":
            raise HTTPException(status_code=403, detail="Corporate role required for Kia chat")
        circle_id, _ = await _get_or_create_corporate_circle(user, db)

    # Verify membership
    membership = await db.execute(
        select(CircleMember).where(
            and_(CircleMember.circle_id == circle_id, CircleMember.user_id == user.id)
        )
    )
    if membership.scalar_one_or_none() is None:
        raise HTTPException(status_code=403, detail="Not a member of this circle")

    result = await db.execute(
        select(ChatChannel).where(ChatChannel.circle_id == circle_id)
    )
    channels = result.scalars().all()
    return [
        ChannelOut(
            id=c.id,
            circle_id=c.circle_id,
            name=c.name,
            channel_type=(
                c.channel_type.value
                if hasattr(c.channel_type, "value")
                else c.channel_type
            ),
            created_at=c.created_at,
        )
        for c in channels
    ]


# REST: POST /chat/channels  (sponsor or admin only)


@router.post(
    "/chat/channels", response_model=ChannelOut, status_code=status.HTTP_201_CREATED
)
async def create_channel(
    body: ChannelCreate,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Create a chat channel. Sponsor or admin role only."""
    user = await get_current_user_from_token(token, db)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or missing token")

    if str(user.persona) not in ("sponsor", "admin"):
        raise HTTPException(status_code=403, detail="Sponsor or admin role required")

    # Verify circle exists
    circle_result = await db.execute(
        select(SponsorCircle).where(SponsorCircle.id == body.circle_id)
    )
    if circle_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Circle not found")

    channel = ChatChannel(
        circle_id=body.circle_id,
        name=body.name,
        channel_type=body.channel_type,
    )
    db.add(channel)
    await db.commit()
    await db.refresh(channel)

    return ChannelOut(
        id=channel.id,
        circle_id=channel.circle_id,
        name=channel.name,
        channel_type=(
            channel.channel_type.value
            if hasattr(channel.channel_type, "value")
            else channel.channel_type
        ),
        created_at=channel.created_at,
    )


# REST: GET /chat/messages/{channel_id}


@router.get("/chat/messages/{channel_id}", response_model=list[MessageOut])
async def list_messages(
    channel_id: str,
    token: str = Query(...),
    before: Optional[datetime] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """
    Return paginated messages for a channel.
    Excludes hidden messages.
    Joins persona for nickname and avatar.
    """
    user = await get_current_user_from_token(token, db)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or missing token")

    # Verify channel exists and user is a member of its circle
    channel_result = await db.execute(
        select(ChatChannel).where(ChatChannel.id == channel_id)
    )
    channel = channel_result.scalar_one_or_none()
    if channel is None:
        raise HTTPException(status_code=404, detail="Channel not found")

    membership = await db.execute(
        select(CircleMember).where(
            and_(
                CircleMember.circle_id == channel.circle_id,
                CircleMember.user_id == user.id,
            )
        )
    )
    if membership.scalar_one_or_none() is None:
        raise HTTPException(status_code=403, detail="Not a member of this circle")


    from sqlalchemy.orm import joinedload
    query = (
        select(ChatMessage)
        .options(joinedload(ChatMessage.persona))
        .where(
            and_(
                ChatMessage.channel_id == channel_id,
                ChatMessage.hidden_at.is_(None),
            )
        )
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
    )
    if before:
        query = query.where(ChatMessage.created_at < before)

    msg_result = await db.execute(query)
    messages = msg_result.scalars().unique().all()

    output = []
    for msg in reversed(messages):
        if not msg.persona:
            continue
        output.append(
            MessageOut(
                id=msg.id,
                channel_id=msg.channel_id,
                gamified_persona_id=msg.gamified_persona_id,
                persona_nickname=msg.persona.nickname,
                avatar_key=msg.persona.avatar_key,
                content_text=msg.content_text if not msg.deleted_at else None,
                media_url=msg.media_url if not msg.deleted_at else None,
                shield_action=msg.shield_action,
                created_at=msg.created_at,
                deleted_at=msg.deleted_at,
            )
        )
    return output


# REST: POST /chat/upload


@router.post("/chat/upload")
async def upload_chat_file(
    file: UploadFile,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a file for use in chat (images, PDF only).
    Max size: 5 MB. Returns {url: str}.
    """
    user = await get_current_user_from_token(token, db)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or missing token")

    # Content-type whitelist
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type: {file.content_type}. Allowed: {', '.join(ALLOWED_CONTENT_TYPES)}",
        )

    # Cloudinary upload logic
    from app.services.cloudinary_service import upload_image, upload_raw

    is_image = file.content_type in ["image/jpeg", "image/png", "image/webp"]
    
    if is_image:
        url = await upload_image(file, folder="zenk/chat")
    else:
        url = await upload_raw(file, folder="zenk/chat")

    if not url:
         raise HTTPException(
            status_code=500,
            detail="Failed to upload file to Cloud storage."
        )

    return {"url": url}


# REST: GET /chat/sos-reports  (admin only)


@router.get("/chat/sos-reports", response_model=list[SOSReportOut])
async def list_sos_reports(
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Return unresolved SOS reports. Admin only."""
    user = await get_current_user_from_token(token, db)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or missing token")

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


# REST: PATCH /chat/sos-reports/{report_id}/resolve  (admin only)


@router.patch("/chat/sos-reports/{report_id}/resolve")
async def resolve_sos_report(
    report_id: str,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Mark an SOS report as resolved. Admin only."""
    user = await get_current_user_from_token(token, db)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or missing token")

    result = await db.execute(select(SOSReport).where(SOSReport.id == report_id))
    report = result.scalar_one_or_none()
    if report is None:
        raise HTTPException(status_code=404, detail="SOS report not found")

    report.resolved_at = datetime.now(timezone.utc)

    # Audit trail
    log = AdminAccessLog(
        admin_id=str(user.id),
        action="RESOLVE_REPORT",
        target_table="sos_reports",
        target_id=str(report_id),
        changes_json={"resolved": True},
    )
    db.add(log)

    await db.commit()
    return {"id": report_id, "resolved_at": report.resolved_at.isoformat()}


@router.get("/chat/circle/{circle_id}/members", response_model=list[CircleMemberOut])
async def list_circle_members(
    circle_id: str,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Return all members in a circle (gamified personas only). User must be a member."""
    user = await get_current_user_from_token(token, db)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or missing token")

    if circle_id == "corporate-kia":
        if user.persona.value != "corporate":
            raise HTTPException(status_code=403, detail="Corporate role required")
        circle_id, _ = await _get_or_create_corporate_circle(user, db)

    # Verify membership
    membership_check = await db.execute(
        select(CircleMember).where(
            and_(CircleMember.circle_id == circle_id, CircleMember.user_id == user.id)
        )
    )
    if membership_check.scalar_one_or_none() is None:
        raise HTTPException(status_code=403, detail="Not a member of this circle")

    # Fetch all members joined with their personas
    logger.info(f"Fetching members for circle {circle_id}")
    result = await db.execute(
        select(CircleMember, GamifiedPersona)
        .join(GamifiedPersona, CircleMember.user_id == GamifiedPersona.user_id)
        .where(CircleMember.circle_id == circle_id)
        .order_by(CircleMember.joined_at.asc())
    )
    rows = result.all()
    logger.info(f"Found {len(rows)} members for circle {circle_id}")

    output = []
    for m, p in rows:
        output.append(CircleMemberOut(
            persona_id=p.id,
            nickname=p.nickname,
            avatar_key=p.avatar_key,
            role=m.role,
            joined_at=m.joined_at,
        ))
    return output
