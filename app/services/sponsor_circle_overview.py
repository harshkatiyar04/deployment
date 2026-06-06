"""Live sponsor circle overview metrics (no placeholders)."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.models import CircleMember, SponsorCircle
from app.models.school import SchoolStudent, SchoolStudentEnrollmentRequest
from app.models.signup import SignupRequest
from app.services.circle_budget import _can_set_budget, build_budget_payload
from app.services.school_enrollment_constants import ENROLLMENT_PENDING
from app.services.circle_membership_ops import circle_member_limit, count_circle_members
from app.services.sponsor_circle_time_impact import build_time_impact, build_member_participation


async def build_circle_overview(
    db: AsyncSession,
    user_id: str,
    circle_id: str,
) -> dict[str, Any]:
    circle_res = await db.execute(
        select(SponsorCircle, CircleMember.role)
        .join(CircleMember, CircleMember.circle_id == SponsorCircle.id)
        .where(
            SponsorCircle.id == circle_id,
            CircleMember.user_id == user_id,
        )
    )
    row = circle_res.first()
    if not row:
        raise ValueError("not_a_member")
    circle, role = row
    budget = build_budget_payload(circle, role)

    member_count = await count_circle_members(db, circle_id)

    student_res = await db.execute(
        select(func.count()).select_from(SchoolStudent).where(SchoolStudent.circle_id == circle_id)
    )
    student_count = int(student_res.scalar_one() or 0)

    pending_enroll = await db.execute(
        select(func.count())
        .select_from(SchoolStudentEnrollmentRequest)
        .where(
            SchoolStudentEnrollmentRequest.circle_id == circle_id,
            SchoolStudentEnrollmentRequest.status == ENROLLMENT_PENDING,
        )
    )
    pending_enrollment_count = int(pending_enroll.scalar_one() or 0)

    zqa_avg: Optional[float] = None
    if student_count > 0:
        avg_res = await db.execute(
            select(func.avg(SchoolStudent.zqa_score)).where(SchoolStudent.circle_id == circle_id)
        )
        raw = avg_res.scalar_one()
        if raw is not None:
            zqa_avg = round(float(raw), 1)

    time_data = await build_time_impact(db, circle_id)
    participation_data = await build_member_participation(
        db, circle, current_user_id=user_id
    )
    my_pct = 0
    for m in participation_data.get("members", []):
        if m.get("badge") == "you":
            my_pct = int(m.get("participation_pct") or 0)
            break

    return {
        "circle_id": circle.id,
        "circle_name": circle.name,
        "is_leader": _can_set_budget(role),
        "member_count": member_count,
        "student_count": student_count,
        "pending_enrollment_count": pending_enrollment_count,
        "zenq_score": int(zqa_avg) if zqa_avg is not None else None,
        "zenq_available": student_count > 0,
        "circle_rank": None,
        "total_circles": None,
        "participation_pct": my_pct,
        "circle_avg_pct": int(participation_data.get("circle_avg_pct") or 0),
        "participation_vs_avg": my_pct - int(participation_data.get("circle_avg_pct") or 0),
        "participation_available": participation_data.get("metrics_available", True),
        "time_this_month_hrs": time_data.get("my_circle_hrs"),
        "top_group_hrs": time_data.get("highest_circle_hrs"),
        "zenq_change": None,
        "rank_previous": None,
        "budget": {
            "total_budget": budget["total_budget"],
            "spent": budget["spent"],
            "collected": budget["collected"],
            "balance_to_spend": budget["balance_to_spend"],
            "fy_label": budget["fy_label"],
        },
        "has_students": student_count > 0,
        "member_limit": circle_member_limit(circle),
        "onboarding_hint": (
            None
            if student_count > 0
            else "No sponsored students yet. Leaders: use School Comm to approve school enrollments."
        ),
    }
