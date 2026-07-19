"""Live sponsor circle overview metrics (no placeholders)."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.models import CircleMember, SponsorCircle
from app.core.settings import settings
from app.models.school import SchoolStudent, SchoolStudentEnrollmentRequest
from app.models.signup import SignupRequest
from app.services.circle_budget import _can_set_budget, build_budget_payload
from app.services.school_enrollment_constants import ENROLLMENT_PENDING
from app.services.circle_membership_ops import circle_member_limit, count_circle_members
from app.services.sponsor_circle_time_impact import (
    _minutes_as_hours,
    build_member_participation,
    build_time_impact,
)
from app.services.zenq_public_scores import list_engine_league_rows, resolve_circle_zenq_display
from app.services.zenq_score_display import build_sponsor_scoreboard


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

    zenq_display = await resolve_circle_zenq_display(
        db,
        circle_id,
        student_count=student_count,
        materialize_if_missing=settings.zenq_engine_enabled,
    )

    time_data = await build_time_impact(db, circle_id)
    participation_data = await build_member_participation(
        db, circle, current_user_id=user_id
    )
    my_pct = 0
    my_hours = 0.0
    for m in participation_data.get("members", []):
        if m.get("badge") == "you":
            my_pct = int(m.get("participation_pct") or 0)
            my_hours = float(m.get("hours_this_month") or 0)
            break

    # Same source as Active Members total (seat holders only) — not circle-wide
    # chat that also includes student / non-roster messages.
    roster_minutes = int(participation_data.get("circle_total_minutes") or 0)
    roster_hrs = participation_data.get("circle_total_hrs")
    if roster_hrs is None:
        roster_hrs = _minutes_as_hours(roster_minutes)

    # Peer "top group" is circle-wide; if we are that top circle, match the roster
    # figure so the card never shows a higher "Top group" than our own total.
    my_wide = int(time_data.get("my_circle_minutes") or 0)
    highest = int(time_data.get("highest_circle_minutes") or 0)
    if highest > 0 and my_wide >= highest:
        top_minutes = roster_minutes
        top_hrs = roster_hrs
    else:
        top_minutes = highest
        top_hrs = time_data.get("highest_circle_hrs")

    scoreboard = await build_sponsor_scoreboard(
        db,
        circle_id=circle_id,
        user_id=user_id,
        zenq_display=zenq_display,
        activity={
            "participation_pct": my_pct,
            "hours_this_month": my_hours,
        },
    )

    league = await list_engine_league_rows(db, circle_id)
    my_league = next((r for r in league if r.get("is_mine")), None)
    circle_rank = int(my_league["rank"]) if my_league else None
    total_circles = len(league) if league else None

    return {
        "circle_id": circle.id,
        "circle_name": circle.name,
        "is_leader": _can_set_budget(role),
        "member_count": member_count,
        "student_count": student_count,
        "pending_enrollment_count": pending_enrollment_count,
        "zenq_score": zenq_display.get("zenq_score"),
        "zenq_available": bool(zenq_display.get("zenq_available")),
        "zenq_source": zenq_display.get("zenq_source"),
        "zenq_change": zenq_display.get("zenq_change"),
        "zenq_breakdown": zenq_display.get("zenq_breakdown"),
        "zenq_scoreboard": scoreboard,
        "legacy_zqa_avg": zenq_display.get("legacy_zqa_avg"),
        "circle_rank": circle_rank,
        "total_circles": total_circles,
        "participation_pct": my_pct,
        "circle_avg_pct": int(participation_data.get("circle_avg_pct") or 0),
        "participation_vs_avg": my_pct - int(participation_data.get("circle_avg_pct") or 0),
        "participation_available": participation_data.get("metrics_available", True),
        "time_this_month_hrs": roster_hrs,
        "time_this_month_minutes": roster_minutes,
        "top_group_hrs": top_hrs,
        "top_group_minutes": top_minutes,
        "rank_previous": None,
        "budget": {
            "total_budget": budget["total_budget"],
            "spent": budget["spent"],
            "collected": budget["collected"],
            "available_balance": budget["available_balance"],
            "remaining_target": budget["remaining_target"],
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
