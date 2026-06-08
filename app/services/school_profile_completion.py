"""School profile completion checks and updates."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.school import SchoolProfile
from app.models.signup import SignupRequest


REQUIRED_PROFILE_FIELDS = ("affiliation_number", "enrollment_year")


def _field_present(value: Optional[str]) -> bool:
    return bool((value or "").strip())


def missing_profile_fields(profile: SchoolProfile) -> list[str]:
    missing: list[str] = []
    if not _field_present(profile.affiliation_number):
        missing.append("affiliation_number")
    if not _field_present(profile.enrollment_year):
        missing.append("enrollment_year")
    return missing


def is_profile_complete(profile: SchoolProfile) -> bool:
    return len(missing_profile_fields(profile)) == 0


def profile_completion_payload(profile: SchoolProfile) -> dict[str, Any]:
    missing = missing_profile_fields(profile)
    return {
        "complete": len(missing) == 0,
        "missing_fields": missing,
        "school_code": profile.school_code,
        "profile_completed_at": (
            profile.profile_completed_at.isoformat() if profile.profile_completed_at else None
        ),
    }


def school_fields_from_signup(signup: SignupRequest) -> dict[str, str]:
    """Map signup school columns to profile fields."""
    principal = (signup.school_principal_name or signup.full_name or "Principal").strip()
    name = (signup.school_name or signup.address_line1 or signup.full_name or "Partner School").strip()
    affiliation = (signup.school_affiliation or "CBSE").strip().upper()
    if affiliation not in {"CBSE", "ICSE", "STATE", "IB", "CIE", "OTHER"}:
        affiliation = "OTHER"
    return {
        "school_name": name[:300],
        "principal_name": principal[:200],
        "affiliation": affiliation[:100],
        "affiliation_number": (signup.school_affiliation_number or "").strip()[:64] or None,
        "enrollment_year": (signup.school_enrollment_year or "").strip()[:10] or None,
        "city": (signup.city or "Mumbai").strip()[:120],
        "district": (signup.state or signup.city or "Maharashtra").strip()[:120],
    }


def apply_profile_completion_timestamp(profile: SchoolProfile) -> None:
    if is_profile_complete(profile) and not profile.profile_completed_at:
        profile.profile_completed_at = datetime.utcnow()
    elif not is_profile_complete(profile):
        profile.profile_completed_at = None


async def update_school_profile_fields(
    db: AsyncSession,
    profile: SchoolProfile,
    *,
    school_name: Optional[str] = None,
    principal_name: Optional[str] = None,
    affiliation: Optional[str] = None,
    affiliation_number: Optional[str] = None,
    enrollment_year: Optional[str] = None,
    city: Optional[str] = None,
    district: Optional[str] = None,
) -> SchoolProfile:
    if school_name is not None and school_name.strip():
        profile.school_name = school_name.strip()[:300]
    if principal_name is not None and principal_name.strip():
        profile.principal_name = principal_name.strip()[:200]
    if affiliation is not None and affiliation.strip():
        profile.affiliation = affiliation.strip()[:100]
    if affiliation_number is not None:
        profile.affiliation_number = affiliation_number.strip()[:64] or None
    if enrollment_year is not None:
        profile.enrollment_year = enrollment_year.strip()[:10] or None
    if city is not None and city.strip():
        profile.city = city.strip()[:120]
    if district is not None and district.strip():
        profile.district = district.strip()[:120]
    profile.updated_at = datetime.utcnow()
    apply_profile_completion_timestamp(profile)
    await db.flush()
    return profile
