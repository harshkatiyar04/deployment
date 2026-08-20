"""Unique sponsor circle display names (case-insensitive)."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.models import SponsorCircle
from app.models.enums import KycStatus
from app.models.signup import SignupRequest

# Applications that still "hold" a requested circle name.
_HOLDING_KYC = frozenset(
    {KycStatus.pending, KycStatus.approved, KycStatus.info_required}
)


def normalize_circle_name(name: str) -> str:
    return " ".join((name or "").strip().split())


async def circle_name_taken(
    db: AsyncSession,
    name: str,
    *,
    exclude_circle_id: Optional[str] = None,
    exclude_signup_id: Optional[str] = None,
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
    if res.scalar_one_or_none() is not None:
        return True

    # Also block names already requested on in-flight / approved leader apps.
    pending_q = select(SignupRequest.id).where(
        SignupRequest.requested_circle_name.isnot(None),
        func.lower(func.trim(SignupRequest.requested_circle_name)) == cleaned.lower(),
        SignupRequest.kyc_status.in_(_HOLDING_KYC),
    )
    if exclude_signup_id:
        pending_q = pending_q.where(SignupRequest.id != exclude_signup_id)
    pending_res = await db.execute(pending_q.limit(1))
    return pending_res.scalar_one_or_none() is not None


async def assert_circle_name_available(
    db: AsyncSession,
    name: str,
    *,
    exclude_circle_id: Optional[str] = None,
    exclude_signup_id: Optional[str] = None,
) -> str:
    cleaned = normalize_circle_name(name)
    if len(cleaned) < 2:
        raise ValueError("Circle name must be at least 2 characters.")
    if await circle_name_taken(
        db,
        cleaned,
        exclude_circle_id=exclude_circle_id,
        exclude_signup_id=exclude_signup_id,
    ):
        raise ValueError("This circle name is already in use. Choose a different name.")
    return cleaned
