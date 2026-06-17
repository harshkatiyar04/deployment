"""Create or repair school_profiles when a school principal is approved or signs in."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import Persona
from app.models.school import SchoolKiaWelcome, SchoolProfile
from app.models.signup import SignupRequest
from app.services.school_profile_completion import (
    apply_profile_completion_timestamp,
    school_fields_from_signup,
)


def _school_code_from_id(signup_id: str) -> str:
    compact = (signup_id or "").replace("-", "")[:8].upper()
    return f"ZNK-SCH-{compact}"


async def ensure_school_profile(
    db: AsyncSession,
    signup: SignupRequest,
    *,
    is_partner: bool = True,
    onboarding_source: str = "public_signup",
) -> SchoolProfile | None:
    """
    Ensure school_profiles row exists for an approved school principal (signup.id == profile.id).
    Idempotent — safe on login and KYC approval.
    """
    persona = signup.persona.value if hasattr(signup.persona, "value") else str(signup.persona)
    if persona != Persona.school.value:
        return None

    res = await db.execute(select(SchoolProfile).where(SchoolProfile.id == signup.id))
    profile = res.scalar_one_or_none()
    fields = school_fields_from_signup(signup)
    now = datetime.utcnow()

    if profile:
        profile.school_name = fields["school_name"] or profile.school_name
        profile.principal_name = fields["principal_name"] or profile.principal_name
        profile.affiliation = fields["affiliation"] or profile.affiliation
        profile.city = fields["city"] or profile.city
        profile.district = fields["district"] or profile.district
        if fields["affiliation_number"]:
            profile.affiliation_number = fields["affiliation_number"]
        if fields["enrollment_year"]:
            profile.enrollment_year = fields["enrollment_year"]
        profile.portal_role = profile.portal_role or "principal"
        if is_partner:
            profile.is_partner = True
        profile.onboarding_source = profile.onboarding_source or onboarding_source
        profile.updated_at = now
        apply_profile_completion_timestamp(profile)
        await db.flush()
    else:
        profile = SchoolProfile(
            id=signup.id,
            school_name=fields["school_name"],
            school_code=_school_code_from_id(signup.id),
            affiliation=fields["affiliation"],
            affiliation_number=fields["affiliation_number"],
            enrollment_year=fields["enrollment_year"],
            city=fields["city"],
            district=fields["district"],
            principal_name=fields["principal_name"],
            partner_since=fields["enrollment_year"] or str(now.year),
            is_partner=is_partner,
            fy_current="2025-26",
            portal_role="principal",
            onboarding_source=onboarding_source,
            created_at=now,
            updated_at=now,
        )
        apply_profile_completion_timestamp(profile)
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
                        "Complete your school profile, then add students and submit reports."
                    ),
                    task_list=[
                        "Complete school profile",
                        "Review students",
                        "Submit quarterly report",
                        "Enter monthly attendance",
                    ],
                )
            )
            await db.flush()

    from app.services.school_referral_invite import complete_referral_after_school_profile

    await complete_referral_after_school_profile(
        db,
        school_signup_id=signup.id,
        school_profile_id=profile.id,
    )

    return profile
