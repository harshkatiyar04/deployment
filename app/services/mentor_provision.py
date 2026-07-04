"""Create mentor_profiles when a mentor is approved or first opens the dashboard."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import Persona, KycStatus
from app.models.mentor import MentorProfile
from app.models.signup import SignupRequest


def _mentor_code_from_id(signup_id: str) -> str:
    compact = (signup_id or "").replace("-", "")[:8].upper()
    return f"ZNK-MEN-{compact}"


def _specialty_from_signup(signup: SignupRequest) -> str:
    categories = (signup.product_categories or "").strip()
    if categories:
        return categories[:200]
    business_type = (signup.business_type or "").strip()
    if business_type:
        return business_type[:200]
    business_name = (signup.business_name or "").strip()
    if business_name:
        return f"Mentoring — {business_name}"[:200]
    return "Technology & career mentoring"


async def ensure_mentor_profile(
    db: AsyncSession,
    signup: SignupRequest,
) -> MentorProfile | None:
    """
    Ensure mentor_profiles row exists for an approved mentor (signup.id == profile.id).
    Idempotent — safe on login, KYC approval, and profile GET.
    """
    persona = signup.persona.value if hasattr(signup.persona, "value") else str(signup.persona)
    if persona != Persona.mentor.value:
        return None

    res = await db.execute(select(MentorProfile).where(MentorProfile.id == signup.id))
    profile = res.scalar_one_or_none()
    now = datetime.utcnow()

    if profile:
        # Keep city/specialty in sync with signup when still defaults
        if signup.city and (not profile.city or profile.city == "Bengaluru"):
            profile.city = signup.city[:100]
        specialty = _specialty_from_signup(signup)
        if specialty and profile.specialty in (
            "Technology & career mentoring",
            "",
        ):
            profile.specialty = specialty
        profile.updated_at = now
        await db.flush()
        return profile

    profile = MentorProfile(
        id=signup.id,
        mentor_id=_mentor_code_from_id(signup.id),
        specialty=_specialty_from_signup(signup),
        city=(signup.city or "Bengaluru")[:100],
        tier=1,
        tier_label="Tier 1 — Rising",
        sessions_this_fy=0,
        hours_mentored=0.0,
        inspire_index=0.0,
        inspire_index_percentile=0,
        inspire_index_delta=0.0,
        zenq_contribution=0.0,
        community_uplift_count=0,
        inspire_breakdown={
            "session_consistency": 0.0,
            "student_engagement": 0.0,
            "topic_diversity": 0.0,
            "community_uplift": 0.0,
            "circle_feedback_score": 0.0,
        },
        assigned_circles=[],
        badges=["ZenK Verified"] if signup.kyc_status == KycStatus.approved else [],
        created_at=now,
        updated_at=now,
    )
    db.add(profile)
    await db.flush()
    return profile
