"""Principal-managed school faculty directory and student assignments."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.school import SchoolFaculty, SchoolStudent

FACULTY_CLASS_TEACHER = "class_teacher"
FACULTY_MENTOR = "mentor"
FACULTY_COORDINATOR = "coordinator"
VALID_FACULTY_ROLES = frozenset({FACULTY_CLASS_TEACHER, FACULTY_MENTOR, FACULTY_COORDINATOR})

ROLE_LABELS = {
    FACULTY_CLASS_TEACHER: "Class teacher",
    FACULTY_MENTOR: "Mentor",
    FACULTY_COORDINATOR: "Coordinator",
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def faculty_to_dict(row: SchoolFaculty) -> dict[str, Any]:
    return {
        "id": row.id,
        "display_name": row.display_name,
        "faculty_role": row.faculty_role,
        "role_label": ROLE_LABELS.get(row.faculty_role, row.faculty_role),
        "subject": row.subject,
        "email": row.email,
        "portal_member_id": row.portal_member_id,
        "notes": row.notes,
        "is_active": row.is_active,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


async def list_faculty(
    db: AsyncSession,
    school_id: str,
    *,
    role: Optional[str] = None,
    active_only: bool = True,
) -> list[dict[str, Any]]:
    q = select(SchoolFaculty).where(SchoolFaculty.school_id == school_id)
    if active_only:
        q = q.where(SchoolFaculty.is_active.is_(True))
    if role:
        q = q.where(SchoolFaculty.faculty_role == role)
    q = q.order_by(SchoolFaculty.faculty_role, SchoolFaculty.display_name)
    res = await db.execute(q)
    return [faculty_to_dict(r) for r in res.scalars().all()]


async def create_faculty(
    db: AsyncSession,
    school_id: str,
    *,
    display_name: str,
    faculty_role: str,
    subject: Optional[str] = None,
    email: Optional[str] = None,
    portal_member_id: Optional[str] = None,
    notes: Optional[str] = None,
) -> dict[str, Any]:
    role = (faculty_role or "").strip().lower()
    if role not in VALID_FACULTY_ROLES:
        raise HTTPException(status_code=400, detail="Invalid faculty role.")

    name = (display_name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Display name is required.")

    row = SchoolFaculty(
        school_id=school_id,
        display_name=name,
        faculty_role=role,
        subject=(subject or "").strip() or None,
        email=(email or "").strip().lower() or None,
        portal_member_id=portal_member_id,
        notes=(notes or "").strip() or None,
    )
    db.add(row)
    await db.flush()
    return faculty_to_dict(row)


async def update_faculty(
    db: AsyncSession,
    school_id: str,
    faculty_id: str,
    *,
    display_name: Optional[str] = None,
    faculty_role: Optional[str] = None,
    subject: Optional[str] = None,
    email: Optional[str] = None,
    notes: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> dict[str, Any]:
    res = await db.execute(
        select(SchoolFaculty).where(
            SchoolFaculty.id == faculty_id,
            SchoolFaculty.school_id == school_id,
        )
    )
    row = res.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Faculty member not found.")

    if display_name is not None:
        name = display_name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="Display name cannot be empty.")
        row.display_name = name
    if faculty_role is not None:
        role = faculty_role.strip().lower()
        if role not in VALID_FACULTY_ROLES:
            raise HTTPException(status_code=400, detail="Invalid faculty role.")
        row.faculty_role = role
    if subject is not None:
        row.subject = subject.strip() or None
    if email is not None:
        row.email = email.strip().lower() or None
    if notes is not None:
        row.notes = notes.strip() or None
    if is_active is not None:
        row.is_active = is_active
    row.updated_at = _utcnow()
    await db.flush()
    return faculty_to_dict(row)


async def _faculty_for_school(
    db: AsyncSession,
    school_id: str,
    faculty_id: str,
    *,
    role: Optional[str] = None,
) -> SchoolFaculty:
    res = await db.execute(
        select(SchoolFaculty).where(
            SchoolFaculty.id == faculty_id,
            SchoolFaculty.school_id == school_id,
            SchoolFaculty.is_active.is_(True),
        )
    )
    row = res.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Faculty member not found.")
    if role and row.faculty_role != role:
        raise HTTPException(
            status_code=400,
            detail=f"Selected faculty is not a {ROLE_LABELS.get(role, role)}.",
        )
    return row


async def resolve_faculty_labels_for_enrollment(
    db: AsyncSession,
    school_id: str,
    *,
    class_teacher: Optional[str] = None,
    class_teacher_faculty_id: Optional[str] = None,
    mentor_name: Optional[str] = None,
    mentor_faculty_id: Optional[str] = None,
) -> tuple[Optional[str], Optional[str]]:
    teacher_label = (class_teacher or "").strip() or None
    mentor_label = (mentor_name or "").strip() or None

    if class_teacher_faculty_id:
        row = await _faculty_for_school(
            db, school_id, class_teacher_faculty_id, role=FACULTY_CLASS_TEACHER
        )
        teacher_label = row.display_name
    if mentor_faculty_id:
        row = await _faculty_for_school(
            db, school_id, mentor_faculty_id, role=FACULTY_MENTOR
        )
        mentor_label = row.display_name

    return teacher_label, mentor_label


async def assign_faculty_to_student(
    db: AsyncSession,
    school_id: str,
    student: SchoolStudent,
    *,
    class_teacher_faculty_id: Optional[str] = None,
    mentor_faculty_id: Optional[str] = None,
    clear_class_teacher: bool = False,
    clear_mentor: bool = False,
) -> dict[str, Any]:
    if clear_class_teacher:
        student.class_teacher_faculty_id = None
        student.class_teacher = None
    elif class_teacher_faculty_id:
        teacher = await _faculty_for_school(
            db, school_id, class_teacher_faculty_id, role=FACULTY_CLASS_TEACHER
        )
        student.class_teacher_faculty_id = teacher.id
        student.class_teacher = teacher.display_name

    if clear_mentor:
        student.mentor_faculty_id = None
        student.mentor_name = None
    elif mentor_faculty_id:
        mentor = await _faculty_for_school(
            db, school_id, mentor_faculty_id, role=FACULTY_MENTOR
        )
        student.mentor_faculty_id = mentor.id
        student.mentor_name = mentor.display_name

    return {
        "class_teacher": student.class_teacher,
        "class_teacher_faculty_id": student.class_teacher_faculty_id,
        "mentor_name": student.mentor_name,
        "mentor_faculty_id": student.mentor_faculty_id,
    }
