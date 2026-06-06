"""Sponsor profile badges and engagement streaks — computed from live DB activity."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.models import ChatChannel, ChatMessage, CircleMember, GamifiedPersona, SponsorCircle
from app.microservices.vendor.models import VendorOrder
from app.models.school import SchoolStudent, SchoolStudentEnrollmentRequest
from app.models.signup import SignupRequest
from app.services.circle_budget import LEADER_ROLES
from app.services.school_enrollment_constants import ENROLLMENT_APPROVED

BADGE_CATALOG: tuple[dict[str, str], ...] = (
    {
        "id": "circle_member",
        "title": "Circle Member",
        "description": "You belong to an active sponsor circle.",
        "icon": "users",
    },
    {
        "id": "verified_sponsor",
        "title": "Verified Sponsor",
        "description": "KYC approved — ready to place student-fund orders.",
        "icon": "shield",
    },
    {
        "id": "first_contribution",
        "title": "First Contribution",
        "description": "Placed your first marketplace order for the circle.",
        "icon": "cart",
    },
    {
        "id": "marketplace_ally",
        "title": "Marketplace Ally",
        "description": "Three or more marketplace orders (this account).",
        "icon": "sparkles",
    },
    {
        "id": "circle_voice",
        "title": "Circle Voice",
        "description": "Five or more messages in this circle's chat (last 90 days).",
        "icon": "chat",
    },
    {
        "id": "school_connector",
        "title": "School Connector",
        "description": "Your circle has students enrolled from partner schools.",
        "icon": "school",
    },
    {
        "id": "enrollment_champion",
        "title": "Enrollment Champion",
        "description": "You approved at least one school enrollment into the circle.",
        "icon": "check",
    },
    {
        "id": "impact_leader",
        "title": "Impact Leader",
        "description": "Serving as circle leader or coordinator.",
        "icon": "star",
    },
    {
        "id": "student_momentum",
        "title": "Student Momentum",
        "description": "A sponsored student in your circle reached ZQA 70+.",
        "icon": "chart",
    },
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None) -> Optional[str]:
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _week_key(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    iso = dt.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _consecutive_weeks_back(week_keys: set[str], *, from_dt: datetime) -> int:
    """How many consecutive ISO weeks (including from_dt's week) have activity."""
    count = 0
    cursor = from_dt
    for _ in range(52):
        if _week_key(cursor) not in week_keys:
            break
        count += 1
        cursor = cursor - timedelta(days=7)
    return count


def _streak_weeks_display(week_keys: set[str], *, from_dt: datetime) -> int:
    """
    Streak shown to users: consecutive active weeks, but 0 if only the current
    week has activity (still building — need last week + this week for week 1).
    """
    total = _consecutive_weeks_back(week_keys, from_dt=from_dt)
    if total == 0:
        return 0
    current_key = _week_key(from_dt)
    if total == 1 and current_key in week_keys:
        prior_key = _week_key(from_dt - timedelta(days=7))
        if prior_key not in week_keys:
            return 0
    return total


async def _user_circle_role(db: AsyncSession, user_id: str, circle_id: str) -> Optional[str]:
    res = await db.execute(
        select(CircleMember.role).where(
            CircleMember.circle_id == circle_id,
            CircleMember.user_id == user_id,
        )
    )
    row = res.first()
    return row[0] if row else None


async def _member_joined_at(db: AsyncSession, user_id: str, circle_id: str) -> Optional[datetime]:
    res = await db.execute(
        select(CircleMember.joined_at).where(
            CircleMember.circle_id == circle_id,
            CircleMember.user_id == user_id,
        )
    )
    row = res.first()
    return row[0] if row else None


async def _count_user_messages(db: AsyncSession, user_id: str, circle_id: str, since: datetime) -> int:
    res = await db.execute(
        select(func.count(ChatMessage.id))
        .select_from(ChatMessage)
        .join(ChatChannel, ChatChannel.id == ChatMessage.channel_id)
        .join(GamifiedPersona, GamifiedPersona.id == ChatMessage.gamified_persona_id)
        .where(
            ChatChannel.circle_id == circle_id,
            GamifiedPersona.user_id == user_id,
            ChatMessage.created_at >= since,
            ChatMessage.hidden_at.is_(None),
            ChatMessage.deleted_at.is_(None),
            ChatMessage.content_text.isnot(None),
            func.length(func.trim(ChatMessage.content_text)) > 0,
        )
    )
    return int(res.scalar() or 0)


async def _nth_message_at(
    db: AsyncSession, user_id: str, circle_id: str, n: int, since: datetime
) -> Optional[datetime]:
    res = await db.execute(
        select(ChatMessage.created_at)
        .join(ChatChannel, ChatChannel.id == ChatMessage.channel_id)
        .join(GamifiedPersona, GamifiedPersona.id == ChatMessage.gamified_persona_id)
        .where(
            ChatChannel.circle_id == circle_id,
            GamifiedPersona.user_id == user_id,
            ChatMessage.created_at >= since,
            ChatMessage.hidden_at.is_(None),
            ChatMessage.deleted_at.is_(None),
            ChatMessage.content_text.isnot(None),
            func.length(func.trim(ChatMessage.content_text)) > 0,
        )
        .order_by(ChatMessage.created_at.asc())
        .offset(n - 1)
        .limit(1)
    )
    row = res.first()
    return row[0] if row else None


async def _count_user_orders(db: AsyncSession, user_id: str) -> int:
    res = await db.execute(
        select(func.count(VendorOrder.id)).where(VendorOrder.buyer_id == user_id)
    )
    return int(res.scalar() or 0)


async def _nth_order_at(db: AsyncSession, user_id: str, n: int) -> Optional[datetime]:
    res = await db.execute(
        select(VendorOrder.created_at)
        .where(VendorOrder.buyer_id == user_id)
        .order_by(VendorOrder.created_at.asc())
        .offset(n - 1)
        .limit(1)
    )
    row = res.first()
    return row[0] if row else None


def _order_clauses_for_circle(circle: SponsorCircle, member_ids: list[str]):
    clauses = []
    if circle.name:
        clauses.append(VendorOrder.circle_name == circle.name)
    if member_ids:
        clauses.append(
            (VendorOrder.buyer_id.in_(member_ids)) & (VendorOrder.order_type == "student")
        )
    return clauses


async def _user_activity_weeks_in_circle(
    db: AsyncSession, user_id: str, circle: SponsorCircle
) -> set[str]:
    """Weeks with real chat in this circle or orders tied to this circle."""
    since = _utc_now() - timedelta(days=90)
    weeks: set[str] = set()
    circle_id = circle.id

    msg_res = await db.execute(
        select(ChatMessage.created_at)
        .join(ChatChannel, ChatChannel.id == ChatMessage.channel_id)
        .join(GamifiedPersona, GamifiedPersona.id == ChatMessage.gamified_persona_id)
        .where(
            ChatChannel.circle_id == circle_id,
            GamifiedPersona.user_id == user_id,
            ChatMessage.created_at >= since,
            ChatMessage.hidden_at.is_(None),
            ChatMessage.deleted_at.is_(None),
            ChatMessage.content_text.isnot(None),
            func.length(func.trim(ChatMessage.content_text)) > 0,
        )
    )
    for (created_at,) in msg_res.all():
        if created_at:
            weeks.add(_week_key(created_at))

    member_res = await db.execute(
        select(CircleMember.user_id).where(CircleMember.circle_id == circle_id)
    )
    member_ids = [r[0] for r in member_res.all()]
    clauses = _order_clauses_for_circle(circle, member_ids)
    if clauses:
        order_res = await db.execute(
            select(VendorOrder.created_at).where(
                VendorOrder.buyer_id == user_id,
                VendorOrder.created_at >= since,
                or_(*clauses),
            )
        )
        for (created_at,) in order_res.all():
            if created_at:
                weeks.add(_week_key(created_at))

    return weeks


async def _circle_marketplace_weeks(db: AsyncSession, circle: SponsorCircle) -> set[str]:
    since = _utc_now() - timedelta(days=90)
    weeks: set[str] = set()
    member_res = await db.execute(
        select(CircleMember.user_id).where(CircleMember.circle_id == circle.id)
    )
    member_ids = [r[0] for r in member_res.all()]
    clauses = _order_clauses_for_circle(circle, member_ids)
    if not clauses:
        return weeks
    res = await db.execute(
        select(VendorOrder.created_at).where(
            VendorOrder.created_at >= since,
            or_(*clauses),
        )
    )
    for (created_at,) in res.all():
        if created_at:
            weeks.add(_week_key(created_at))
    return weeks


async def compute_sponsor_gamification(
    db: AsyncSession,
    *,
    circle: SponsorCircle,
    user: SignupRequest,
) -> dict[str, Any]:
    """Return badge catalog with earned flags and engagement streaks from DB facts."""
    now = _utc_now()
    since_90d = now - timedelta(days=90)
    role = await _user_circle_role(db, user.id, circle.id)
    is_leader = (role or "").lower() in LEADER_ROLES or role == "sponsor_leader"
    joined_at = await _member_joined_at(db, user.id, circle.id)

    msg_90d = await _count_user_messages(db, user.id, circle.id, since_90d)
    order_count = await _count_user_orders(db, user.id)

    student_res = await db.execute(
        select(func.count(SchoolStudent.id)).where(SchoolStudent.circle_id == circle.id)
    )
    student_count = int(student_res.scalar() or 0)

    first_student_res = await db.execute(
        select(SchoolStudent.created_at)
        .where(SchoolStudent.circle_id == circle.id)
        .order_by(SchoolStudent.created_at.asc())
        .limit(1)
    )
    first_student_at = first_student_res.scalar_one_or_none()

    zqa_student_res = await db.execute(
        select(SchoolStudent.created_at)
        .where(
            SchoolStudent.circle_id == circle.id,
            SchoolStudent.zqa_score >= 70,
        )
        .order_by(SchoolStudent.zqa_score.desc())
        .limit(1)
    )
    zqa_student_at = zqa_student_res.scalar_one_or_none()

    approved_res = await db.execute(
        select(SchoolStudentEnrollmentRequest.reviewed_at, SchoolStudentEnrollmentRequest.requested_at)
        .where(
            SchoolStudentEnrollmentRequest.circle_id == circle.id,
            SchoolStudentEnrollmentRequest.status == ENROLLMENT_APPROVED,
        )
        .order_by(SchoolStudentEnrollmentRequest.reviewed_at.asc().nulls_last())
        .limit(1)
    )
    approved_row = approved_res.first()
    first_approval_at = None
    if approved_row:
        first_approval_at = approved_row[0] or approved_row[1]

    kyc = (user.kyc_status.value if hasattr(user.kyc_status, "value") else str(user.kyc_status or "")).lower()
    kyc_ok = kyc == "approved"

    first_order_at = await _nth_order_at(db, user.id, 1) if order_count >= 1 else None
    third_order_at = await _nth_order_at(db, user.id, 3) if order_count >= 3 else None
    fifth_msg_at = await _nth_message_at(db, user.id, circle.id, 5, since_90d) if msg_90d >= 5 else None

    earned_map: dict[str, bool] = {
        "circle_member": joined_at is not None,
        "verified_sponsor": kyc_ok,
        "first_contribution": order_count >= 1,
        "marketplace_ally": order_count >= 3,
        "circle_voice": msg_90d >= 5,
        "school_connector": student_count >= 1,
        "enrollment_champion": is_leader and first_approval_at is not None,
        "impact_leader": is_leader,
        "student_momentum": zqa_student_at is not None,
    }

    earned_at_map: dict[str, Optional[str]] = {
        "circle_member": _iso(joined_at),
        "verified_sponsor": None,  # no reviewed_at on signup row
        "first_contribution": _iso(first_order_at),
        "marketplace_ally": _iso(third_order_at),
        "circle_voice": _iso(fifth_msg_at),
        "school_connector": _iso(first_student_at),
        "enrollment_champion": _iso(first_approval_at) if is_leader else None,
        "impact_leader": _iso(joined_at) if is_leader else None,
        "student_momentum": _iso(zqa_student_at),
    }

    progress_map: dict[str, dict] = {
        "marketplace_ally": {"current": order_count, "target": 3, "label": "orders"},
        "circle_voice": {"current": msg_90d, "target": 5, "label": "messages in circle"},
        "first_contribution": {"current": order_count, "target": 1, "label": "orders"},
    }

    badges: list[dict] = []
    for spec in BADGE_CATALOG:
        earned = earned_map.get(spec["id"], False)
        prog = progress_map.get(spec["id"])
        badges.append(
            {
                **spec,
                "earned": earned,
                "earned_at": earned_at_map.get(spec["id"]) if earned else None,
                "progress_current": prog["current"] if prog and not earned else None,
                "progress_target": prog["target"] if prog and not earned else None,
                "progress_label": prog["label"] if prog and not earned else None,
            }
        )

    activity_weeks = await _user_activity_weeks_in_circle(db, user.id, circle)
    circle_order_weeks = await _circle_marketplace_weeks(db, circle)
    current_week = _week_key(now)
    active_this_week = current_week in activity_weeks
    streak_weeks = _streak_weeks_display(activity_weeks, from_dt=now)
    circle_streak = _streak_weeks_display(circle_order_weeks, from_dt=now)
    circle_active_week = current_week in circle_order_weeks

    streaks = [
        {
            "id": "engagement",
            "label": "Your engagement streak",
            "current": streak_weeks,
            "unit": "week",
            "active_this_week": active_this_week,
            "building_this_week": active_this_week and streak_weeks == 0,
            "next_milestone": 4 if streak_weeks < 4 else 8,
            "hint": (
                "You're active this week — stay engaged next week to start a 1-week streak."
                if active_this_week and streak_weeks == 0
                else "Chat in this circle or place a circle-linked order each week to build your streak."
            ),
        },
        {
            "id": "circle_impact",
            "label": "Circle marketplace streak",
            "current": circle_streak,
            "unit": "week",
            "active_this_week": circle_active_week,
            "building_this_week": circle_active_week and circle_streak == 0,
            "next_milestone": 4,
            "hint": (
                "Your circle ordered this week — another active week in a row starts the streak."
                if circle_active_week and circle_streak == 0
                else "Consecutive weeks where your circle places at least one marketplace order."
            ),
        },
    ]

    earned_count = sum(1 for b in badges if b["earned"])

    return {
        "badges": badges,
        "badges_available": True,
        "badges_earned_count": earned_count,
        "badges_total": len(badges),
        "streaks": streaks,
    }
