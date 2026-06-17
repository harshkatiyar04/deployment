"""Student-initiated school onboarding invites when the school is not yet on ZenK."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import settings
from app.models.signup import SignupRequest
from app.models.student_onboarding import StudentSchoolReferral
from app.services.student_onboarding_v2 import ONBOARDING_V2, create_school_interest

SCHOOL_NOT_LISTED_ID = "__NOT_LISTED__"
REFERRAL_TTL_DAYS = 90


def is_school_not_listed(school_id: Optional[str]) -> bool:
    return (school_id or "").strip() == SCHOOL_NOT_LISTED_ID


def build_school_referral_url(token: str) -> str:
    base = (getattr(settings, "frontend_base_url", None) or settings.website_url or "http://localhost:5173").rstrip("/")
    return f"{base}/signup?tab=school&school_referral={token}"


def _new_token() -> str:
    return secrets.token_urlsafe(32)


async def create_referral_for_student(
    db: AsyncSession,
    *,
    student_signup_id: str,
    proposed_school_name: str,
    proposed_city: str,
    proposed_state: Optional[str] = None,
    proposed_contact_email: Optional[str] = None,
) -> tuple[StudentSchoolReferral, str]:
    existing = await db.execute(
        select(StudentSchoolReferral).where(StudentSchoolReferral.student_signup_id == student_signup_id)
    )
    row = existing.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    name = proposed_school_name.strip()[:300]
    city = proposed_city.strip()[:120]
    if not name or not city:
        raise HTTPException(status_code=400, detail="School name and city are required for the invite.")

    if row:
        if row.status == "linked":
            return row, build_school_referral_url(row.token)
        row.proposed_school_name = name
        row.proposed_city = city
        row.proposed_state = (proposed_state or "").strip()[:120] or None
        row.proposed_contact_email = (proposed_contact_email or "").strip()[:320] or None
        row.expires_at = now + timedelta(days=REFERRAL_TTL_DAYS)
        row.updated_at = now
        if row.status == "pending":
            await db.flush()
            return row, build_school_referral_url(row.token)
        row.token = _new_token()
        row.status = "pending"
        row.school_signup_id = None
        row.school_profile_id = None
        await db.flush()
        return row, build_school_referral_url(row.token)

    row = StudentSchoolReferral(
        token=_new_token(),
        student_signup_id=student_signup_id,
        proposed_school_name=name,
        proposed_city=city,
        proposed_state=(proposed_state or "").strip()[:120] or None,
        proposed_contact_email=(proposed_contact_email or "").strip()[:320] or None,
        status="pending",
        expires_at=now + timedelta(days=REFERRAL_TTL_DAYS),
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    await db.flush()
    return row, build_school_referral_url(row.token)


async def resolve_referral_token(db: AsyncSession, token: str) -> dict[str, Any]:
    tok = (token or "").strip()
    if not tok:
        raise HTTPException(status_code=400, detail="Invite token is required.")

    res = await db.execute(
        select(StudentSchoolReferral, SignupRequest)
        .join(SignupRequest, SignupRequest.id == StudentSchoolReferral.student_signup_id)
        .where(StudentSchoolReferral.token == tok)
    )
    row = res.first()
    if not row:
        raise HTTPException(status_code=404, detail="This school invite link is invalid.")

    referral, student = row[0], row[1]
    now = datetime.now(timezone.utc)
    if referral.expires_at < now:
        raise HTTPException(status_code=410, detail="This invite link has expired. Ask the student for a new one.")
    if referral.status == "linked":
        raise HTTPException(status_code=410, detail="This school has already joined ZenK through this invite.")

    return {
        "token": referral.token,
        "proposed_school_name": referral.proposed_school_name,
        "proposed_city": referral.proposed_city,
        "proposed_state": referral.proposed_state,
        "proposed_contact_email": referral.proposed_contact_email,
        "student_first_name": (student.full_name or "A student").split()[0],
        "status": referral.status,
        "expires_at": referral.expires_at.isoformat(),
    }


async def attach_school_signup_to_referral(
    db: AsyncSession,
    *,
    token: str,
    school_signup_id: str,
) -> None:
    tok = (token or "").strip()
    if not tok:
        return

    res = await db.execute(select(StudentSchoolReferral).where(StudentSchoolReferral.token == tok))
    referral = res.scalar_one_or_none()
    if not referral:
        raise HTTPException(status_code=400, detail="School invite link is invalid.")
    now = datetime.now(timezone.utc)
    if referral.expires_at < now:
        raise HTTPException(status_code=410, detail="School invite link has expired.")
    if referral.status == "linked":
        return

    referral.school_signup_id = school_signup_id
    referral.status = "school_registered"
    referral.updated_at = now
    await db.flush()


async def complete_referral_after_school_profile(
    db: AsyncSession,
    *,
    school_signup_id: str,
    school_profile_id: str,
) -> None:
    """Link student interest once the referred school profile exists (idempotent)."""
    res = await db.execute(
        select(StudentSchoolReferral).where(StudentSchoolReferral.school_signup_id == school_signup_id)
    )
    referral = res.scalar_one_or_none()
    if not referral or referral.status == "linked":
        return

    student_res = await db.execute(
        select(SignupRequest).where(SignupRequest.id == referral.student_signup_id)
    )
    student = student_res.scalar_one_or_none()
    if not student:
        return

    now = datetime.now(timezone.utc)
    student.selected_school_id = school_profile_id
    student.school_or_college_name = referral.proposed_school_name
    student.onboarding_version = ONBOARDING_V2
    student.updated_at = now

    referral.school_profile_id = school_profile_id
    referral.status = "linked"
    referral.updated_at = now
    await db.flush()

    from app.models.student_onboarding import StudentSchoolInterest

    interest_res = await db.execute(
        select(StudentSchoolInterest).where(StudentSchoolInterest.student_signup_id == student.id)
    )
    if not interest_res.scalar_one_or_none():
        await create_school_interest(db, student_signup_id=student.id, school_id=school_profile_id)
