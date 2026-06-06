"""Student-initiated circle join — after school has enrolled the student."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.school import SchoolStudent, SchoolStudentEnrollmentRequest
from app.models.signup import SignupRequest
from app.services.student_onboarding_v2 import ONBOARDING_V2
from app.services.school_enrollment_constants import ENROLLMENT_PENDING
from app.services.school_student_enrollment import create_enrollment_request, list_active_circles
from app.services.student_dashboard import resolve_school_student


async def student_join_status(
    db: AsyncSession,
    student: SignupRequest,
) -> dict[str, Any]:
    if (student.onboarding_version or "v1") == ONBOARDING_V2:
        from app.services.student_onboarding_v2 import build_onboarding_timeline

        timeline = await build_onboarding_timeline(db, student)
        school_student = await resolve_school_student(db, student)
        return {
            "onboarding_version": ONBOARDING_V2,
            "school_linked": school_student is not None,
            "school_student_id": school_student.id if school_student else None,
            "in_circle": timeline.get("in_circle", False),
            "circle_id": school_student.circle_id if school_student else None,
            "circle_name": school_student.circle_name if school_student else None,
            "pending_request": None,
            "can_request_join": False,
            "block_reason": (
                "Use the Join Circle tab to request open circles (v2 onboarding)."
                if timeline.get("unlocked_circle_request")
                else "Complete ZenK KYC, school admission, and parent KYC first."
            ),
            "timeline": timeline,
        }

    school_student = await resolve_school_student(db, student)
    pending = None
    if school_student:
        res = await db.execute(
            select(SchoolStudentEnrollmentRequest)
            .where(
                SchoolStudentEnrollmentRequest.school_id == school_student.school_id,
                SchoolStudentEnrollmentRequest.full_name.ilike(school_student.full_name),
                SchoolStudentEnrollmentRequest.status == ENROLLMENT_PENDING,
            )
            .order_by(SchoolStudentEnrollmentRequest.requested_at.desc())
            .limit(1)
        )
        pending = res.scalar_one_or_none()

    return {
        "school_linked": school_student is not None,
        "school_student_id": school_student.id if school_student else None,
        "in_circle": bool(school_student and school_student.circle_id),
        "circle_id": school_student.circle_id if school_student else None,
        "circle_name": school_student.circle_name if school_student else None,
        "pending_request": {
            "id": pending.id,
            "circle_id": pending.circle_id,
            "circle_name": pending.circle_name,
            "status": pending.status,
            "requested_at": pending.requested_at.isoformat() if pending and pending.requested_at else None,
        }
        if pending
        else None,
        "can_request_join": bool(
            school_student and not school_student.circle_id and not pending
        ),
        "block_reason": _block_reason(school_student, pending),
    }


def _block_reason(
    school_student: Optional[SchoolStudent],
    pending: Optional[SchoolStudentEnrollmentRequest],
) -> Optional[str]:
    if not school_student:
        return (
            "Your partner school must enroll you first. "
            "After school approval, you can request to join a sponsorship circle."
        )
    if school_student.circle_id:
        return None
    if pending:
        return f"A join request to {pending.circle_name} is awaiting circle leader approval."
    return None


async def list_circles_for_student(db: AsyncSession) -> list[dict[str, str]]:
    return await list_active_circles(db)


async def submit_student_circle_join(
    db: AsyncSession,
    student: SignupRequest,
    *,
    circle_id: str,
) -> dict[str, Any]:
    if (student.onboarding_version or "v1") == ONBOARDING_V2:
        raise HTTPException(
            status_code=400,
            detail="v2 students request circles via Join Circle with a support note, not legacy join.",
        )

    school_student = await resolve_school_student(db, student)
    if not school_student:
        raise HTTPException(
            status_code=403,
            detail="School enrollment is required before requesting a circle.",
        )
    if school_student.circle_id:
        raise HTTPException(status_code=400, detail="You are already linked to a circle.")

    dup = await db.execute(
        select(SchoolStudentEnrollmentRequest).where(
            SchoolStudentEnrollmentRequest.school_id == school_student.school_id,
            SchoolStudentEnrollmentRequest.full_name.ilike(school_student.full_name),
            SchoolStudentEnrollmentRequest.status == ENROLLMENT_PENDING,
        )
    )
    if dup.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="You already have a pending circle join request.",
        )

    req = await create_enrollment_request(
        db,
        school_id=school_student.school_id,
        user=student,
        body={
            "circle_id": circle_id,
            "full_name": school_student.full_name or student.full_name,
            "grade": school_student.grade or student.grade_or_year or "",
            "dob": school_student.dob,
            "zenk_id": student.id,
            "class_teacher": school_student.class_teacher,
            "sl_name": school_student.sl_name,
            "mentor_name": school_student.mentor_name,
            "rank_in_class": school_student.rank_in_class,
            "class_size": school_student.class_size,
        },
    )
    return {
        "id": req.id,
        "circle_id": req.circle_id,
        "circle_name": req.circle_name,
        "status": req.status,
        "message": f"Join request sent to {req.circle_name}. Your parent will be added after approval.",
    }
