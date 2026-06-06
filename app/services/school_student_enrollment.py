"""School student enrollment: propose → circle intimation → approve/reject."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.models import CircleMember, SponsorCircle
from app.services.kia_event_briefings import (
    emit_enrollment_approved,
    emit_enrollment_rejected,
    emit_enrollment_submitted,
)
from app.services.school_enrollment_constants import (
    ENROLLMENT_APPROVED,
    ENROLLMENT_PENDING,
    ENROLLMENT_REJECTED,
)
from app.models.notification import Notification
from app.models.school import (
    SchoolProfile,
    SchoolStudent,
    SchoolStudentEnrollmentRequest,
)
from app.models.signup import SignupRequest
from app.services.school_reports import apply_quarterly_report, _recalc_school_profile
from app.services.student_onboarding_v2 import ONBOARDING_V2


async def _assert_not_v2_circle_flow(
    db: AsyncSession,
    *,
    signup_id: Optional[str],
    school_id: str,
) -> None:
    """v2 students use circle interest requests — not school enrollment intimations."""
    if signup_id:
        signup_res = await db.execute(
            select(SignupRequest).where(SignupRequest.id == signup_id)
        )
        signup = signup_res.scalar_one_or_none()
        if signup and (signup.onboarding_version or "v1") == ONBOARDING_V2:
            raise ValueError(
                "This student uses v2 onboarding. Admit them at school, then they request "
                "a circle from their student dashboard — not via school enrollment intimations."
            )
        admitted = await db.execute(
            select(SchoolStudent.id).where(
                SchoolStudent.school_id == school_id,
                SchoolStudent.signup_request_id == signup_id,
            )
        )
        if admitted.scalar_one_or_none():
            raise ValueError(
                "Student is already admitted to your school. v2 students join circles via "
                "their student dashboard interest requests."
            )


async def list_active_circles(db: AsyncSession) -> list[dict[str, str]]:
    from app.services.school_circle_sync import resolve_circle_leader_signup

    res = await db.execute(
        select(SponsorCircle).order_by(SponsorCircle.name)
    )
    out: list[dict[str, str]] = []
    for c in res.scalars().all():
        leader = await resolve_circle_leader_signup(db, c.id)
        out.append({
            "id": c.id,
            "name": c.name,
            "description": c.description or "",
            "leader_name": (leader.full_name or "").strip() if leader else None,
        })
    return out


def _validate_initial_academic(payload: Optional[dict]) -> Optional[dict]:
    if not payload or not payload.get("include_initial_report"):
        return None
    quarter = (payload.get("quarter") or "Q4").upper()
    return {
        "include_initial_report": True,
        "quarter": quarter,
        "fy": payload.get("fy") or "2025-26",
        "attendance_pct": payload.get("attendance_pct", 0),
        "avg_score": payload.get("avg_score", 0),
        "risk_level": payload.get("risk_level") or "Low",
        "rank_in_class": payload.get("rank_in_class"),
        "class_size": payload.get("class_size"),
        "subject_scores": payload.get("subject_scores") or {},
        "blooms": payload.get("blooms") or {},
        "sel": payload.get("sel") or {},
        "narrative": (payload.get("narrative") or "").strip(),
        "tutor_recommendation": payload.get("tutor_recommendation"),
        "ready_for_zenk": bool(payload.get("ready_for_zenk", False)),
    }


async def create_enrollment_request(
    db: AsyncSession,
    *,
    school_id: str,
    user: SignupRequest,
    body: dict[str, Any],
) -> SchoolStudentEnrollmentRequest:
    circle_id = body["circle_id"]
    circle_res = await db.execute(
        select(SponsorCircle).where(SponsorCircle.id == circle_id)
    )
    circle = circle_res.scalar_one_or_none()
    if not circle:
        raise ValueError("ZenK circle not found or inactive.")

    full_name = (body.get("full_name") or "").strip()
    grade = (body.get("grade") or "").strip()
    if not full_name or not grade:
        raise ValueError("Student name and grade are required.")

    signup_id = (body.get("zenk_id") or body.get("signup_request_id") or "").strip() or None
    await _assert_not_v2_circle_flow(db, signup_id=signup_id, school_id=school_id)

    dup = await db.execute(
        select(SchoolStudentEnrollmentRequest).where(
            SchoolStudentEnrollmentRequest.school_id == school_id,
            SchoolStudentEnrollmentRequest.full_name.ilike(full_name),
            SchoolStudentEnrollmentRequest.status == ENROLLMENT_PENDING,
        )
    )
    if dup.scalar_one_or_none():
        raise ValueError(
            f"A pending enrollment for '{full_name}' already exists. "
            "Wait for circle approval or withdraw the request."
        )

    profile_res = await db.execute(
        select(SchoolProfile).where(SchoolProfile.id == school_id)
    )
    profile = profile_res.scalar_one_or_none()
    school_name = profile.school_name if profile else "School"

    from app.services.school_circle_sync import resolve_circle_leader_signup
    from app.services.school_faculty_registry import resolve_faculty_labels_for_enrollment

    sl_name = (body.get("sl_name") or "").strip() or None
    if not sl_name:
        leader = await resolve_circle_leader_signup(db, circle.id)
        sl_name = (leader.full_name or "").strip() if leader else None

    class_teacher, mentor_name = await resolve_faculty_labels_for_enrollment(
        db,
        school_id,
        class_teacher=body.get("class_teacher"),
        class_teacher_faculty_id=body.get("class_teacher_faculty_id"),
        mentor_name=body.get("mentor_name"),
        mentor_faculty_id=body.get("mentor_faculty_id"),
    )

    req = SchoolStudentEnrollmentRequest(
        id=str(uuid.uuid4()),
        school_id=school_id,
        circle_id=circle.id,
        circle_name=circle.name,
        status=ENROLLMENT_PENDING,
        full_name=full_name,
        grade=grade,
        dob=body.get("dob"),
        zenk_id=body.get("zenk_id"),
        class_teacher=class_teacher,
        sl_name=sl_name,
        mentor_name=mentor_name,
        rank_in_class=body.get("rank_in_class"),
        class_size=body.get("class_size"),
        initial_academic_payload=_validate_initial_academic(
            body.get("initial_academic_payload")
        ),
        requested_by_user_id=user.id,
        requested_by_name=user.full_name or "School staff",
        requested_by_email=user.email,
    )
    db.add(req)
    await db.flush()

    await emit_enrollment_submitted(
        db, req=req, school_name=school_name, school_user=user
    )
    await db.commit()
    await db.refresh(req)
    return req


async def _require_circle_reviewer(
    db: AsyncSession, user: SignupRequest, circle_id: str
) -> None:
    if str(user.persona) in ("admin",):
        return
    res = await db.execute(
        select(CircleMember).where(
            CircleMember.circle_id == circle_id,
            CircleMember.user_id == user.id,
            CircleMember.role.in_(("lead", "sponsor_leader", "sponsor")),
        )
    )
    if not res.scalar_one_or_none():
        raise PermissionError("You are not a member of this ZenK circle.")


async def approve_enrollment_request(
    db: AsyncSession,
    *,
    request_id: str,
    user: SignupRequest,
    review_note: Optional[str] = None,
) -> SchoolStudent:
    res = await db.execute(
        select(SchoolStudentEnrollmentRequest).where(
            SchoolStudentEnrollmentRequest.id == request_id
        )
    )
    req = res.scalar_one_or_none()
    if not req:
        raise ValueError("Enrollment request not found.")
    if req.status != ENROLLMENT_PENDING:
        raise ValueError(f"Request is already {req.status}.")

    await _require_circle_reviewer(db, user, req.circle_id)

    signup_request_id = None
    if req.zenk_id:
        signup_request_id = str(req.zenk_id).strip()
        signup_res = await db.execute(
            select(SignupRequest).where(SignupRequest.id == signup_request_id)
        )
        linked_signup = signup_res.scalar_one_or_none()
        if linked_signup and (linked_signup.onboarding_version or "v1") == ONBOARDING_V2:
            raise ValueError(
                "Cannot approve legacy enrollment for a v2 student. "
                "They must join via student dashboard circle interest."
            )

    student = SchoolStudent(
        id=str(uuid.uuid4()),
        school_id=req.school_id,
        full_name=req.full_name,
        grade=req.grade,
        circle_id=req.circle_id,
        circle_name=req.circle_name,
        signup_request_id=signup_request_id,
        attendance_pct=0.0,
        avg_score=0.0,
        zqa_score=0.0,
        risk_level="Low",
        q_report_status="Pending",
        tutor_recommendation_status="none",
        dob=req.dob,
        zenk_id=req.zenk_id,
        class_teacher=req.class_teacher,
        sl_name=req.sl_name,
        mentor_name=req.mentor_name,
        rank_in_class=req.rank_in_class,
        class_size=req.class_size,
    )
    db.add(student)
    await db.flush()

    if req.circle_id:
        from app.services.school_circle_sync import sync_school_student_circle_link

        await sync_school_student_circle_link(
            db,
            student,
            req.circle_id,
            leader=None,
            force_sl=not req.sl_name,
        )
        if req.sl_name:
            student.sl_name = req.sl_name

    if req.initial_academic_payload:
        payload = {**req.initial_academic_payload}
        payload["student_id"] = student.id
        school_user_res = await db.execute(
            select(SignupRequest).where(SignupRequest.id == req.school_id)
        )
        school_user = school_user_res.scalar_one_or_none()
        if school_user:
            await apply_quarterly_report(
                db,
                school_id=req.school_id,
                student=student,
                user=school_user,
                payload=payload,
                source="enrollment",
            )
    else:
        await _recalc_school_profile(db, req.school_id)

    req.status = ENROLLMENT_APPROVED
    req.student_id = student.id
    req.reviewed_by_user_id = user.id
    req.reviewed_by_name = user.full_name or "Circle reviewer"
    req.reviewed_at = datetime.utcnow()
    req.review_note = review_note

    prof_res = await db.execute(
        select(SchoolProfile.school_name).where(SchoolProfile.id == req.school_id)
    )
    school_name = prof_res.scalar_one_or_none()
    await emit_enrollment_approved(
        db,
        req=req,
        student=student,
        reviewer=user,
        school_name=school_name,
    )

    from app.services.family_circle_provision import provision_parent_after_student_enrollment

    await provision_parent_after_student_enrollment(
        db, school_student=student, circle_id=req.circle_id
    )

    await db.commit()
    await db.refresh(student)
    return student


async def reject_enrollment_request(
    db: AsyncSession,
    *,
    request_id: str,
    user: SignupRequest,
    review_note: str,
) -> SchoolStudentEnrollmentRequest:
    if not (review_note or "").strip():
        raise ValueError("Please provide a reason for rejection.")

    res = await db.execute(
        select(SchoolStudentEnrollmentRequest).where(
            SchoolStudentEnrollmentRequest.id == request_id
        )
    )
    req = res.scalar_one_or_none()
    if not req:
        raise ValueError("Enrollment request not found.")
    if req.status != ENROLLMENT_PENDING:
        raise ValueError(f"Request is already {req.status}.")

    await _require_circle_reviewer(db, user, req.circle_id)

    req.status = ENROLLMENT_REJECTED
    req.reviewed_by_user_id = user.id
    req.reviewed_by_name = user.full_name or "Circle reviewer"
    req.reviewed_at = datetime.utcnow()
    req.review_note = review_note.strip()

    await emit_enrollment_rejected(db, req=req, reviewer=user)

    await db.commit()
    await db.refresh(req)
    return req


def enrollment_request_to_dict(
    req: SchoolStudentEnrollmentRequest,
    *,
    school_name: Optional[str] = None,
) -> dict[str, Any]:
    return {
        "id": req.id,
        "school_id": req.school_id,
        "school_name": school_name,
        "circle_id": req.circle_id,
        "circle_name": req.circle_name,
        "status": req.status,
        "student_id": req.student_id,
        "full_name": req.full_name,
        "grade": req.grade,
        "dob": req.dob,
        "zenk_id": req.zenk_id,
        "class_teacher": req.class_teacher,
        "sl_name": req.sl_name,
        "mentor_name": req.mentor_name,
        "rank_in_class": req.rank_in_class,
        "class_size": req.class_size,
        "initial_academic_payload": req.initial_academic_payload,
        "requested_by_name": req.requested_by_name,
        "requested_by_email": req.requested_by_email,
        "requested_at": req.requested_at.isoformat() if req.requested_at else None,
        "reviewed_by_name": req.reviewed_by_name,
        "reviewed_at": req.reviewed_at.isoformat() if req.reviewed_at else None,
        "review_note": req.review_note,
        "intimation_sent_at": (
            req.intimation_sent_at.isoformat() if req.intimation_sent_at else None
        ),
    }
