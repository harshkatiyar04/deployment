"""Circle-scoped authorization for chat REST and WebSocket handlers."""

from __future__ import annotations

from typing import Optional

from fastapi import HTTPException
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.chat.display_name import is_leader_member_role
from app.chat.models import ChatChannel, ChatMessage, CircleMember
from app.core.jwt_auth import get_current_user_from_token
from app.models.signup import SignupRequest

CHANNEL_CREATE_PERSONAS = frozenset(
    {"sponsor", "sponsor_member", "sponsor_leader", "admin"}
)


async def chat_user_from_token(token: str, db: AsyncSession) -> SignupRequest:
    user = await get_current_user_from_token(token, db)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    return user


async def get_circle_membership(
    db: AsyncSession,
    *,
    circle_id: str,
    user_id: str,
) -> Optional[CircleMember]:
    res = await db.execute(
        select(CircleMember).where(
            CircleMember.circle_id == circle_id,
            CircleMember.user_id == user_id,
        )
    )
    return res.scalar_one_or_none()


async def require_circle_member(
    db: AsyncSession,
    *,
    circle_id: str,
    user: SignupRequest,
) -> CircleMember:
    membership = await get_circle_membership(db, circle_id=circle_id, user_id=user.id)
    if membership is None:
        raise HTTPException(status_code=403, detail="Not a member of this circle")
    return membership


async def require_circle_leader(
    db: AsyncSession,
    *,
    circle_id: str,
    user: SignupRequest,
) -> CircleMember:
    membership = await require_circle_member(db, circle_id=circle_id, user=user)
    if not is_leader_member_role(membership.role):
        raise HTTPException(status_code=403, detail="Circle leader role required")
    return membership


async def get_channel_in_circle(
    db: AsyncSession,
    *,
    channel_id: str,
    circle_id: str,
) -> Optional[ChatChannel]:
    res = await db.execute(
        select(ChatChannel).where(
            ChatChannel.id == channel_id,
            ChatChannel.circle_id == circle_id,
        )
    )
    return res.scalar_one_or_none()


async def require_channel_in_circle(
    db: AsyncSession,
    *,
    channel_id: str,
    circle_id: str,
) -> ChatChannel:
    channel = await get_channel_in_circle(db, channel_id=channel_id, circle_id=circle_id)
    if channel is None:
        raise HTTPException(status_code=403, detail="Channel not in this circle")
    return channel


async def get_message_in_circle(
    db: AsyncSession,
    *,
    message_id: str,
    circle_id: str,
) -> Optional[ChatMessage]:
    res = await db.execute(
        select(ChatMessage)
        .join(ChatChannel, ChatMessage.channel_id == ChatChannel.id)
        .where(
            ChatMessage.id == message_id,
            ChatChannel.circle_id == circle_id,
        )
    )
    return res.scalar_one_or_none()


async def require_channel_access_for_user(
    db: AsyncSession,
    *,
    channel_id: str,
    user: SignupRequest,
) -> tuple[ChatChannel, CircleMember]:
    res = await db.execute(select(ChatChannel).where(ChatChannel.id == channel_id))
    channel = res.scalar_one_or_none()
    if channel is None:
        raise HTTPException(status_code=404, detail="Channel not found")
    membership = await require_circle_member(
        db, circle_id=channel.circle_id, user=user
    )
    return channel, membership


def require_channel_create_persona(user: SignupRequest) -> None:
    persona = user.persona.value if hasattr(user.persona, "value") else str(user.persona)
    if persona not in CHANNEL_CREATE_PERSONAS:
        raise HTTPException(status_code=403, detail="Not authorized to create channels")


async def set_admin_audit_actor(db: AsyncSession, admin_id: str) -> None:
    """Set Postgres session variable for audit triggers (parameterized)."""
    await db.execute(
        text("SET LOCAL zenk.current_admin_id = :admin_id"),
        {"admin_id": str(admin_id)},
    )
