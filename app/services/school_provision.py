"""Create or repair school_profiles when a school principal is approved or signs in."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import Persona
from app.models.school import SchoolKiaWelcome, SchoolProfile
from app.models.signup import SignupRequest


def _school_code_from_id(signup_id: str) -> str:
    compact = (signup_id or "").replace("-", "")[:8].upper()
    return f"ZNK-SCH-{compact}"


def _derive_school_fields(signup: SignupRequest) -> dict:
    name = (signup.address_line1 or "").strip()
    if not name or name.lower() in ("school portal member", "n/a"):
        name = (signup.full_name or "Partner School").strip()
        if "school" not in name.lower():
            name = f"{name} School"
    city = (signup.city or "Mumbai").strip() or "Mumbai"
    district = (signup.state or signup.city or "Maharashtra").strip() or "Maharashtra"
    principal = (signup.full_name or "Principal").strip()
    return {
        "school_name": name[:300],
        "city": city[:120],
        "district": district[:120],
        "principal_name": principal[:200],
    }


async def ensure_school_profile(db: AsyncSession, signup: SignupRequest) -> SchoolProfile | None:
    """
    Ensure school_profiles row exists for an approved school principal (signup.id == profile.id).
    Idempotent — safe on login and KYC approval.
    """
    persona = signup.persona.value if hasattr(signup.persona, "value") else str(signup.persona)
    if persona != Persona.school.value:
        return None

    res = await db.execute(select(SchoolProfile).where(SchoolProfile.id == signup.id))
    profile = res.scalar_one_or_none()
    fields = _derive_school_fields(signup)
    now = datetime.utcnow()

    if profile:
        profile.school_name = profile.school_name or fields["school_name"]
        profile.principal_name = profile.principal_name or fields["principal_name"]
        profile.city = profile.city or fields["city"]
        profile.district = profile.district or fields["district"]
        profile.portal_role = profile.portal_role or "principal"
        profile.updated_at = now
        await db.flush()
        return profile

    profile = SchoolProfile(
        id=signup.id,
        school_name=fields["school_name"],
        school_code=_school_code_from_id(signup.id),
        affiliation="CBSE",
        city=fields["city"],
        district=fields["district"],
        principal_name=fields["principal_name"],
        partner_since=str(now.year),
        is_partner=True,
        fy_current="2025-26",
        portal_role="principal",
        created_at=now,
        updated_at=now,
    )
    db.add(profile)
    await db.flush()

    from app.services.kia_event_briefings import emit_school_onboarded

    await emit_school_onboarded(
        db,
        profile=profile,
        principal_name=fields["principal_name"],
    )

    welcome_res = await db.execute(
        select(SchoolKiaWelcome).where(SchoolKiaWelcome.id == signup.id)
    )
    if not welcome_res.scalar_one_or_none():
        db.add(
            SchoolKiaWelcome(
                id=signup.id,
                welcome_sent=False,
                welcome_message=(
                    "Welcome to your ZenK School Dashboard. "
                    "Add students, submit reports, and track ZQA from this portal."
                ),
                task_list=[
                    "Review students",
                    "Submit quarterly report",
                    "Enter monthly attendance",
                ],
            )
        )
        await db.flush()

    return profile
