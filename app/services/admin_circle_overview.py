"""Admin overview of all sponsor circles — roster, activity, ops queue context."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.models import CircleMember, SponsorCircle
from app.models.circle_ops import CircleAdminRequest, REQUEST_MEMBER_REMOVAL, STATUS_PENDING
from app.models.signup import SignupRequest
from app.services.circle_membership_ops import circle_member_limit, count_circle_members
from app.services.sponsor_circle_time_impact import (
    _month_start,
    member_activity_since,
    platform_hours_since,
)

LEADER_ROLES = frozenset({"lead", "sponsor_leader", "coordinator"})


def _iso(dt) -> Optional[str]:
    if not dt:
        return None
    return dt.isoformat()


async def _circle_leader_name(db: AsyncSession, circle_id: str) -> Optional[str]:
    res = await db.execute(
        select(SignupRequest.full_name)
        .join(CircleMember, CircleMember.user_id == SignupRequest.id)
        .where(
            CircleMember.circle_id == circle_id,
            CircleMember.role.in_(list(LEADER_ROLES)),
        )
        .limit(1)
    )
    return res.scalar_one_or_none()


async def _pending_ops_count(db: AsyncSession, circle_id: str) -> int:
    res = await db.execute(
        select(func.count())
        .select_from(CircleAdminRequest)
        .where(
            CircleAdminRequest.circle_id == circle_id,
            CircleAdminRequest.status == STATUS_PENDING,
        )
    )
    return int(res.scalar_one() or 0)


async def _circle_month_hours(db: AsyncSession, circle: SponsorCircle) -> float:
    since = _month_start()
    res = await db.execute(
        select(CircleMember.user_id).where(CircleMember.circle_id == circle.id)
    )
    total = 0.0
    for (uid,) in res.all():
        act = await member_activity_since(db, uid, circle, since)
        total += float(act.get("hours") or 0)
    return round(total, 1)


async def list_admin_circles(db: AsyncSession) -> list[dict[str, Any]]:
    res = await db.execute(
        select(SponsorCircle).order_by(SponsorCircle.created_at.desc())
    )
    circles = list(res.scalars().all())
    out: list[dict[str, Any]] = []
    for circle in circles:
        member_count = await count_circle_members(db, circle.id)
        out.append(
            {
                "id": circle.id,
                "name": circle.name,
                "status": circle.status,
                "member_count": member_count,
                "member_limit": circle_member_limit(circle),
                "created_at": _iso(circle.created_at),
                "leader_name": await _circle_leader_name(db, circle.id),
                "circle_hours_month": await _circle_month_hours(db, circle),
                "pending_ops_count": await _pending_ops_count(db, circle.id),
            }
        )
    return out


async def get_admin_circle_detail(db: AsyncSession, circle_id: str) -> Optional[dict[str, Any]]:
    res = await db.execute(select(SponsorCircle).where(SponsorCircle.id == circle_id))
    circle = res.scalar_one_or_none()
    if not circle:
        return None

    since = _month_start()
    members_res = await db.execute(
        select(CircleMember, SignupRequest)
        .join(SignupRequest, SignupRequest.id == CircleMember.user_id)
        .where(CircleMember.circle_id == circle.id)
        .order_by(CircleMember.joined_at.asc())
    )
    members_out: list[dict[str, Any]] = []
    total_hrs = 0.0
    for cm, signup in members_res.all():
        act = await member_activity_since(db, signup.id, circle, since)
        hrs = float(act.get("hours") or 0)
        total_hrs += hrs
        members_out.append(
            {
                "user_id": signup.id,
                "name": signup.full_name or "Member",
                "email": signup.email,
                "role": cm.role,
                "joined_at": _iso(cm.joined_at),
                "hours_this_month": hrs,
                "messages_count": act.get("messages_count", 0),
                "orders_count": act.get("orders_count", 0),
                "enrollment_reviews_count": act.get("enrollment_reviews_count", 0),
            }
        )

    pending_removals = await db.execute(
        select(CircleAdminRequest.target_user_id).where(
            CircleAdminRequest.circle_id == circle.id,
            CircleAdminRequest.request_type == REQUEST_MEMBER_REMOVAL,
            CircleAdminRequest.status == STATUS_PENDING,
        )
    )
    pending_removal_ids = {uid for (uid,) in pending_removals.all() if uid}

    for m in members_out:
        m["pending_removal"] = m["user_id"] in pending_removal_ids
        if total_hrs > 0:
            m["participation_pct"] = int(round(100 * m["hours_this_month"] / total_hrs))
        else:
            m["participation_pct"] = 0

    members_out.sort(key=lambda x: x["hours_this_month"], reverse=True)

    return {
        "id": circle.id,
        "name": circle.name,
        "status": circle.status,
        "description": circle.description,
        "member_count": len(members_out),
        "member_limit": circle_member_limit(circle),
        "created_at": _iso(circle.created_at),
        "leader_name": await _circle_leader_name(db, circle.id),
        "circle_hours_month": round(total_hrs, 1),
        "pending_ops_count": await _pending_ops_count(db, circle.id),
        "annual_budget": circle.annual_budget,
        "budget_spent": circle.budget_spent,
        "members": members_out,
    }


async def admin_circles_summary_light(db: AsyncSession) -> dict[str, Any]:
    """
    Fast circle KPIs for the admin dashboard — aggregate counts only (no per-circle loop).
    Full roster + per-member hours remain on list_admin_circles / circle detail pages.
    """
    circles_res = await db.execute(select(func.count()).select_from(SponsorCircle))
    total_circles = int(circles_res.scalar_one() or 0)

    members_res = await db.execute(select(func.count()).select_from(CircleMember))
    total_members = int(members_res.scalar_one() or 0)

    pending_res = await db.execute(
        select(func.count())
        .select_from(CircleAdminRequest)
        .where(CircleAdminRequest.status == STATUS_PENDING)
    )
    pending_ops = int(pending_res.scalar_one() or 0)

    total_hours = await platform_hours_since(db, _month_start())

    return {
        "total_circles": total_circles,
        "total_members": total_members,
        "pending_ops_count": pending_ops,
        "total_hours_month": round(total_hours, 1),
    }


async def admin_circles_summary(db: AsyncSession) -> dict[str, Any]:
    """Full summary including per-member hours — use on circle ops pages, not main dashboard."""
    circles = await list_admin_circles(db)
    pending_res = await db.execute(
        select(func.count())
        .select_from(CircleAdminRequest)
        .where(CircleAdminRequest.status == STATUS_PENDING)
    )
    return {
        "total_circles": len(circles),
        "total_members": sum(c["member_count"] for c in circles),
        "pending_ops_count": int(pending_res.scalar_one() or 0),
        "total_hours_month": round(sum(c["circle_hours_month"] for c in circles), 1),
    }
