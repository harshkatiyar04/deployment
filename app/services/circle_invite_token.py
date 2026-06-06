"""Opaque circle invite tokens for member signup links."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.models import SponsorCircle
from app.models.circle_ops import CircleInviteToken


def _new_token() -> str:
    return secrets.token_urlsafe(24)


async def create_circle_invite_token(
    db: AsyncSession,
    *,
    circle_id: str,
    created_by: str,
    ttl_days: int = 90,
) -> CircleInviteToken:
    expires = datetime.now(timezone.utc) + timedelta(days=ttl_days)
    for _ in range(5):
        token = _new_token()
        existing = await db.execute(
            select(CircleInviteToken.id).where(CircleInviteToken.token == token)
        )
        if not existing.scalar_one_or_none():
            row = CircleInviteToken(
                circle_id=circle_id,
                token=token,
                created_by=created_by,
                expires_at=expires,
            )
            db.add(row)
            await db.commit()
            await db.refresh(row)
            return row
    raise RuntimeError("Could not generate unique invite token")


async def resolve_invite_token(db: AsyncSession, token: str) -> tuple[str, str] | None:
    """Return (circle_id, circle_name) if token is valid."""
    raw = (token or "").strip()
    if not raw or len(raw) < 16:
        return None
    now = datetime.now(timezone.utc)
    res = await db.execute(
        select(CircleInviteToken, SponsorCircle.name)
        .join(SponsorCircle, SponsorCircle.id == CircleInviteToken.circle_id)
        .where(
            CircleInviteToken.token == raw,
            CircleInviteToken.revoked_at.is_(None),
            CircleInviteToken.expires_at > now,
        )
    )
    row = res.first()
    if not row:
        return None
    invite, circle_name = row
    return invite.circle_id, circle_name


def is_uuid_like(value: str) -> bool:
    v = (value or "").strip()
    if len(v) != 36:
        return False
    parts = v.split("-")
    return len(parts) == 5 and all(len(p) in (8, 4, 4, 4, 12) for p in parts)
