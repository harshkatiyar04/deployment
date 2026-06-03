"""Access + refresh token issuance and rotation."""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jwt_auth import create_access_token, jwt_settings
from app.models.refresh_token import RefreshToken
from app.models.signup import SignupRequest


def _hash_refresh_token(plain: str) -> str:
    return hashlib.sha256(plain.encode("utf-8")).hexdigest()


async def issue_token_pair(db: AsyncSession, user_id: str) -> Tuple[str, str]:
    """Return (access_jwt, plain_refresh_token)."""
    access = create_access_token(data={"sub": user_id})
    refresh = await _create_refresh_token(db, user_id)
    return access, refresh


async def _create_refresh_token(db: AsyncSession, user_id: str) -> str:
    plain = secrets.token_urlsafe(48)
    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=jwt_settings.refresh_token_expire_days)
    row = RefreshToken(
        user_id=user_id,
        token_hash=_hash_refresh_token(plain),
        expires_at=expires,
        created_at=now,
    )
    db.add(row)
    await db.flush()
    return plain


async def refresh_access_token(
    db: AsyncSession, plain_refresh: str
) -> Optional[Tuple[str, str, SignupRequest]]:
    """
    Validate refresh token, rotate it, return (access_jwt, new_plain_refresh, user).
    Returns None if invalid/expired/revoked.
    """
    token_hash = _hash_refresh_token(plain_refresh)
    now = datetime.now(timezone.utc)

    res = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > now,
        )
    )
    row = res.scalar_one_or_none()
    if not row:
        return None

    user_res = await db.execute(
        select(SignupRequest).where(SignupRequest.id == row.user_id)
    )
    user = user_res.scalar_one_or_none()
    if not user:
        return None

    row.revoked_at = now
    access = create_access_token(data={"sub": user.id})
    new_refresh = await _create_refresh_token(db, user.id)
    await db.commit()
    return access, new_refresh, user


async def revoke_refresh_token(db: AsyncSession, plain_refresh: str) -> bool:
    token_hash = _hash_refresh_token(plain_refresh)
    res = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
        )
    )
    row = res.scalar_one_or_none()
    if not row:
        return False
    row.revoked_at = datetime.now(timezone.utc)
    await db.commit()
    return True
