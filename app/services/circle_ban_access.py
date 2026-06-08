"""Resolve whether a user is banned from circle chat (account-level gate)."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.models import ChatBan, SponsorCircle


async def resolve_user_circle_ban(
    db: AsyncSession,
    user_id: str,
) -> Optional[dict[str, Any]]:
    """
    Return the user's most recent active circle ban, if any.
    Used at login and /auth/me to block dashboard access.
    """
    res = await db.execute(
        select(ChatBan, SponsorCircle.name)
        .join(SponsorCircle, ChatBan.circle_id == SponsorCircle.id)
        .where(ChatBan.user_id == user_id)
        .order_by(ChatBan.created_at.desc())
        .limit(1)
    )
    row = res.first()
    if not row:
        return None
    ban, circle_name = row
    return {
        "banned": True,
        "circle_id": str(ban.circle_id),
        "circle_name": circle_name,
        "reason": ban.reason,
        "banned_at": ban.created_at.isoformat() if ban.created_at else None,
    }
