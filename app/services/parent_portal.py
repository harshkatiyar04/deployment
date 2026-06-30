"""Parent portal — linked child view and academic document uploads."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.gamified_persona import get_or_create_persona
from app.models.enums import MemberKind, Persona
from app.models.school import SchoolStudent
from app.models.signup import SignupRequest
from app.models.student_family import ParentAcademicSubmission, StudentFamilyLink
from app.services.cloudinary_service import upload_raw
from app.services.notifications import create_notification
from app.services.student_dashboard import (
    mask_circle_label,
    resolve_school_student,
    resolve_student_circle_id,
)
from app.services.student_circle_enrollment import student_join_status
from app.services.student_family import get_family_link_for_user

ALLOWED_DOC_TYPES = frozenset({"marksheet", "transcript", "term_grades"})
ALLOWED_MIMES = frozenset({
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/jpg",
    "image/webp",
})
MAX_FILE_BYTES = 10 * 1024 * 1024


def resolve_upload_mime(content_type: str, filename: str = "") -> str:
    """Normalize browser upload MIME (Windows often sends application/octet-stream for PDFs)."""
    mime = (content_type or "").lower().split(";")[0].strip()
    if mime in ALLOWED_MIMES:
        return mime
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        return "application/pdf"
    if name.endswith(".jpg") or name.endswith(".jpeg"):
        return "image/jpeg"
    if name.endswith(".png"):
        return "image/png"
    if name.endswith(".webp"):
        return "image/webp"
    return mime


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def require_parent_guardian(
    db: AsyncSession,
    user: SignupRequest,
) -> tuple[SignupRequest, StudentFamilyLink]:
    if user.persona != Persona.sponsor_member:
        raise HTTPException(status_code=403, detail="Parent portal requires sponsor member account")

    link = await get_family_link_for_user(db, user.id)
    if not link or link.parent_signup_id != user.id:
        raise HTTPException(status_code=404, detail="No linked child for this parent account")

    is_guardian = (
        user.member_kind == MemberKind.parent_guardian.value
        or link.parent_signup_id == user.id
    )
    if not is_guardian:
        raise HTTPException(status_code=403, detail="Parent guardian account required")
    return user, link


async def _sync_family_link(
    db: AsyncSession,
    link: StudentFamilyLink,
    student: SignupRequest,
) -> tuple[Optional[SchoolStudent], Optional[str]]:
    school_student = await resolve_school_student(db, student)
    circle_id = await resolve_student_circle_id(db, student, school_student)
    changed = False
    if school_student and link.school_student_id != school_student.id:
        link.school_student_id = school_student.id
        changed = True
    if circle_id and link.circle_id != circle_id:
        link.circle_id = circle_id
        changed = True
    if changed:
        link.updated_at = _utcnow()
    return school_student, circle_id


def _upload_gate(
    circle_id: Optional[str],
    school_student: Optional[SchoolStudent],
    *,
    student: Optional[SignupRequest] = None,
) -> tuple[bool, Optional[str]]:
    if not school_student:
        return False, "Student must be admitted to your partner school before academic uploads."
    if student and (student.onboarding_version or "v1") == "v2":
        return True, None
    if not circle_id:
        return False, "Student must join a circle before academic uploads are allowed."
    return True, None


async def _child_summary(
    db: AsyncSession,
    *,
    link: StudentFamilyLink,
    student: SignupRequest,
) -> dict[str, Any]:
    persona = await get_or_create_persona(student, db)
    school_student, circle_id = await _sync_family_link(db, link, student)
    upload_ok, upload_reason = _upload_gate(circle_id, school_student, student=student)

    from app.chat.models import SponsorCircle

    circle_name = None
    if circle_id:
        c_res = await db.execute(select(SponsorCircle).where(SponsorCircle.id == circle_id))
        circle = c_res.scalar_one_or_none()
        circle_name = circle.name if circle else None

    zqa = attendance = avg_score = 0
    risk = "—"
    if school_student:
        zqa = int(school_student.zqa_score or 0)
        attendance = int(school_student.attendance_pct or 0)
        avg_score = int(school_student.avg_score or 0)
        risk = school_student.risk_level or "Low"

    join = await student_join_status(db, student)

    return {
        "student_signup_id": student.id,
        "pseudonym": persona.nickname,
        "grade": student.grade_or_year or (school_student.grade if school_student else None),
        "school_linked": school_student is not None,
        "school_student_id": school_student.id if school_student else None,
        "circle_id": circle_id,
        "circle_name_masked": mask_circle_label(circle_name),
        "relationship": link.relationship,
        "kpis": {
            "zqa_score": zqa,
            "attendance_pct": attendance,
            "avg_score": avg_score,
            "risk_level": risk,
        },
        "upload_eligible": upload_ok,
        "upload_block_reason": upload_reason,
        "circle_join": {
            "in_circle": join.get("in_circle", False),
            "pending_request": join.get("pending_request"),
            "can_request_join": join.get("can_request_join", False),
            "block_reason": join.get("block_reason"),
        },
    }


async def build_parent_academic_profile(
    db: AsyncSession,
    parent: SignupRequest,
    *,
    quarter: str = "Q4",
) -> dict[str, Any]:
    """Read-only full academic record for parent's linked child."""
    from app.services.sponsor_sponsored_student import build_sponsored_student_profile

    _, link = await require_parent_guardian(db, parent)
    res = await db.execute(select(SignupRequest).where(SignupRequest.id == link.student_signup_id))
    student = res.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Linked student account not found")

    school_student, _circle_id = await _sync_family_link(db, link, student)
    persona = await get_or_create_persona(student, db)
    if not school_student:
        return {
            "linked": False,
            "pseudonym": persona.nickname,
            "message": "Academic records appear after your child's school admits them.",
        }

    record = await build_sponsored_student_profile(
        db,
        school_student,
        quarter=quarter,
        viewer="parent",
    )
    return {"linked": True, "quarter": quarter.upper(), **record}


