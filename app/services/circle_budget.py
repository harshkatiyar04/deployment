"""Sponsor circle FY budget — load/save per circle."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Tuple

from fastapi import HTTPException
from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.models import CircleMember, SponsorCircle
from app.models.signup import SignupRequest

LEADER_ROLES = frozenset({"lead", "sponsor_leader", "coordinator"})

DEFAULT_TXNS = [
    {"date": "Mar 20", "description": "New Member Kit", "amount": 5000, "category": "Operational"},
    {"date": "Mar 15", "description": "Kia AI Tokens", "amount": 3500, "category": "Platform"},
    {"date": "Mar 10", "description": "School Supplies", "amount": 12000, "category": "Student"},
]


def _fy_display(label: Optional[str]) -> str:
    raw = (label or "2025-26").strip()
    return f"FY {raw}" if not raw.upper().startswith("FY") else raw


def _can_set_budget(role: Optional[str]) -> bool:
    return (role or "").lower() in LEADER_ROLES or role == "sponsor_leader"


async def resolve_user_circle(
    db: AsyncSession, user_id: str, circle_id: Optional[str] = None
) -> Tuple[SponsorCircle, str]:
    """Return circle + member role for the user (preferred: lead/coordinator)."""
    q = (
        select(SponsorCircle, CircleMember.role)
        .join(CircleMember, CircleMember.circle_id == SponsorCircle.id)
        .where(CircleMember.user_id == user_id)
    )
    if circle_id:
        q = q.where(SponsorCircle.id == circle_id)

    priority = case(
        (CircleMember.role.in_(list(LEADER_ROLES)), 0),
        else_=1,
    )
    q = q.order_by(priority, SponsorCircle.name)
    res = await db.execute(q)
    row = res.first()
    if not row:
        raise HTTPException(status_code=404, detail="You are not a member of any sponsor circle.")
    return row[0], row[1]


def build_budget_payload(circle: SponsorCircle, role: Optional[str]) -> dict:
    total = int(circle.annual_budget or 150_000)
    spent = int(circle.budget_spent or 94_200)
    collected = int(circle.budget_collected or 124_500)
    balance_to_spend = max(0, total - spent)

    return {
        "circle_id": circle.id,
        "circle_name": circle.name,
        "total_budget": total,
        "spent": spent,
        "collected": collected,
        "balance_to_spend": balance_to_spend,
        "fy_label": _fy_display(circle.fy_label),
        "fy_key": circle.fy_label or "2025-26",
        "transactions": DEFAULT_TXNS,
        "can_set_budget": _can_set_budget(role),
        "budget_set_at": circle.budget_set_at,
    }


async def set_circle_budget(
    db: AsyncSession,
    user: SignupRequest,
    annual_budget: int,
    fy_label: Optional[str] = None,
    circle_id: Optional[str] = None,
) -> dict:
    circle, role = await resolve_user_circle(db, user.id, circle_id)
    if not _can_set_budget(role):
        raise HTTPException(
            status_code=403,
            detail="Only the circle leader or coordinator can set the annual budget.",
        )

    if annual_budget < 1 or annual_budget > 50_000_000:
        raise HTTPException(status_code=400, detail="Annual budget must be between ₹1 and ₹5 crore.")

    circle.annual_budget = annual_budget
    if fy_label and fy_label.strip():
        cleaned = fy_label.strip().replace("FY", "").strip()
        circle.fy_label = cleaned or circle.fy_label
    circle.budget_set_at = datetime.now(timezone.utc)
    circle.budget_set_by = user.id
    await db.commit()
    await db.refresh(circle)
    return build_budget_payload(circle, role)
