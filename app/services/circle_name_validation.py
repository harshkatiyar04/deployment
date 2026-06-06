"""Unique sponsor circle display names (case-insensitive)."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.models import SponsorCircle


def normalize_circle_name(name: str) -> str:
    return " ".join((name or "").strip().split())


async def circle_name_taken(
    db: AsyncSession,
    name: str,
    *,
    exclude_circle_id: Optional[str] = None,
) -> bool:
    cleaned = normalize_circle_name(name)
    if len(cleaned) < 2:
        return False
    q = select(SponsorCircle.id).where(
        func.lower(func.trim(SponsorCircle.name)) == cleaned.lower()
    )
    if exclude_circle_id:
        q = q.where(SponsorCircle.id != exclude_circle_id)
    res = await db.execute(q.limit(1))
    return res.scalar_one_or_none() is not None


async def assert_circle_name_available(
    db: AsyncSession,
    name: str,
    *,
    exclude_circle_id: Optional[str] = None,
) -> str:
    cleaned = normalize_circle_name(name)
    if len(cleaned) < 2:
        raise ValueError("Circle name must be at least 2 characters.")
    if await circle_name_taken(db, cleaned, exclude_circle_id=exclude_circle_id):
        raise ValueError("This circle name is already in use. Choose a different name.")
    return cleaned
