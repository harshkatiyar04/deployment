"""School student enrollment: propose → circle intimation → approve/reject."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.models import ChatChannel, ChatMessage, CircleMember, GamifiedPersona, SponsorCircle
from app.chat.router_client import _get_or_create_persona
from app.models.notification import Notification
from app.models.school import (
    SchoolProfile,
    SchoolStudent,
    SchoolStudentEnrollmentRequest,
)
from app.models.signup import SignupRequest
from app.services.school_reports import apply_quarterly_report, _recalc_school_profile


ENROLLMENT_PENDING = "pending_circle"
ENROLLMENT_APPROVED = "approved"
ENROLLMENT_REJECTED = "rejected"


async def list_active_circles(db: AsyncSession) -> list[dict[str, str]]:
    res = await db.execute(
        select(SponsorCircle).order_by(SponsorCircle.name)
    )
    return [
        {"id": c.id, "name": c.name, "description": c.description or ""}
        for c in res.scalars().all()
    ]


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
        class_teacher=body.get("class_teacher"),
        sl_name=body.get("sl_name"),
        mentor_name=body.get("mentor_name"),
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

    await _send_circle_intimation(db, req=req, school_name=school_name, school_user=user)
    await db.commit()
    await db.refresh(req)
    return req


async def _send_circle_intimation(
    db: AsyncSession,
    *,
    req: SchoolStudentEnrollmentRequest,
    school_name: str,
    school_user: SignupRequest,
) -> None:
    """Post intimation to circle chat and notify circle leads/sponsors."""
    academic_note = ""
    if req.initial_academic_payload:
        q = req.initial_academic_payload.get("quarter", "Q4")
        academic_note = f" Initial {q} academic data included — will apply after approval."

    msg_text = (
        f"📋 **School enrollment intimation** — {school_name}\n\n"
        f"**Student:** {req.full_name} · **Grade:** {req.grade}\n"
        f"**Requested ZenK circle:** {req.circle_name}\n"
        f"**SL:** {req.sl_name or 'TBD'} · **Class teacher:** {req.class_teacher or 'TBD'}\n"
        f"{academic_note}\n\n"
        f"Please review in **School Comm → Enrollment requests** and Approve or Reject.\n"
        f"_Request ID: {req.id[:8]}…_"
    )

    channel_res = await db.execute(
        select(ChatChannel)
        .where(ChatChannel.circle_id == req.circle_id)
        .order_by(ChatChannel.created_at)
        .limit(1)
    )
    channel = channel_res.scalar_one_or_none()
    if channel:
        persona = await _get_or_create_persona(school_user, db)
        db.add(
            ChatMessage(
                id=str(uuid.uuid4()),
                channel_id=channel.id,
                gamified_persona_id=persona.id,
                content_text=msg_text,
                shield_action="allow",
            )
        )

    members_res = await db.execute(
        select(CircleMember).where(
            CircleMember.circle_id == req.circle_id,
            CircleMember.role.in_(("lead", "sponsor_leader", "sponsor")),
        )
    )
    for member in members_res.scalars().all():
        db.add(
            Notification(
                id=str(uuid.uuid4()),
                recipient_id=member.user_id,
                recipient_type="user",
                notification_type="school_enrollment_request",
                title="New school enrollment request",
                message=(
                    f"{school_name} requested to enroll {req.full_name} ({req.grade}) "
                    f"in {req.circle_name}. Approve in School Comm."
                ),
                related_entity_id=req.id,
                related_entity_type="school_enrollment",
            )
        )

    req.intimation_sent_at = datetime.utcnow()


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

    student = SchoolStudent(
        id=str(uuid.uuid4()),
        school_id=req.school_id,
        full_name=req.full_name,
        grade=req.grade,
        circle_id=req.circle_id,
        circle_name=req.circle_name,
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

    if req.requested_by_user_id:
        db.add(
            Notification(
                id=str(uuid.uuid4()),
                recipient_id=req.requested_by_user_id,
                recipient_type="user",
                notification_type="school_enrollment_approved",
                title="Enrollment approved",
                message=(
                    f"{req.circle_name} approved enrollment for {req.full_name}. "
                    f"The student is now active on your school dashboard."
                ),
                related_entity_id=student.id,
                related_entity_type="school_student",
            )
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

    if req.requested_by_user_id:
        db.add(
            Notification(
                id=str(uuid.uuid4()),
                recipient_id=req.requested_by_user_id,
                recipient_type="user",
                notification_type="school_enrollment_rejected",
                title="Enrollment not approved",
                message=(
                    f"{req.circle_name} declined enrollment for {req.full_name}. "
                    f"Reason: {req.review_note}"
                ),
                related_entity_id=req.id,
                related_entity_type="school_enrollment",
            )
        )

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
