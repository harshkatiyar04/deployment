"""Admit KYC-approved student signups into a partner school (links signup_request_id)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import KycStatus, Persona
from app.models.school import SchoolProfile, SchoolStudent
from app.models.signup import SignupRequest
from app.models.student_family import StudentFamilyLink
from app.services.school_reports import _recalc_school_profile


def _normalize_grade(grade_or_year: Optional[str]) -> str:
    if not grade_or_year:
        return "Grade 10"
    g = grade_or_year.strip()
    if g.lower().startswith("grade"):
        return g
    if g.isdigit():
        return f"Grade {g}"
    return g


def _school_name_matches(signup_school: Optional[str], profile: SchoolProfile) -> bool:
    if not signup_school:
        return False
    needle = signup_school.strip().lower()
    hay = (profile.school_name or "").strip().lower()
    if not needle or not hay:
        return False
    return needle in hay or hay in needle


async def _already_admitted(
    db: AsyncSession,
    *,
    school_id: str,
    signup_id: str,
) -> bool:
    res = await db.execute(
        select(SchoolStudent.id).where(
            SchoolStudent.school_id == school_id,
            or_(
                SchoolStudent.signup_request_id == signup_id,
                SchoolStudent.zenk_id == signup_id,
            ),
        )
    )
    return res.scalar_one_or_none() is not None


async def list_pending_student_signups(
    db: AsyncSession,
    profile: SchoolProfile,
) -> list[dict[str, Any]]:
    """KYC-approved students not yet admitted to this school."""
    linked_res = await db.execute(
        select(SchoolStudent.signup_request_id).where(
            SchoolStudent.school_id == profile.id,
            SchoolStudent.signup_request_id.isnot(None),
        )
    )
    linked_ids = {row[0] for row in linked_res.all() if row[0]}

    res = await db.execute(
        select(SignupRequest)
        .where(
            SignupRequest.persona == Persona.student,
            SignupRequest.kyc_status == KycStatus.approved,
        )
        .order_by(SignupRequest.created_at.desc())
    )
    rows: list[dict[str, Any]] = []
    for signup in res.scalars().all():
        if signup.id in linked_ids:
            continue
        if await _already_admitted(db, school_id=profile.id, signup_id=signup.id):
            continue
        rows.append({
            "signup_id": signup.id,
            "full_name": signup.full_name,
            "email": signup.email,
            "grade": _normalize_grade(signup.grade_or_year),
            "school_on_signup": signup.school_or_college_name,
            "guardian_name": signup.guardian_name,
            "date_of_birth": signup.date_of_birth.isoformat() if signup.date_of_birth else None,
            "submitted_at": signup.created_at.isoformat() if signup.created_at else None,
            "matches_school": _school_name_matches(signup.school_or_college_name, profile),
        })
    rows.sort(key=lambda r: (not r["matches_school"], r["full_name"] or ""))
    return rows


async def admit_student_signup(
    db: AsyncSession,
    *,
    school_id: str,
    signup_id: str,
) -> SchoolStudent:
    """Create school_students row linked to signup — no circle until student requests join."""
    prof_res = await db.execute(select(SchoolProfile).where(SchoolProfile.id == school_id))
    profile = prof_res.scalar_one_or_none()
    if not profile:
        raise ValueError("School profile not found.")

    signup_res = await db.execute(
        select(SignupRequest).where(
            SignupRequest.id == signup_id,
            SignupRequest.persona == Persona.student,
        )
    )
    signup = signup_res.scalar_one_or_none()
    if not signup:
        raise ValueError("Student signup not found.")
    if signup.kyc_status != KycStatus.approved:
        raise ValueError("Student KYC must be approved before school admission.")

    if await _already_admitted(db, school_id=school_id, signup_id=signup.id):
        raise ValueError("This student is already admitted to your school.")

    dup_name = await db.execute(
        select(SchoolStudent).where(
            SchoolStudent.school_id == school_id,
            func.lower(SchoolStudent.full_name) == signup.full_name.strip().lower(),
            SchoolStudent.signup_request_id.is_(None),
        )
    )
    existing = dup_name.scalar_one_or_none()
    if existing:
        existing.signup_request_id = signup.id
        existing.zenk_id = signup.id
        existing.grade = _normalize_grade(signup.grade_or_year) or existing.grade
        student = existing
    else:
        student = SchoolStudent(
            id=str(uuid.uuid4()),
            school_id=school_id,
            full_name=signup.full_name,
            grade=_normalize_grade(signup.grade_or_year),
            signup_request_id=signup.id,
            zenk_id=signup.id,
            dob=signup.date_of_birth.strftime("%d-%m-%Y") if signup.date_of_birth else None,
            attendance_pct=0.0,
            avg_score=0.0,
            zqa_score=0.0,
            risk_level="Low",
            q_report_status="Pending",
            tutor_recommendation_status="none",
        )
        db.add(student)
        await db.flush()

    link_res = await db.execute(
        select(StudentFamilyLink).where(StudentFamilyLink.student_signup_id == signup.id)
    )
    link = link_res.scalar_one_or_none()
    if link:
        link.school_student_id = student.id
        link.updated_at = datetime.now(timezone.utc)

    await _recalc_school_profile(db, school_id)
    await db.commit()
    await db.refresh(student)
    return student
