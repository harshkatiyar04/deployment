"""Resolve signup row for email/password login when multiple personas share an email."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.models.enums import KycStatus, LoginAccessTier, MemberKind, Persona
from app.models.signup import SignupRequest
from app.services.signup_validation import normalize_email

# When one email has multiple persona rows, prefer the account matching the mailbox role.
_EMAIL_PERSONA_PREFERENCE: dict[str, Persona] = {
    "school@zenk": Persona.school,
    "mentor@zenk.in": Persona.mentor,
    "mentor@zenk": Persona.mentor,
    "leader@zenk.in": Persona.sponsor_leader,
    "leader@zenk": Persona.sponsor_leader,
}


def _prefer_persona_for_email(email: str) -> Persona | None:
    key = (email or "").strip().lower()
    if key in _EMAIL_PERSONA_PREFERENCE:
        return _EMAIL_PERSONA_PREFERENCE[key]
    if key.startswith("school@"):
        return Persona.school
    if key.startswith("mentor@"):
        return Persona.mentor
    return None


def _pick_family_login_match(matches: list[SignupRequest]) -> SignupRequest | None:
    """Same-email student + parent guardian: default hat by Indian age tier."""
    students = [m for m in matches if m.persona == Persona.student]
    parents = [
        m
        for m in matches
        if m.persona == Persona.sponsor_member and m.member_kind == MemberKind.parent_guardian.value
    ]
    if not students or not parents:
        return None
    student = students[0]
    tier = student.login_access_tier or LoginAccessTier.consent_required.value
    if tier == LoginAccessTier.guardian_only.value:
        return parents[0]
    return student


def _pick_best_match(email: str, matches: list[SignupRequest]) -> SignupRequest:
    if len(matches) == 1:
        return matches[0]
    family_pick = _pick_family_login_match(matches)
    if family_pick is not None:
        return family_pick
    preferred = _prefer_persona_for_email(email)
    if preferred is not None:
        for row in matches:
            if row.persona == preferred:
                return row
    for status in (KycStatus.approved, KycStatus.pending, KycStatus.rejected):
        for row in matches:
            if row.kyc_status == status:
                return row
    return matches[0]


async def resolve_signup_for_credentials(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    persona: Persona | None = None,
) -> SignupRequest | None:
    """
    Find the signup row matching email + password.
    When persona is omitted and several rows share the email, pick the best match
    (approved first, then pending, then most recently updated).
    """
    norm_email = normalize_email(email)
    if persona is not None:
        res = await db.execute(
            select(SignupRequest).where(
                func.lower(SignupRequest.email) == norm_email,
                SignupRequest.persona == persona,
            )
        )
        row = res.scalar_one_or_none()
        if row and verify_password(password, row.password_hash):
            return row
        return None

    res = await db.execute(
        select(SignupRequest)
        .where(func.lower(SignupRequest.email) == norm_email)
        .order_by(SignupRequest.updated_at.desc())
    )
    candidates = list(res.scalars().all())
    matches = [c for c in candidates if verify_password(password, c.password_hash)]
    if not matches:
        return None
    return _pick_best_match(norm_email, matches)
