"""Admin student progress — list + detail composed from existing builders."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.models import CircleMember, GamifiedPersona, SOSReport, SponsorCircle
from app.models.admin_support import ZenkAdminThread
from app.models.enums import Persona
from app.models.school import SchoolStudent, SchoolStudentSubjectScore
from app.models.signup import SignupRequest
from app.models.student_family import ParentAcademicSubmission, StudentFamilyLink
from app.models.student_onboarding import StudentCircleInterestRequest
from app.services.parent_portal import _submission_out
from app.services.sponsor_sponsored_student import build_sponsored_student_profile


def _kyc_str(value: Any) -> str:
    if value is None:
        return ""
    return value.value if hasattr(value, "value") else str(value)


def _iso(dt: Any) -> Optional[str]:
    if dt is None:
        return None
    try:
        return dt.isoformat()
    except Exception:
        return str(dt)


def _roster_quality(row: SchoolStudent) -> tuple:
    """Prefer rows with real progress data over empty duplicate roster stubs."""
    zqa = float(row.zqa_score or 0)
    avg = float(row.avg_score or 0)
    att = float(row.attendance_pct or 0)
    has_circle = 1 if row.circle_id else 0
    return (zqa, avg, att, has_circle)


async def resolve_admin_school_student(
    db: AsyncSession,
    signup: SignupRequest,
) -> Optional[SchoolStudent]:
    """
    Pick the best SchoolStudent for admin progress.

    Duplicate roster rows for one signup can exist; `.limit(1)` without ranking
    often returns an empty stub (ZQA 0, no subject scores) while another row
    holds the real academics.
    """
    link_res = await db.execute(
        select(StudentFamilyLink).where(StudentFamilyLink.student_signup_id == signup.id)
    )
    link = link_res.scalar_one_or_none()
    if link and link.school_student_id:
        linked = (
            await db.execute(
                select(SchoolStudent).where(SchoolStudent.id == link.school_student_id)
            )
        ).scalar_one_or_none()
        if linked and (
            float(linked.zqa_score or 0) > 0
            or float(linked.avg_score or 0) > 0
            or linked.circle_id
        ):
            return linked

    rows = list(
        (
            await db.execute(
                select(SchoolStudent).where(SchoolStudent.signup_request_id == signup.id)
            )
        )
        .scalars()
        .all()
    )
    if not rows and link and link.school_student_id:
        linked = (
            await db.execute(
                select(SchoolStudent).where(SchoolStudent.id == link.school_student_id)
            )
        ).scalar_one_or_none()
        if linked:
            return linked
    if not rows:
        return None

    # Prefer rows that actually have quarterly subject scores
    scored_ids: set[str] = set()
    id_list = [r.id for r in rows]
    if id_list:
        score_res = await db.execute(
            select(SchoolStudentSubjectScore.student_id)
            .where(SchoolStudentSubjectScore.student_id.in_(id_list))
            .distinct()
        )
        scored_ids = {sid for sid in score_res.scalars().all()}

    def sort_key(row: SchoolStudent) -> tuple:
        has_scores = 1 if row.id in scored_ids else 0
        return (has_scores, *_roster_quality(row))

    return max(rows, key=sort_key)


async def list_admin_students(
    db: AsyncSession,
    *,
    q: Optional[str] = None,
    circle_id: Optional[str] = None,
    kyc_status: Optional[str] = None,
    roster: str = "all",
) -> dict[str, Any]:
    stmt = (
        select(SignupRequest)
        .where(SignupRequest.persona == Persona.student)
        .order_by(SignupRequest.created_at.desc())
    )

    needle = (q or "").strip()
    if needle:
        like = f"%{needle}%"
        stmt = stmt.where(
            or_(
                SignupRequest.full_name.ilike(like),
                SignupRequest.email.ilike(like),
                SignupRequest.mobile.ilike(like),
                SignupRequest.school_or_college_name.ilike(like),
            )
        )

    if kyc_status and kyc_status.strip().lower() not in ("", "all"):
        stmt = stmt.where(SignupRequest.kyc_status == kyc_status.strip().lower())

    signups = list((await db.execute(stmt)).scalars().all())

    items: list[dict[str, Any]] = []
    for signup in signups:
        school_row = await resolve_admin_school_student(db, signup)

        if circle_id and circle_id.strip():
            cid = circle_id.strip()
            if not school_row or school_row.circle_id != cid:
                mem = (
                    await db.execute(
                        select(CircleMember.id)
                        .where(
                            CircleMember.user_id == signup.id,
                            CircleMember.circle_id == cid,
                        )
                        .limit(1)
                    )
                ).scalar_one_or_none()
                if not mem:
                    continue

        has_roster = school_row is not None
        if roster == "yes" and not has_roster:
            continue
        if roster == "no" and has_roster:
            continue

        circle_name = None
        circle_id_val = None
        zqa = None
        attendance = None
        risk = None
        grade = signup.grade_or_year
        school_name = signup.school_or_college_name

        if school_row:
            circle_name = school_row.circle_name
            circle_id_val = school_row.circle_id
            zqa = int(round(float(school_row.zqa_score or 0)))
            attendance = int(round(float(school_row.attendance_pct or 0)))
            risk = school_row.risk_level
            grade = school_row.grade or grade

        items.append(
            {
                "signup_id": signup.id,
                "full_name": signup.full_name,
                "email": signup.email,
                "mobile": signup.mobile,
                "grade": grade,
                "school_name": school_name,
                "kyc_status": _kyc_str(signup.kyc_status),
                "on_roster": has_roster,
                "school_student_id": school_row.id if school_row else None,
                "circle_id": circle_id_val,
                "circle_name": circle_name,
                "zqa_score": zqa,
                "attendance_pct": attendance,
                "risk_level": risk,
                "created_at": _iso(signup.created_at),
            }
        )

    on_roster_count = sum(1 for i in items if i["on_roster"])
    return {
        "summary": {
            "total": len(items),
            "on_roster": on_roster_count,
            "not_enrolled": len(items) - on_roster_count,
        },
        "students": items,
    }


async def _circle_payload(
    db: AsyncSession,
    signup: SignupRequest,
    school_student: Optional[SchoolStudent],
) -> dict[str, Any]:
    circle_id = school_student.circle_id if school_student else None
    circle_name = school_student.circle_name if school_student else None
    membership_role = None

    mem_res = await db.execute(
        select(CircleMember, SponsorCircle)
        .join(SponsorCircle, SponsorCircle.id == CircleMember.circle_id)
        .where(CircleMember.user_id == signup.id)
        .order_by(CircleMember.joined_at.desc())
        .limit(1)
    )
    mem_row = mem_res.first()
    if mem_row:
        member, circle = mem_row
        circle_id = circle_id or member.circle_id
        circle_name = circle_name or circle.name
        membership_role = member.role

    interest_res = await db.execute(
        select(StudentCircleInterestRequest)
        .where(StudentCircleInterestRequest.student_signup_id == signup.id)
        .order_by(StudentCircleInterestRequest.created_at.desc())
        .limit(10)
    )
    interests = [
        {
            "id": r.id,
            "circle_id": r.circle_id,
            "status": r.status,
            "help_comment": r.help_comment,
            "pseudonym": r.pseudonym,
            "created_at": _iso(r.created_at),
            "reviewed_at": _iso(r.reviewed_at),
        }
        for r in interest_res.scalars().all()
    ]

    return {
        "circle_id": circle_id,
        "circle_name": circle_name,
        "membership_role": membership_role,
        "interest_requests": interests,
    }


async def _family_payload(db: AsyncSession, signup_id: str) -> dict[str, Any]:
    link_res = await db.execute(
        select(StudentFamilyLink).where(StudentFamilyLink.student_signup_id == signup_id)
    )
    links = list(link_res.scalars().all())
    guardians: list[dict[str, Any]] = []
    for link in links:
        parent = (
            await db.execute(
                select(SignupRequest).where(SignupRequest.id == link.parent_signup_id)
            )
        ).scalar_one_or_none()
        guardians.append(
            {
                "link_id": link.id,
                "relationship": link.relationship,
                "parent_signup_id": link.parent_signup_id,
                "parent_name": parent.full_name if parent else None,
                "parent_email": parent.email if parent else None,
                "parent_mobile": parent.mobile if parent else None,
                "circle_id": link.circle_id,
                "school_student_id": link.school_student_id,
            }
        )

    sub_res = await db.execute(
        select(ParentAcademicSubmission)
        .where(ParentAcademicSubmission.student_signup_id == signup_id)
        .order_by(ParentAcademicSubmission.created_at.desc())
        .limit(25)
    )
    submissions = [_submission_out(s) for s in sub_res.scalars().all()]

    return {"guardians": guardians, "parent_submissions": submissions}


async def _reports_payload(db: AsyncSession, signup_id: str) -> dict[str, Any]:
    sos_res = await db.execute(
        select(SOSReport)
        .join(GamifiedPersona, GamifiedPersona.id == SOSReport.reporter_persona_id)
        .where(GamifiedPersona.user_id == signup_id)
        .order_by(SOSReport.created_at.desc())
        .limit(25)
    )
    sos_items = [
        {
            "id": r.id,
            "message_id": r.message_id,
            "resolved_at": _iso(r.resolved_at),
            "notes": r.notes,
            "created_at": _iso(r.created_at),
            "status": "resolved" if r.resolved_at else "open",
        }
        for r in sos_res.scalars().all()
    ]

    interest_res = await db.execute(
        select(StudentCircleInterestRequest)
        .where(StudentCircleInterestRequest.student_signup_id == signup_id)
        .order_by(StudentCircleInterestRequest.created_at.desc())
        .limit(25)
    )
    interest_items = [
        {
            "id": r.id,
            "circle_id": r.circle_id,
            "status": r.status,
            "help_comment": r.help_comment,
            "created_at": _iso(r.created_at),
        }
        for r in interest_res.scalars().all()
    ]

    thread = (
        await db.execute(
            select(ZenkAdminThread).where(ZenkAdminThread.user_id == signup_id)
        )
    ).scalar_one_or_none()
    support_threads: list[dict[str, Any]] = []
    if thread:
        support_threads.append(
            {
                "id": thread.id,
                "admin_unread_count": thread.admin_unread_count,
                "user_unread_count": thread.user_unread_count,
                "last_message_text": thread.last_message_text,
                "last_message_at": _iso(thread.last_message_at),
                "status": "open",
            }
        )

    return {
        "sos_reports": sos_items,
        "circle_interest_requests": interest_items,
        "support_threads": support_threads,
    }


async def get_admin_student_progress(
    db: AsyncSession,
    signup_id: str,
    *,
    quarter: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    signup = (
        await db.execute(select(SignupRequest).where(SignupRequest.id == signup_id))
    ).scalar_one_or_none()
    if not signup or signup.persona != Persona.student:
        return None

    school_student = await resolve_admin_school_student(db, signup)

    identity = {
        "signup_id": signup.id,
        "full_name": signup.full_name,
        "email": signup.email,
        "mobile": signup.mobile,
        "date_of_birth": signup.date_of_birth.isoformat() if signup.date_of_birth else None,
        "school_or_college_name": signup.school_or_college_name,
        "selected_school_id": signup.selected_school_id,
        "grade_or_year": signup.grade_or_year,
        "guardian_name": signup.guardian_name,
        "guardian_mobile": signup.guardian_mobile,
        "guardian_relationship": signup.guardian_relationship,
        "kyc_status": _kyc_str(signup.kyc_status),
        "onboarding_version": signup.onboarding_version,
        "created_at": _iso(signup.created_at),
    }

    roster: Optional[dict[str, Any]]
    if school_student:
        roster = {
            "school_student_id": school_student.id,
            "full_name": school_student.full_name,
            "grade": school_student.grade,
            "circle_id": school_student.circle_id,
            "circle_name": school_student.circle_name,
            "attendance_pct": int(school_student.attendance_pct or 0),
            "avg_score": int(school_student.avg_score or 0),
            "zqa_score": int(school_student.zqa_score or 0),
            "risk_level": school_student.risk_level,
            "q_report_status": school_student.q_report_status,
            "mentor_name": school_student.mentor_name,
            "class_teacher": school_student.class_teacher,
            "rank_in_class": school_student.rank_in_class,
            "class_size": school_student.class_size,
        }
        academics = await build_sponsored_student_profile(
            db, school_student, quarter=quarter, viewer="admin"
        )
        academics = {"linked": True, **academics}
    else:
        roster = None
        academics = {
            "linked": False,
            "available": False,
            "message": "Student is not on a school roster yet. Academics appear after school enrollment.",
            "quarters_with_data": [],
            "subject_scores": [],
            "blooms": None,
            "sel": None,
            "narrative": None,
            "zqa_breakdown": None,
        }

    return {
        "identity": identity,
        "roster": roster,
        "academics": academics,
        "circle": await _circle_payload(db, signup, school_student),
        "family": await _family_payload(db, signup.id),
        "reports": await _reports_payload(db, signup.id),
    }
