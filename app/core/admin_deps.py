"""Admin-only API dependencies (KYC review, queues, etc.)."""

from __future__ import annotations

import secrets
from typing import Optional

from fastapi import Header, HTTPException, status

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import settings

SYSTEM_ADMIN_ACTOR_ID = "00000000-0000-0000-0000-000000000000"


async def resolve_admin_actor_id(db: AsyncSession) -> str:
    """Best-effort admin user id for audit columns (admin@zenk signup if present)."""
    from app.models.signup import SignupRequest

    res = await db.execute(
        select(SignupRequest.id).where(SignupRequest.email == "admin@zenk").limit(1)
    )
    return res.scalar_one_or_none() or SYSTEM_ADMIN_ACTOR_ID


async def require_admin_api_key(
    x_zenk_admin_key: Optional[str] = Header(default=None, alias="X-Zenk-Admin-Key"),
) -> None:
    """
    Require a shared admin API key on sensitive routes.
    Set ZENK_ADMIN_API_KEY in production; FE sends the same value via VITE_ZENK_ADMIN_API_KEY.
    """
    expected = (settings.admin_api_key or "").strip()
    if not expected:
        if settings.admin_allow_open_dev:
            return
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Admin API is not configured. Set ZENK_ADMIN_API_KEY in the backend .env "
                "(and VITE_ZENK_ADMIN_API_KEY on the frontend), or for local dev only set "
                "ZENK_ADMIN_ALLOW_OPEN_DEV=true."
            ),
        )
    provided = (x_zenk_admin_key or "").strip()
    if not provided or not secrets.compare_digest(provided, expected):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin authentication required.",
        )