async def list_linked_children(db: AsyncSession, parent: SignupRequest) -> list[dict[str, Any]]:
    _, link = await require_parent_guardian(db, parent)
    res = await db.execute(select(SignupRequest).where(SignupRequest.id == link.student_signup_id))
    student = res.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Linked student account not found")
    return [await _child_summary(db, link=link, student=student)]


async def build_parent_onboarding_timeline(db: AsyncSession, parent: SignupRequest) -> dict[str, Any]:
    """Same step timeline as student dashboard, for parent viewing linked child."""
    _, link = await require_parent_guardian(db, parent)
    res = await db.execute(select(SignupRequest).where(SignupRequest.id == link.student_signup_id))
    student = res.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Linked student account not found")

    from app.services.student_onboarding_v2 import build_onboarding_timeline

    persona = await get_or_create_persona(student, db)
    timeline = await build_onboarding_timeline(db, student)
    return {
        **timeline,
        "viewer": "parent",
        "child_pseudonym": persona.nickname,
        "child_signup_id": student.id,
    }


def _build_grade_payload(
    *,
    quarter: Optional[str] = None,
    maths_grade: Optional[str] = None,
    science_grade: Optional[str] = None,
    english_grade: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    raw = {
        "maths": maths_grade,
        "science": science_grade,
        "english": english_grade,
    }
    subjects = [
        {"name": name, "grade": (val or "").strip()}
        for name, val in raw.items()
        if (val or "").strip()
    ]
    if not subjects:
        return None
    payload: dict[str, Any] = {"subjects": subjects}
    q = (quarter or "").strip().upper()
    if q:
        payload["quarter"] = q
    return payload


def _resolve_submission_kind(
    *,
    has_file: bool,
    grade_payload: Optional[dict[str, Any]],
) -> str:
    if has_file and grade_payload:
        return "combined"
    if grade_payload:
        return "manual"
    return "file"


def submission_brief_dict(sub: ParentAcademicSubmission) -> dict[str, Any]:
    """Leader/sponsor-safe summary of an approved parent submission."""
    return {
        "document_type": sub.document_type,
        "submission_kind": sub.submission_kind or "file",
        "approved_at": sub.reviewed_at.isoformat() if sub.reviewed_at else None,
        "parent_note": sub.parent_note,
        "grade_payload": sub.grade_payload,
        "has_file": bool(sub.file_url),
    }


def _submission_out(row: ParentAcademicSubmission) -> dict[str, Any]:
    return {
        "id": row.id,
        "student_signup_id": row.student_signup_id,
        "school_student_id": row.school_student_id,
        "document_type": row.document_type,
        "submission_kind": row.submission_kind or "file",
        "file_url": row.file_url,
        "original_filename": row.original_filename,
        "parent_note": row.parent_note,
        "grade_payload": row.grade_payload,
        "status": row.status,
        "principal_note": row.principal_note,
        "reviewed_at": row.reviewed_at.isoformat() if row.reviewed_at else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


async def list_parent_submissions(
    db: AsyncSession,
    parent: SignupRequest,
    *,
    student_signup_id: Optional[str] = None,
) -> list[dict[str, Any]]:
    _, link = await require_parent_guardian(db, parent)
    if student_signup_id and student_signup_id != link.student_signup_id:
        raise HTTPException(status_code=403, detail="Not your linked child")
    q = select(ParentAcademicSubmission).where(ParentAcademicSubmission.parent_signup_id == parent.id)
    if student_signup_id:
        q = q.where(ParentAcademicSubmission.student_signup_id == student_signup_id)
    q = q.order_by(ParentAcademicSubmission.created_at.desc())
    res = await db.execute(q)
    return [_submission_out(r) for r in res.scalars().all()]


async def create_parent_submission(
    db: AsyncSession,
    parent: SignupRequest,
    *,
    student_signup_id: str,
    document_type: str,
    file: Optional[UploadFile] = None,
    parent_note: Optional[str] = None,
    quarter: Optional[str] = None,
    maths_grade: Optional[str] = None,
    science_grade: Optional[str] = None,
    english_grade: Optional[str] = None,
) -> dict[str, Any]:
    _, link = await require_parent_guardian(db, parent)
    if student_signup_id != link.student_signup_id:
        raise HTTPException(status_code=400, detail="You can only upload documents for your linked child")

    doc_type = (document_type or "").strip().lower()
    if doc_type not in ALLOWED_DOC_TYPES:
        raise HTTPException(
            status_code=400,
            detail="document_type must be 'marksheet', 'transcript', or 'term_grades'",
        )

    res = await db.execute(select(SignupRequest).where(SignupRequest.id == student_signup_id))
    student = res.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    school_student, circle_id = await _sync_family_link(db, link, student)
    upload_ok, upload_reason = _upload_gate(circle_id, school_student, student=student)
    if not upload_ok:
        raise HTTPException(status_code=403, detail=upload_reason)

    grade_payload = _build_grade_payload(
        quarter=quarter,
        maths_grade=maths_grade,
        science_grade=science_grade,
        english_grade=english_grade,
    )
    note = (parent_note or "").strip() or None
    has_file = file is not None and (file.filename or "").strip()

    if not has_file and not grade_payload:
        raise HTTPException(
            status_code=400,
            detail="Attach a marksheet/transcript file or enter at least one term grade",
        )

    url: Optional[str] = None
    original_filename: Optional[str] = None
    if has_file:
        content_type = resolve_upload_mime(file.content_type or "", file.filename or "")
        if content_type not in ALLOWED_MIMES:
            raise HTTPException(status_code=400, detail="Use PDF, JPG, PNG, or WebP")

        raw = await file.read()
        if len(raw) > MAX_FILE_BYTES:
            raise HTTPException(status_code=400, detail="File must be under 10 MB")
        await file.seek(0)

        url = await upload_raw(file, folder="zenk/parent-academic")
        if not url:
            raise HTTPException(status_code=502, detail="Upload failed — try again later")
        original_filename = file.filename

    if not has_file:
        doc_type = "term_grades"

    submission_kind = _resolve_submission_kind(has_file=bool(url), grade_payload=grade_payload)

    row = ParentAcademicSubmission(
        parent_signup_id=parent.id,
        student_signup_id=student_signup_id,
        school_student_id=school_student.id if school_student else None,
        document_type=doc_type,
        submission_kind=submission_kind,
        file_url=url,
        original_filename=original_filename,
        parent_note=note,
        grade_payload=grade_payload,
        status="pending_principal",
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return _submission_out(row)


async def list_school_parent_submissions(
    db: AsyncSession,
    school_id: str,
    *,
    status: str = "pending_principal",
) -> list[dict[str, Any]]:
    q = (
        select(ParentAcademicSubmission, SchoolStudent, SignupRequest)
        .join(SchoolStudent, ParentAcademicSubmission.school_student_id == SchoolStudent.id)
        .join(SignupRequest, ParentAcademicSubmission.student_signup_id == SignupRequest.id)
        .where(SchoolStudent.school_id == school_id)
    )
    if status and status != "all":
        q = q.where(ParentAcademicSubmission.status == status)
    q = q.order_by(ParentAcademicSubmission.created_at.desc())
    res = await db.execute(q)
    rows = []
    for sub, school_student, student in res.all():
        rows.append({
            **_submission_out(sub),
            "student_name": school_student.full_name or student.full_name,
            "grade": school_student.grade or student.grade_or_year,
            "parent_signup_id": sub.parent_signup_id,
        })
    return rows


async def _get_school_submission(
    db: AsyncSession,
    school_id: str,
    submission_id: str,
) -> tuple[ParentAcademicSubmission, SchoolStudent]:
    res = await db.execute(
        select(ParentAcademicSubmission, SchoolStudent)
        .join(SchoolStudent, ParentAcademicSubmission.school_student_id == SchoolStudent.id)
        .where(
            ParentAcademicSubmission.id == submission_id,
            SchoolStudent.school_id == school_id,
        )
    )
    row = res.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Submission not found")
    return row[0], row[1]


async def approve_parent_submission(
    db: AsyncSession,
    *,
    school_user: SignupRequest,
    school_id: str,
    submission_id: str,
    note: Optional[str] = None,
) -> dict[str, Any]:
    sub, _student = await _get_school_submission(db, school_id, submission_id)
    if sub.status != "pending_principal":
        raise HTTPException(status_code=400, detail=f"Submission is already {sub.status}")

    sub.status = "approved"
    sub.principal_note = (note or "").strip() or None
    sub.reviewed_by = school_user.id
    sub.reviewed_at = _utcnow()
    sub.updated_at = _utcnow()
    await db.commit()
    await db.refresh(sub)

    await create_notification(
        recipient_id=sub.parent_signup_id,
        recipient_type="user",
        notification_type="parent_upload_approved",
        title="Academic submission approved",
        message=(
            f"Your {sub.document_type.replace('_', ' ')} submission was approved by the school principal."
            + (f" Note: {sub.principal_note}" if sub.principal_note else "")
        ),
        related_entity_id=sub.id,
        related_entity_type="parent_academic_submission",
        db=db,
    )
    return _submission_out(sub)


async def reject_parent_submission(
    db: AsyncSession,
    *,
    school_user: SignupRequest,
    school_id: str,
    submission_id: str,
    note: str,
) -> dict[str, Any]:
    reason = (note or "").strip()
    if not reason:
        raise HTTPException(status_code=400, detail="A rejection note is required")

    sub, _student = await _get_school_submission(db, school_id, submission_id)
    if sub.status != "pending_principal":
        raise HTTPException(status_code=400, detail=f"Submission is already {sub.status}")

    sub.status = "rejected"
    sub.principal_note = reason
    sub.reviewed_by = school_user.id
    sub.reviewed_at = _utcnow()
    sub.updated_at = _utcnow()
    await db.commit()
    await db.refresh(sub)

    await create_notification(
        recipient_id=sub.parent_signup_id,
        recipient_type="user",
        notification_type="parent_upload_rejected",
        title="Academic submission needs revision",
        message=f"Your {sub.document_type.replace('_', ' ')} submission was not accepted. Principal note: {reason}",
        related_entity_id=sub.id,
        related_entity_type="parent_academic_submission",
        db=db,
    )
    return _submission_out(sub)
