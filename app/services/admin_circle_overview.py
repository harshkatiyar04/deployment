"""Admin overview of all sponsor circles — roster, activity, ops queue context."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.models import CircleMember, SponsorCircle
from app.models.circle_ops import (
    CircleAdminRequest,
    REQUEST_MEMBER_REMOVAL,
    REQUEST_TYPES_MEMBERSHIP,
    STATUS_PENDING,
)
from app.models.signup import SignupRequest
from app.services.circle_membership_ops import circle_member_limit
from app.services.student_circle_privacy import BENEFICIARY_ROLE
from app.services.sponsor_circle_time_impact import (
    _allocate_percentages,
    _minutes_as_hours,
    _month_start,
    batch_circle_minutes_since,
    batch_member_activity_for_circle,
    platform_minutes_since,
)

LEADER_ROLES = frozenset({"lead", "sponsor_leader", "coordinator"})


def _iso(dt) -> Optional[str]:
    if not dt:
        return None
    return dt.isoformat()


def _is_beneficiary(role: Optional[str]) -> bool:
    return (role or "").lower() == BENEFICIARY_ROLE


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
            CircleAdminRequest.request_type.in_(sorted(REQUEST_TYPES_MEMBERSHIP)),
        )
    )
    return int(res.scalar_one() or 0)


async def list_admin_circles(db: AsyncSession) -> list[dict[str, Any]]:
    res = await db.execute(
        select(SponsorCircle).order_by(SponsorCircle.created_at.desc())
    )
    circles = list(res.scalars().all())
    if not circles:
        return []

    circle_ids = [c.id for c in circles]
    since = _month_start()

    mc_res = await db.execute(
        select(CircleMember.circle_id, func.count())
        .where(
            CircleMember.circle_id.in_(circle_ids),
            func.lower(CircleMember.role) != BENEFICIARY_ROLE,
        )
        .group_by(CircleMember.circle_id)
    )
    member_counts = {cid: int(cnt) for cid, cnt in mc_res.all()}

    leader_res = await db.execute(
        select(CircleMember.circle_id, SignupRequest.full_name)
        .join(SignupRequest, SignupRequest.id == CircleMember.user_id)
        .where(
            CircleMember.circle_id.in_(circle_ids),
            CircleMember.role.in_(list(LEADER_ROLES)),
        )
        .order_by(CircleMember.joined_at.asc())
    )
    leader_names: dict[str, str] = {}
    for cid, name in leader_res.all():
        leader_names.setdefault(cid, name)

    pend_res = await db.execute(
        select(CircleAdminRequest.circle_id, func.count())
        .where(
            CircleAdminRequest.circle_id.in_(circle_ids),
            CircleAdminRequest.status == STATUS_PENDING,
            CircleAdminRequest.request_type.in_(sorted(REQUEST_TYPES_MEMBERSHIP)),
        )
        .group_by(CircleAdminRequest.circle_id)
    )
    pending_counts = {cid: int(cnt) for cid, cnt in pend_res.all()}

    minutes_by_circle = await batch_circle_minutes_since(db, circles, since)

    out: list[dict[str, Any]] = []
    for circle in circles:
        mins = int(minutes_by_circle.get(circle.id, 0) or 0)
        out.append(
            {
                "id": circle.id,
                "name": circle.name,
                "status": circle.status,
                "member_count": member_counts.get(circle.id, 0),
                "member_limit": circle_member_limit(circle),
                "created_at": _iso(circle.created_at),
                "leader_name": leader_names.get(circle.id),
                "circle_minutes_month": mins,
                "circle_hours_month": _minutes_as_hours(mins),
                "pending_ops_count": pending_counts.get(circle.id, 0),
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
    member_rows = members_res.all()
    user_ids = [signup.id for _, signup in member_rows]
    activity_by_user = await batch_member_activity_for_circle(
        db, circle, user_ids, since
    )
    # Same source as the list Activity column (circle-wide, not sum of seats).
    minutes_map = await batch_circle_minutes_since(db, [circle], since)
    circle_minutes = int(minutes_map.get(circle.id, 0) or 0)

    members_out: list[dict[str, Any]] = []
    minute_parts: list[int] = []
    for cm, signup in member_rows:
        act = activity_by_user.get(signup.id, {})
        mins = int(act.get("minutes") or 0)
        minute_parts.append(mins)
        members_out.append(
            {
                "user_id": signup.id,
                "name": signup.full_name or "Member",
                "email": signup.email,
                "role": cm.role,
                "joined_at": _iso(cm.joined_at),
                "minutes_this_month": mins,
                "hours_this_month": _minutes_as_hours(mins),
                "messages_count": act.get("messages_count", 0),
                "orders_count": act.get("orders_count", 0),
                "enrollment_reviews_count": act.get("enrollment_reviews_count", 0),
            }
        )

    pcts = _allocate_percentages(minute_parts)
    pending_removals = await db.execute(
        select(CircleAdminRequest.target_user_id).where(
            CircleAdminRequest.circle_id == circle.id,
            CircleAdminRequest.request_type == REQUEST_MEMBER_REMOVAL,
            CircleAdminRequest.status == STATUS_PENDING,
        )
    )
    pending_removal_ids = {uid for (uid,) in pending_removals.all() if uid}

    for i, m in enumerate(members_out):
        m["pending_removal"] = m["user_id"] in pending_removal_ids
        m["participation_pct"] = pcts[i] if i < len(pcts) else 0

    members_out.sort(key=lambda x: x["minutes_this_month"], reverse=True)
    seat_count = sum(1 for cm, _ in member_rows if not _is_beneficiary(cm.role))

    return {
        "id": circle.id,
        "name": circle.name,
        "status": circle.status,
        "description": circle.description,
        "member_count": seat_count,
        "member_limit": circle_member_limit(circle),
        "created_at": _iso(circle.created_at),
        "leader_name": await _circle_leader_name(db, circle.id),
        "circle_minutes_month": circle_minutes,
        "circle_hours_month": _minutes_as_hours(circle_minutes),
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
        .where(
            CircleAdminRequest.status == STATUS_PENDING,
            CircleAdminRequest.request_type.in_(sorted(REQUEST_TYPES_MEMBERSHIP)),
        )
    )
    pending_ops = int(pending_res.scalar_one() or 0)

    total_minutes = await platform_minutes_since(db, _month_start())

    return {
        "total_circles": total_circles,
        "total_members": total_members,
        "pending_ops_count": pending_ops,
        "total_minutes_month": int(total_minutes or 0),
        "total_hours_month": _minutes_as_hours(total_minutes),
    }


async def admin_circles_summary(db: AsyncSession) -> dict[str, Any]:
    """KPI strip for circle ops — aggregate counts only (no per-circle roster loop)."""
    return await admin_circles_summary_light(db)


async def admin_circle_ops_page_bundle(db: AsyncSession) -> dict[str, Any]:
    """Single round-trip payload for the admin Circle Ops page."""
    from app.services.circle_membership_ops import list_pending_membership_ops_queue

    # AsyncSession is not safe for concurrent use — load sequentially.
    circles = await list_admin_circles(db)
    pending = await list_pending_membership_ops_queue(db)
    total_minutes = sum(int(c.get("circle_minutes_month") or 0) for c in circles)
    summary = {
        "total_circles": len(circles),
        "total_members": sum(c["member_count"] for c in circles),
        "pending_ops_count": len(pending),
        "total_minutes_month": total_minutes,
        "total_hours_month": _minutes_as_hours(total_minutes),
    }
    return {
        "summary": summary,
        "circles": circles,
        "pending": pending,
    }
