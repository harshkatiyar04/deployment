"""Time-on-impact hours derived from live circle activity (chat, orders, enrollments)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.models import ChatChannel, ChatMessage, CircleMember, GamifiedPersona, SponsorCircle
from app.microservices.vendor.models import VendorOrder
from app.models.school import SchoolStudentEnrollmentRequest
from app.services.school_enrollment_constants import ENROLLMENT_APPROVED
from app.services.sponsor_gamification import _order_clauses_for_circle

# Estimated engagement minutes per activity type (transparent heuristic).
MINUTES_PER_MESSAGE = 3
MINUTES_PER_ORDER = 25
MINUTES_PER_ENROLLMENT_REVIEW = 12


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _month_start(now: datetime | None = None) -> datetime:
    now = now or _utc_now()
    return datetime(now.year, now.month, 1, tzinfo=timezone.utc)


def _since_naive(since: datetime) -> datetime:
    return since.replace(tzinfo=None) if since.tzinfo else since


async def _count_circle_messages(
    db: AsyncSession, circle_id: str, since: datetime
) -> int:
    res = await db.execute(
        select(func.count(ChatMessage.id))
        .select_from(ChatMessage)
        .join(ChatChannel, ChatChannel.id == ChatMessage.channel_id)
        .where(
            ChatChannel.circle_id == circle_id,
            ChatMessage.created_at >= _since_naive(since),
            ChatMessage.hidden_at.is_(None),
            ChatMessage.deleted_at.is_(None),
            ChatMessage.content_text.isnot(None),
            func.length(func.trim(ChatMessage.content_text)) > 0,
        )
    )
    return int(res.scalar() or 0)


async def _count_circle_orders(
    db: AsyncSession, circle: SponsorCircle, since: datetime
) -> int:
    member_res = await db.execute(
        select(CircleMember.user_id).where(CircleMember.circle_id == circle.id)
    )
    member_ids = [r[0] for r in member_res.all()]
    clauses = _order_clauses_for_circle(circle, member_ids)
    if not clauses:
        return 0
    res = await db.execute(
        select(func.count(VendorOrder.id)).where(
            VendorOrder.created_at >= _since_naive(since),
            or_(*clauses),
        )
    )
    return int(res.scalar() or 0)


async def _count_circle_enrollment_reviews(
    db: AsyncSession, circle_id: str, since: datetime
) -> int:
    res = await db.execute(
        select(func.count(SchoolStudentEnrollmentRequest.id)).where(
            SchoolStudentEnrollmentRequest.circle_id == circle_id,
            SchoolStudentEnrollmentRequest.status == ENROLLMENT_APPROVED,
            SchoolStudentEnrollmentRequest.reviewed_at.isnot(None),
            SchoolStudentEnrollmentRequest.reviewed_at >= _since_naive(since),
        )
    )
    return int(res.scalar() or 0)


def _minutes_to_hours(
    messages: int, orders: int, enrollment_reviews: int
) -> float:
    total_min = (
        messages * MINUTES_PER_MESSAGE
        + orders * MINUTES_PER_ORDER
        + enrollment_reviews * MINUTES_PER_ENROLLMENT_REVIEW
    )
    return round(total_min / 60.0, 1)


async def circle_hours_since(
    db: AsyncSession, circle: SponsorCircle, since: datetime
) -> float:
    msgs = await _count_circle_messages(db, circle.id, since)
    orders = await _count_circle_orders(db, circle, since)
    reviews = await _count_circle_enrollment_reviews(db, circle.id, since)
    return _minutes_to_hours(msgs, orders, reviews)


async def platform_hours_since(db: AsyncSession, since: datetime) -> float:
    """Platform-wide impact hours in one pass — for admin dashboard KPIs only."""
    since_naive = _since_naive(since)
    msgs_res = await db.execute(
        select(func.count(ChatMessage.id))
        .select_from(ChatMessage)
        .join(ChatChannel, ChatChannel.id == ChatMessage.channel_id)
        .where(
            ChatMessage.created_at >= since_naive,
            ChatMessage.hidden_at.is_(None),
            ChatMessage.deleted_at.is_(None),
            ChatMessage.content_text.isnot(None),
            func.length(func.trim(ChatMessage.content_text)) > 0,
        )
    )
    orders_res = await db.execute(
        select(func.count(VendorOrder.id)).where(VendorOrder.created_at >= since_naive)
    )
    reviews_res = await db.execute(
        select(func.count(SchoolStudentEnrollmentRequest.id)).where(
            SchoolStudentEnrollmentRequest.status == ENROLLMENT_APPROVED,
            SchoolStudentEnrollmentRequest.reviewed_at.isnot(None),
            SchoolStudentEnrollmentRequest.reviewed_at >= since_naive,
        )
    )
    return _minutes_to_hours(
        int(msgs_res.scalar() or 0),
        int(orders_res.scalar() or 0),
        int(reviews_res.scalar() or 0),
    )


async def _count_user_messages_in_circle(
    db: AsyncSession, user_id: str, circle_id: str, since: datetime
) -> int:
    res = await db.execute(
        select(func.count(ChatMessage.id))
        .select_from(ChatMessage)
        .join(ChatChannel, ChatChannel.id == ChatMessage.channel_id)
        .join(GamifiedPersona, GamifiedPersona.id == ChatMessage.gamified_persona_id)
        .where(
            ChatChannel.circle_id == circle_id,
            GamifiedPersona.user_id == user_id,
            ChatMessage.created_at >= _since_naive(since),
            ChatMessage.hidden_at.is_(None),
            ChatMessage.deleted_at.is_(None),
            ChatMessage.content_text.isnot(None),
            func.length(func.trim(ChatMessage.content_text)) > 0,
        )
    )
    return int(res.scalar() or 0)


async def _count_user_orders_for_circle(
    db: AsyncSession, user_id: str, circle: SponsorCircle, since: datetime
) -> int:
    member_res = await db.execute(
        select(CircleMember.user_id).where(CircleMember.circle_id == circle.id)
    )
    member_ids = [r[0] for r in member_res.all()]
    clauses = _order_clauses_for_circle(circle, member_ids)
    if not clauses:
        return 0
    res = await db.execute(
        select(func.count(VendorOrder.id)).where(
            VendorOrder.buyer_id == user_id,
            VendorOrder.created_at >= _since_naive(since),
            or_(*clauses),
        )
    )
    return int(res.scalar() or 0)


async def _count_user_enrollment_reviews(
    db: AsyncSession, user_id: str, circle_id: str, since: datetime
) -> int:
    res = await db.execute(
        select(func.count(SchoolStudentEnrollmentRequest.id)).where(
            SchoolStudentEnrollmentRequest.circle_id == circle_id,
            SchoolStudentEnrollmentRequest.reviewed_by_user_id == user_id,
            SchoolStudentEnrollmentRequest.status == ENROLLMENT_APPROVED,
            SchoolStudentEnrollmentRequest.reviewed_at.isnot(None),
            SchoolStudentEnrollmentRequest.reviewed_at >= _since_naive(since),
        )
    )
    return int(res.scalar() or 0)


async def member_activity_since(
    db: AsyncSession, user_id: str, circle: SponsorCircle, since: datetime
) -> dict[str, Any]:
    msgs = await _count_user_messages_in_circle(db, user_id, circle.id, since)
    orders = await _count_user_orders_for_circle(db, user_id, circle, since)
    reviews = await _count_user_enrollment_reviews(db, user_id, circle.id, since)
    return {
        "hours": _minutes_to_hours(msgs, orders, reviews),
        "messages_count": msgs,
        "orders_count": orders,
        "enrollment_reviews_count": reviews,
    }


async def build_member_participation(
    db: AsyncSession,
    circle: SponsorCircle,
    *,
    current_user_id: str,
    viewer_role: Optional[str] = None,
) -> dict[str, Any]:
    """Per-member impact hours and share-of-circle % for the participation panel."""
    from app.models.circle_ops import REQUEST_MEMBER_REMOVAL, STATUS_PENDING, CircleAdminRequest
    from app.models.signup import SignupRequest
    from app.services.circle_budget import _can_set_budget
    from app.services.circle_membership_ops import (
        circle_member_limit,
        count_circle_members,
        member_row_flags,
    )
    from app.services.student_circle_privacy import (
        display_name_for_roster,
        is_beneficiary_role,
        sponsored_student_for_circle,
    )

    since = _month_start()
    is_leader_viewer = _can_set_budget(viewer_role)
    res = await db.execute(
        select(CircleMember, SignupRequest)
        .join(SignupRequest, SignupRequest.id == CircleMember.user_id)
        .where(CircleMember.circle_id == circle.id)
        .order_by(SignupRequest.full_name)
    )
    rows = res.all()

    pending_removals: set[str] = set()
    pend_res = await db.execute(
        select(CircleAdminRequest.target_user_id).where(
            CircleAdminRequest.circle_id == circle.id,
            CircleAdminRequest.request_type == REQUEST_MEMBER_REMOVAL,
            CircleAdminRequest.status == STATUS_PENDING,
        )
    )
    for (uid,) in pend_res.all():
        if uid:
            pending_removals.add(uid)

    member_stats: list[dict[str, Any]] = []
    for cm, signup in rows:
        if is_beneficiary_role(cm.role):
            continue
        display_name, initials, role_label = await display_name_for_roster(
            db, signup, cm_role=cm.role or ""
        )
        act = await member_activity_since(db, signup.id, circle, since)
        member_stats.append(
            {
                "user_id": signup.id,
                "name": display_name,
                "initials": initials,
                "role": cm.role,
                "role_label": role_label,
                "is_leader": (cm.role or "").lower() in ("lead", "coordinator", "sponsor_leader"),
                "hours": act["hours"],
                "messages_count": act["messages_count"],
                "orders_count": act["orders_count"],
                "enrollment_reviews_count": act["enrollment_reviews_count"],
            }
        )

    total_hrs = round(sum(m["hours"] for m in member_stats), 1)

    leader_name = ""
    leader_pct = None
    members_out: list[dict[str, Any]] = []

    for m in member_stats:
        if total_hrs > 0:
            pct = int(round(100 * m["hours"] / total_hrs))
        else:
            pct = 0

        if m["is_leader"]:
            leader_name = m["name"]
            leader_pct = pct

        flags = member_row_flags(
            cm_role=m["role"],
            user_id=m["user_id"],
            leader_user_id=current_user_id if is_leader_viewer else "",
            is_leader_viewer=is_leader_viewer,
        )

        members_out.append(
            {
                "user_id": m["user_id"],
                "name": m["name"],
                "initials": m["initials"],
                "participation_pct": pct,
                "badge": "you" if m["user_id"] == current_user_id else "",
                "is_top": False,
                "hours_this_month": m["hours"],
                "messages_count": m["messages_count"],
                "orders_count": m["orders_count"],
                "enrollment_reviews_count": m["enrollment_reviews_count"],
                "role": m["role"],
                "role_label": m.get("role_label"),
                "is_removable": flags["is_removable"],
                "pending_removal": m["user_id"] in pending_removals,
            }
        )

    members_out.sort(key=lambda x: x["hours_this_month"] or 0, reverse=True)
    if members_out and (members_out[0]["hours_this_month"] or 0) > 0:
        members_out[0]["is_top"] = True

    avg_pct = None
    if members_out:
        avg_pct = int(
            round(sum(m["participation_pct"] or 0 for m in members_out) / len(members_out))
        )

    if not leader_name and members_out:
        leader_name = members_out[0]["name"]

    from app.models.circle_ops import REQUEST_MEMBER_LIMIT

    member_count = await count_circle_members(db, circle.id)
    limit = circle_member_limit(circle)
    pend_count_res = await db.execute(
        select(func.count())
        .select_from(CircleAdminRequest)
        .where(
            CircleAdminRequest.circle_id == circle.id,
            CircleAdminRequest.status == STATUS_PENDING,
        )
    )
    pending_admin = int(pend_count_res.scalar_one() or 0)
    has_pending_limit = await db.execute(
        select(CircleAdminRequest.id)
        .where(
            CircleAdminRequest.circle_id == circle.id,
            CircleAdminRequest.request_type == REQUEST_MEMBER_LIMIT,
            CircleAdminRequest.status == STATUS_PENDING,
        )
        .limit(1)
    )

    sponsored_student = await sponsored_student_for_circle(db, circle.id)

    return {
        "members": members_out,
        "sponsored_student": sponsored_student,
        "circle_avg_pct": avg_pct,
        "leader_name": leader_name,
        "leader_pct": leader_pct,
        "circle_total_hrs": total_hrs,
        "period_label": since.strftime("%B %Y"),
        "metrics_available": True,
        "message": (
            "Member hours are estimated from chat, marketplace orders, and enrollment "
            "approvals this month. Visible to everyone in your circle."
        ),
        "member_count": member_count,
        "member_limit": limit,
        "is_leader": is_leader_viewer,
        "can_request_limit_increase": is_leader_viewer
        and member_count >= limit
        and has_pending_limit.scalar_one_or_none() is None,
        "pending_admin_requests": pending_admin,
    }


def _time_impact_unavailable(
    message: str,
    *,
    has_enrolled_student: bool = False,
) -> dict[str, Any]:
    return {
        "metrics_available": False,
        "has_enrolled_student": has_enrolled_student,
        "message": message,
        "total_hrs_all_circles": 0,
        "total_circles_count": 0,
        "highest_circle_hrs": 0.0,
        "highest_circle_name": None,
        "my_circle_hrs": 0.0,
    }


async def build_time_impact(
    db: AsyncSession, circle_id: str
) -> dict[str, Any]:
    """Time-on-impact for one circle this calendar month (student-linked circles only)."""
    from app.services.circle_student_enrollment_gate import circle_enrolled_student_count

    since = _month_start()

    circle_res = await db.execute(
        select(SponsorCircle).where(SponsorCircle.id == circle_id)
    )
    circle = circle_res.scalar_one_or_none()
    if not circle:
        return _time_impact_unavailable("Circle not found.")

    enrolled = await circle_enrolled_student_count(db, circle_id)
    if enrolled < 1:
        return _time_impact_unavailable(
            "Time on impact unlocks after a school enrolls a sponsored student in your circle. "
            "Setup chat and leader onboarding are not counted.",
            has_enrolled_student=False,
        )

    my_hrs = await circle_hours_since(db, circle, since)
    if my_hrs <= 0:
        return _time_impact_unavailable(
            "No impact activity this month yet. Hours appear when members chat about the "
            "sponsored student, place student-fund orders, or approve school enrollments.",
            has_enrolled_student=True,
        )

    # Benchmark only among circles that also have enrolled students this month.
    peer_res = await db.execute(
        select(SponsorCircle).where(SponsorCircle.status == "active")
    )
    peer_circles = list(peer_res.scalars().all())

    per_circle: list[tuple[str, str, float]] = []
    total_hrs = 0.0
    for c in peer_circles:
        if await circle_enrolled_student_count(db, c.id) < 1:
            continue
        hrs = await circle_hours_since(db, c, since)
        if hrs <= 0:
            continue
        per_circle.append((c.id, c.name, hrs))
        total_hrs += hrs

    total_hrs = round(total_hrs, 1)
    highest_name: Optional[str] = None
    highest_hrs = 0.0
    if per_circle:
        _cid, highest_name, highest_hrs = max(per_circle, key=lambda x: x[2])

    activity_note = (
        "Estimated from circle chat, student-fund marketplace orders, and school "
        "enrollment reviews this month (sponsored-student circles only)."
    )

    return {
        "metrics_available": True,
        "has_enrolled_student": True,
        "message": activity_note,
        "total_hrs_all_circles": int(round(total_hrs)),
        "total_circles_count": len(per_circle),
        "highest_circle_hrs": highest_hrs,
        "highest_circle_name": highest_name,
        "my_circle_hrs": my_hrs,
    }
