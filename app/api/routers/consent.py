"""
Admin endpoint: record parental consent for a student.

POST /admin/consent/{student_id}
  - Admin only (enforced by email domain for now, same pattern as SOS queue)
  - Body: consent_type (str), notes (str optional)
  - Returns: 201 with the created consent record
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jwt_auth import get_current_user_from_token
from app.db.session import get_db
from app.models.signup import SignupRequest

from fastapi import Query

router = APIRouter(prefix="/admin", tags=["admin-consent"])


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
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Record verified parental/guardian consent for a student.
    Admin role only.

    After this record exists, the student can connect to circle chat
    (the WS handler checks parental_consent_log before allowing the connection).
    """
    admin = await get_current_user_from_token(token, db)
    if admin is None:
        raise HTTPException(status_code=401, detail="Invalid or missing token")

    # Admin check — same convention as SOS queue endpoint
    if not getattr(admin, "email", "").endswith("@zenkedu.com"):
        raise HTTPException(status_code=403, detail="Admin role required")

    # Verify student exists
    student_result = await db.execute(
        select(SignupRequest).where(SignupRequest.id == student_id)
    )
    student = student_result.scalar_one_or_none()
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")

    if str(student.persona) != "student":
        raise HTTPException(status_code=400, detail="Target user is not a student")

    # Insert consent record using raw SQL (table created in migration 002)
    from sqlalchemy import text  # noqa: PLC0415

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
            "verified_by": admin.id,
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
        verified_by_admin_id=admin.id,
        verified_at=now,
        expires_at=None,
        notes=body.notes,
        created_at=now,
    )
