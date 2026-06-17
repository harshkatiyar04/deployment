"""Signup field validation — email uniqueness and format."""

from __future__ import annotations

import re
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import KycStatus, Persona
from app.models.signup import SignupRequest

EMAIL_RE = re.compile(
    r"^[a-z0-9](?:[a-z0-9.!#$%&'*+/=?^_`{|}~-]*[a-z0-9])?"
    r"@"
    r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
    r"(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+$"
)


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def validate_email_format(email: str) -> str:
    """Return normalized email or raise HTTP 400."""
    norm = normalize_email(email)
    if not norm:
        raise HTTPException(status_code=400, detail="Email is required")
    if len(norm) > 254:
        raise HTTPException(status_code=400, detail="Email is too long")
    if ".." in norm or norm.startswith(".") or "@." in norm or norm.endswith("."):
        raise HTTPException(status_code=400, detail="Enter a valid email address")
    if not EMAIL_RE.fullmatch(norm):
        raise HTTPException(status_code=400, detail="Enter a valid email address")
    return norm


async def find_signup_by_persona_email(
    db: AsyncSession,
    *,
    persona: Persona,
    email: str,
) -> Optional[SignupRequest]:
    norm = normalize_email(email)
    res = await db.execute(
        select(SignupRequest).where(
            SignupRequest.persona == persona,
            func.lower(SignupRequest.email) == norm,
        )
    )
    return res.scalar_one_or_none()


async def email_exists_globally(db: AsyncSession, email: str) -> bool:
    norm = normalize_email(email)
    res = await db.execute(
        select(SignupRequest.id).where(func.lower(SignupRequest.email) == norm).limit(1)
    )
    return res.scalar_one_or_none() is not None


async def assert_email_available_for_new_signup(
    db: AsyncSession,
    email: str,
    *,
    except_signup_id: Optional[str] = None,
) -> str:
    """Block any email already on file (all personas, case-insensitive)."""
    norm = validate_email_format(email)
    res = await db.execute(
        select(SignupRequest).where(func.lower(SignupRequest.email) == norm)
    )
    for row in res.scalars().all():
        if except_signup_id and row.id == except_signup_id:
            continue
        raise HTTPException(
            status_code=409,
            detail="This email is already registered. Sign in instead.",
        )
    return norm


def assert_signup_resubmit_allowed(signup: SignupRequest) -> None:
    """Only info_required may be updated via public signup resubmit."""
    if signup.kyc_status == KycStatus.approved:
        raise HTTPException(
            status_code=409,
            detail="Signup already approved; changes are not allowed",
        )
    if signup.kyc_status == KycStatus.pending:
        raise HTTPException(
            status_code=409,
            detail="This email is already registered. Sign in instead.",
        )
    if signup.kyc_status == KycStatus.rejected:
        raise HTTPException(
            status_code=409,
            detail="This email is already registered. Sign in instead.",
        )
    if signup.kyc_status != KycStatus.info_required:
        raise HTTPException(
            status_code=409,
            detail="This email is already registered. Sign in instead.",
        )
