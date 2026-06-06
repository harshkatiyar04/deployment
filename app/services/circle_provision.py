"""Provision a sponsor circle for an approved leader (one primary circle per leader)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.models import ChatChannel, CircleMember, SponsorCircle
from app.models.enums import KycStatus, Persona
from app.models.signup import SignupRequest
from app.services.circle_budget import LEADER_ROLES, _can_set_budget


async def _leader_has_circle(db: AsyncSession, user_id: str) -> SponsorCircle | None:
    res = await db.execute(
        select(SponsorCircle)
        .join(CircleMember, CircleMember.circle_id == SponsorCircle.id)
        .where(
            CircleMember.user_id == user_id,
            CircleMember.role.in_(list(LEADER_ROLES) + ["sponsor_leader"]),
        )
        .order_by(SponsorCircle.created_at)
    )
    return res.scalars().first()


async def provision_leader_circle(
    db: AsyncSession,
    user: SignupRequest,
    *,
    name: str | None = None,
) -> dict:
    if user.persona != Persona.sponsor_leader:
        raise ValueError("Only sponsor leaders can provision a circle.")
    kyc = user.kyc_status.value if hasattr(user.kyc_status, "value") else str(user.kyc_status)
    if kyc != KycStatus.approved.value:
        raise ValueError("Leader KYC must be approved before creating a circle.")

    existing = await _leader_has_circle(db, user.id)
    if existing:
        return {"id": existing.id, "name": existing.name, "role": "sponsor_leader", "created": False}

    from app.services.circle_name_validation import assert_circle_name_available

    raw = (name or "").strip()
    if len(raw) < 2:
        raise ValueError("Circle name is required (at least 2 characters).")
    display = await assert_circle_name_available(db, raw)

    circle = SponsorCircle(
        name=display[:255],
        description="Sponsor circle",
        status="active",
        annual_budget=0,
        budget_spent=0,
        budget_collected=0,
        budget_set_at=None,
        budget_set_by=None,
    )
    db.add(circle)
    await db.flush()

    db.add(
        CircleMember(
            circle_id=circle.id,
            user_id=user.id,
            role="sponsor_leader",
        )
    )
    db.add(
        ChatChannel(
            circle_id=circle.id,
            name="general",
            channel_type="persistent",
        )
    )
    await db.commit()
    await db.refresh(circle)

    return {
        "id": circle.id,
        "name": circle.name,
        "role": "sponsor_leader",
        "created": True,
    }
