"""
Kia RAG context — live data from circle membership, budget, and school students.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.models import CircleMember, SponsorCircle
from app.models.school import SchoolStudent, SchoolStudentEnrollmentRequest, SchoolStudentNarrative
from app.models.signup import SignupRequest
from app.services.circle_budget import _can_set_budget, build_budget_payload
from app.services.school_enrollment_constants import ENROLLMENT_PENDING

logger = logging.getLogger(__name__)


def _mask_student_label(index: int, zenk_id: Optional[str] = None) -> str:
    if zenk_id and str(zenk_id).strip():
        return f"Student {str(zenk_id).strip()}"
    return f"Sponsored student {index + 1}"


def _onboarding_guidance(is_leader: bool, student_count: int, pending_count: int) -> str:
    if student_count > 0:
        if pending_count > 0:
            return (
                f"You have {student_count} active sponsored student(s) and {pending_count} "
                "enrollment request(s) awaiting circle approval. Review pending items in "
                "School Comm or Circle Orders."
            )
        return f"You have {student_count} active sponsored student(s) on record."

    if is_leader:
        return (
            "No sponsored students are linked to this circle yet. Guide the leader to: "
            "(1) open the School Comm tab to connect with their school partner, "
            "(2) approve school enrollment requests, or "
            "(3) use Add Student / school CSV import from the school portal. "
            "Do not invent student names, grades, or scores."
        )
    return (
        "No sponsored students are linked to this circle yet. Guide the member to ask their "
        "circle leader to enroll students via School Comm or school partnership. "
        "Do not invent student names, grades, or scores."
    )


async def _get_circle_name(circle_id: str, db: AsyncSession) -> str:
    try:
        res = await db.execute(select(SponsorCircle).where(SponsorCircle.id == circle_id))
        circle = res.scalar_one_or_none()
        return circle.name if circle else "your circle"
    except Exception:
        return "your circle"


async def _get_member_role(user_id: str, circle_id: str, db: AsyncSession, is_leader: bool) -> str:
    if is_leader:
        return "coordinator"
    try:
        res = await db.execute(
            select(CircleMember).where(
                CircleMember.user_id == user_id,
                CircleMember.circle_id == circle_id,
            )
        )
        member = res.scalar_one_or_none()
        return member.role if member else "member"
    except Exception:
        return "member"


async def _fetch_circle_budget(circle_id: str, user_id: str, db: AsyncSession) -> Optional[dict]:
    try:
        res = await db.execute(
            select(SponsorCircle, CircleMember.role)
            .join(CircleMember, CircleMember.circle_id == SponsorCircle.id)
            .where(
                SponsorCircle.id == circle_id,
                CircleMember.user_id == user_id,
            )
        )
        row = res.first()
        if not row:
            res2 = await db.execute(select(SponsorCircle).where(SponsorCircle.id == circle_id))
            circle = res2.scalar_one_or_none()
            if not circle:
                return None
            return {
                "total_budget": int(circle.annual_budget or 0),
                "spent": int(circle.budget_spent or 0),
                "collected": int(circle.budget_collected or 0),
                "balance_to_spend": max(0, int(circle.annual_budget or 0) - int(circle.budget_spent or 0)),
                "fy_label": circle.fy_label or "FY 2025-26",
            }
        circle, role = row
        payload = build_budget_payload(circle, role)
        return {
            "total_budget": payload["total_budget"],
            "spent": payload["spent"],
            "collected": payload["collected"],
            "balance_to_spend": payload["balance_to_spend"],
            "fy_label": payload["fy_label"],
        }
    except Exception as exc:
        logger.warning("kia_context: budget fetch failed: %s", exc)
        return None


async def _fetch_member_participation(
    circle_id: str, user_id: str, db: AsyncSession
) -> dict[str, Any]:
    """Real roster; participation % is placeholder until activity metrics exist."""
    res = await db.execute(
        select(CircleMember, SignupRequest)
        .join(SignupRequest, SignupRequest.id == CircleMember.user_id)
        .where(CircleMember.circle_id == circle_id)
        .order_by(SignupRequest.full_name)
    )
    rows = res.all()
    if not rows:
        return {"member_count": 0, "my_participation_pct": None, "circle_avg_participation_pct": None}

    pcts = [50 for _ in rows]
    my_pct = 50
    for _cm, signup in rows:
        if signup.id == user_id:
            my_pct = 50
            break
    avg = round(sum(pcts) / len(pcts))
    return {
        "member_count": len(rows),
        "my_participation_pct": my_pct,
        "circle_avg_participation_pct": avg,
        "participation_vs_avg": my_pct - avg,
        "leader_name": next(
            (s.full_name for cm, s in rows if _can_set_budget(cm.role)),
            rows[0][1].full_name if rows else "",
        ),
    }


async def _fetch_circle_students(circle_id: str, db: AsyncSession) -> list[dict]:
    res = await db.execute(
        select(SchoolStudent)
        .where(SchoolStudent.circle_id == circle_id)
        .order_by(SchoolStudent.full_name)
        .limit(20)
    )
    students = res.scalars().all()
    out: list[dict] = []
    for idx, st in enumerate(students):
        narrative = None
        try:
            n_res = await db.execute(
                select(SchoolStudentNarrative)
                .where(SchoolStudentNarrative.student_id == st.id)
                .limit(1)
            )
            narrative = n_res.scalar_one_or_none()
        except Exception:
            pass
        teacher_notes = None
        if narrative and getattr(narrative, "narrative", None):
            teacher_notes = (narrative.narrative or "")[:500]
        elif st.tutor_recommendation:
            teacher_notes = st.tutor_recommendation

        out.append(
            {
                "masked_name": _mask_student_label(idx, st.zenk_id),
                "grade": st.grade,
                "attendance_pct": round(float(st.attendance_pct or 0)),
                "zenq_score": round(float(st.zqa_score or 0)),
                "avg_score": round(float(st.avg_score or 0)),
                "risk_level": st.risk_level,
                "q_report_status": st.q_report_status,
                "teacher_notes": teacher_notes,
                "impact_summary": (
                    f"ZQA score {round(float(st.zqa_score or 0))}; "
                    f"attendance {round(float(st.attendance_pct or 0))}%."
                    if st.zqa_score or st.attendance_pct
                    else None
                ),
            }
        )
    return out


async def _fetch_pending_enrollments(circle_id: str, db: AsyncSession) -> int:
    res = await db.execute(
        select(func.count())
        .select_from(SchoolStudentEnrollmentRequest)
        .where(
            SchoolStudentEnrollmentRequest.circle_id == circle_id,
            SchoolStudentEnrollmentRequest.status == ENROLLMENT_PENDING,
        )
    )
    return int(res.scalar_one() or 0)


async def fetch_user_context(
    user_id: str,
    circle_id: str,
    db: AsyncSession,
    include_private: bool = True,
    is_leader: bool = False,
) -> dict:
    """
    Build live context for Kia from DB. Never injects demo student "Ananya" or fake rankings.
    """
    try:
        circle_name = await _get_circle_name(circle_id, db)
        role = await _get_member_role(user_id, circle_id, db, is_leader)
        budget = await _fetch_circle_budget(circle_id, user_id, db)
        participation = await _fetch_member_participation(circle_id, user_id, db)
        students = await _fetch_circle_students(circle_id, db)
        pending_count = await _fetch_pending_enrollments(circle_id, db)
        student_count = len(students)

        context: dict[str, Any] = {
            "circle_name": circle_name,
            "member_role": role,
            "has_sponsored_students": student_count > 0,
            "sponsored_student_count": student_count,
            "pending_enrollment_count": pending_count,
            "circle_member_count": participation.get("member_count", 0),
            "onboarding_guidance": _onboarding_guidance(is_leader, student_count, pending_count),
            "data_source": "live_database",
        }

        if budget:
            context["circle_budget_summary"] = budget

        if participation.get("member_count"):
            context["my_participation_pct"] = participation.get("my_participation_pct")
            context["circle_avg_participation_pct"] = participation.get("circle_avg_participation_pct")
            context["participation_vs_avg"] = participation.get("participation_vs_avg")
            context["circle_leader_name"] = participation.get("leader_name")

        if students:
            context["sponsored_students"] = students
            context["sponsored_student"] = students[0]
            zqa_vals = [s["zenq_score"] for s in students if s.get("zenq_score") is not None]
            if zqa_vals:
                context["circle_zenq_summary"] = {
                    "average_zqa": round(sum(zqa_vals) / len(zqa_vals)),
                    "student_count": student_count,
                }
        else:
            context["sponsored_students"] = []
            context["sponsored_student"] = None

        if is_leader:
            context["leader_note"] = (
                "You are the Circle Coordinator. Use only the data in this context block. "
                "If there are no students, tell the leader how to add students via School Comm "
                "and enrollment approvals — do not fabricate names or metrics."
            )

        return context

    except Exception as exc:
        logger.warning("kia_context: Failed for user %s: %s", user_id, exc)
        return {
            "circle_name": "your circle",
            "has_sponsored_students": False,
            "onboarding_guidance": _onboarding_guidance(is_leader, 0, 0),
            "data_source": "error_fallback",
        }
