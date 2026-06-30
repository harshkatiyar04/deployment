"""
Admin endpoint: record parental consent for a student.

POST /admin/consent/{student_id}
  - Admin API key required (same as other admin routes)
  - Body: consent_type (str), notes (str optional)
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_deps import require_admin_api_key, resolve_admin_actor_id
from app.db.session import get_db
from app.models.signup import SignupRequest

router = APIRouter(
    prefix="/admin",
    tags=["admin-consent"],
    dependencies=[Depends(require_admin_api_key)],
)


class ConsentBody(BaseModel):
    consent_type: str  # e.g. "guardian_verbal", "guardian_written"
    notes: Optional[str] = None


class ConsentOut(BaseModel):
    id: str
    student_id: str
    consent_type: str
    verified_by_admin_id: str
    verified_at: datetime
    expires_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime


@router.post("/consent/{student_id}", response_model=ConsentOut, status_code=status.HTTP_201_CREATED)
async def record_consent(
    student_id: str,
    body: ConsentBody,
    db: AsyncSession = Depends(get_db),
):
    """
    Record verified parental/guardian consent for a student.
    Admin API key required.

    After this record exists, the student can connect to circle chat
    (the WS handler checks parental_consent_log before allowing the connection).
    """
    admin_id = await resolve_admin_actor_id(db)

    student_result = await db.execute(
        select(SignupRequest).where(SignupRequest.id == student_id)
    )
    student = student_result.scalar_one_or_none()
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")

    if str(student.persona) != "student":
        raise HTTPException(status_code=400, detail="Target user is not a student")

    now = datetime.now(timezone.utc)
    record_id = str(uuid4())

    await db.execute(
        text("""
            INSERT INTO "ZENK".parental_consent_log
                (id, student_id, consent_type, verified_by_admin_id, verified_at, notes, created_at)
            VALUES
                (:id, :student_id, :consent_type, :verified_by, :verified_at, :notes, :created_at)
        """),
        {
            "id": record_id,
            "student_id": student_id,
            "consent_type": body.consent_type,
            "verified_by": admin_id,
            "verified_at": now,
            "notes": body.notes,
            "created_at": now,
        },
    )
    await db.commit()

    return ConsentOut(
        id=record_id,
        student_id=student_id,
        consent_type=body.consent_type,
        verified_by_admin_id=admin_id,
        verified_at=now,
        expires_at=None,
        notes=body.notes,
        created_at=now,
    )
