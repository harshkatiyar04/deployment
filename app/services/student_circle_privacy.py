"""Pseudonym-first student visibility for sponsor circle surfaces."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.gamified_persona import get_or_create_persona
from app.chat.models import CircleMember
from app.models.enums import MemberKind, Persona
from app.models.school import SchoolStudent
from app.models.signup import SignupRequest

BENEFICIARY_ROLE = "student"


def is_beneficiary_role(role: Optional[str]) -> bool:
    return (role or "").lower() == BENEFICIARY_ROLE


def roster_role_label(signup: SignupRequest, cm_role: str) -> str:
    if is_beneficiary_role(cm_role):
        return "Sponsored student"
    if signup.member_kind == MemberKind.parent_guardian.value:
        return "Parent / guardian"
    role = (cm_role or "").lower()
    if role in ("lead", "sponsor_leader", "coordinator"):
        return "Circle leader"
    if role == "sponsor":
        return "Sponsor member"
    if role == "mentor":
        return "Mentor"
    return cm_role or "Member"


def _initials_from_label(label: str) -> str:
    parts = (label or "?").replace("_", " ").split()
    if not parts:
        return "?"
    if len(parts) == 1:
        text = parts[0]
        return (text[:2] or "?").upper()
    return "".join(p[0] for p in parts[:2]).upper()


async def count_circle_seats(db: AsyncSession, circle_id: str) -> int:
    """Member cap seats — excludes sponsored student beneficiary."""
    res = await db.execute(
        select(func.count())
        .select_from(CircleMember)
        .where(
            CircleMember.circle_id == circle_id,
            func.lower(CircleMember.role) != BENEFICIARY_ROLE,
        )
    )
    return int(res.scalar_one() or 0)


async def display_name_for_roster(
    db: AsyncSession,
    signup: SignupRequest,
    *,
    cm_role: str,
) -> tuple[str, str, str]:
    """Return (display_name, initials, role_label)."""
    role_label = roster_role_label(signup, cm_role)
    if is_beneficiary_role(cm_role) or signup.persona == Persona.student:
        persona = await get_or_create_persona(signup, db)
        return persona.nickname, _initials_from_label(persona.nickname), role_label
    if signup.member_kind == MemberKind.parent_guardian.value:
        return "Parent / guardian", "PG", role_label
    name = signup.full_name or "Member"
    return name, _initials_from_label(name), role_label


async def resolve_student_signup_for_school_row(
    db: AsyncSession,
    school_student: SchoolStudent,
) -> Optional[SignupRequest]:
    if school_student.signup_request_id:
        res = await db.execute(
            select(SignupRequest).where(SignupRequest.id == school_student.signup_request_id)
        )
        row = res.scalar_one_or_none()
        if row:
            return row
    if school_student.zenk_id:
        res = await db.execute(select(SignupRequest).where(SignupRequest.id == school_student.zenk_id))
        row = res.scalar_one_or_none()
        if row:
            return row
    return None


async def pseudonym_for_signup(db: AsyncSession, signup: SignupRequest) -> str:
    persona = await get_or_create_persona(signup, db)
    return persona.nickname


async def mask_student_for_circle(
    db: AsyncSession,
    school_student: SchoolStudent,
) -> dict[str, Any]:
    """Sponsor-safe student snapshot (no legal name)."""
    signup = await resolve_student_signup_for_school_row(db, school_student)
    pseudonym = await pseudonym_for_signup(db, signup) if signup else "Sponsored student"

    return {
        "pseudonym": pseudonym,
        "school_student_id": school_student.id,
        "grade": school_student.grade,
        "attendance_pct": int(school_student.attendance_pct or 0),
        "avg_score": int(school_student.avg_score or 0),
        "zqa_score": int(school_student.zqa_score or 0),
        "risk_level": school_student.risk_level,
        "q_report_status": school_student.q_report_status,
        "sl_name": school_student.sl_name,
        "class_teacher": school_student.class_teacher,
    }


async def sponsored_student_for_circle(
    db: AsyncSession,
    circle_id: str,
) -> Optional[dict[str, Any]]:
    res = await db.execute(
        select(SchoolStudent)
        .where(SchoolStudent.circle_id == circle_id)
        .order_by(SchoolStudent.created_at.desc())
        .limit(1)
    )
    row = res.scalar_one_or_none()
    if not row:
        return None
    return await mask_student_for_circle(db, row)


async def checkout_buyer_display_name(
    db: AsyncSession,
    buyer: SignupRequest,
    *,
    order_type: str,
) -> str:
    if (order_type or "").lower() == "student":
        if buyer.persona == Persona.student:
            return await pseudonym_for_signup(db, buyer)
        return "Student fund"
    return buyer.full_name or "Circle member"
