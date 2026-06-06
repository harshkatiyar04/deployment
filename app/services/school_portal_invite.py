"""School portal invite links: create, validate, accept."""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.core.settings import settings
from app.models.enums import KycStatus, Persona
from app.models.signup import SignupRequest
from app.models.school import SchoolPortalInvite, SchoolPortalMember, SchoolProfile
from app.services.school_permissions import ROLE_PRINCIPAL, ROLE_STAFF, normalize_role

INVITE_TTL_DAYS = 14


def build_join_url(token: str) -> str:
    base = (getattr(settings, "frontend_base_url", None) or settings.website_url or "http://localhost:5173").rstrip("/")
    return f"{base}/school/join?token={token}"


def _new_token() -> str:
    return secrets.token_urlsafe(32)


async def _get_valid_invite(db: AsyncSession, token: str) -> Tuple[SchoolPortalInvite, SchoolProfile]:
    tok = (token or "").strip()
    if not tok:
        raise HTTPException(status_code=400, detail="Invite token is required.")

    res = await db.execute(
        select(SchoolPortalInvite, SchoolProfile)
        .join(SchoolProfile, SchoolProfile.id == SchoolPortalInvite.school_id)
        .where(SchoolPortalInvite.token == tok)
    )
    row = res.first()
    if not row:
        raise HTTPException(status_code=404, detail="This invite link is invalid or has expired.")

    invite, profile = row[0], row[1]
    now = datetime.utcnow()

    if invite.revoked_at is not None:
        raise HTTPException(status_code=410, detail="This invite was revoked by the school.")
    if invite.accepted_at is not None:
        raise HTTPException(status_code=410, detail="This invite has already been used.")
    if invite.expires_at < now:
        raise HTTPException(status_code=410, detail="This invite link has expired. Ask your principal for a new one.")

    return invite, profile


async def create_portal_invite(
    db: AsyncSession,
    *,
    school_id: str,
    email: str,
    display_name: str,
    portal_role: str,
    invited_by_user_id: str,
) -> Tuple[SchoolPortalInvite, str]:
    """Create portal member + invite token; returns invite and join URL."""
    email_key = email.strip().lower()
    role = normalize_role(portal_role)
    if role not in (ROLE_PRINCIPAL, ROLE_STAFF):
        raise ValueError("portal_role must be principal or staff.")

    dup_member = await db.execute(
        select(SchoolPortalMember).where(
            SchoolPortalMember.school_id == school_id,
            func.lower(SchoolPortalMember.email) == email_key,
        )
    )
    member = dup_member.scalar_one_or_none()
    if not member:
        member = SchoolPortalMember(
            school_id=school_id,
            email=email_key,
            display_name=display_name.strip(),
            portal_role=role,
            invited_by_user_id=invited_by_user_id,
        )
        db.add(member)
        await db.flush()
    else:
        member.display_name = display_name.strip()
        member.portal_role = role

    active_inv = await db.execute(
        select(SchoolPortalInvite).where(
            SchoolPortalInvite.school_id == school_id,
            func.lower(SchoolPortalInvite.email) == email_key,
            SchoolPortalInvite.accepted_at.is_(None),
            SchoolPortalInvite.revoked_at.is_(None),
        )
    )
    for old in active_inv.scalars().all():
        old.revoked_at = datetime.utcnow()

    token = _new_token()
    invite = SchoolPortalInvite(
        school_id=school_id,
        member_id=member.id,
        email=email_key,
        display_name=display_name.strip(),
        portal_role=role,
        token=token,
        expires_at=datetime.utcnow() + timedelta(days=INVITE_TTL_DAYS),
        invited_by_user_id=invited_by_user_id,
    )
    db.add(invite)
    await db.flush()
    return invite, build_join_url(token)


async def preview_invite(db: AsyncSession, token: str) -> dict:
    invite, profile = await _get_valid_invite(db, token)
    return {
        "school_name": profile.school_name,
        "school_code": profile.school_code,
        "email": invite.email,
        "display_name": invite.display_name,
        "portal_role": normalize_role(invite.portal_role),
        "expires_at": invite.expires_at.isoformat(),
    }


async def accept_invite(
    db: AsyncSession,
    *,
    token: str,
    password: Optional[str] = None,
    full_name: Optional[str] = None,
    mobile: Optional[str] = None,
    current_user: Optional[SignupRequest] = None,
) -> Tuple[SignupRequest, bool]:
    """
    Accept invite. Returns (signup_user, created_new_account).
    """
    invite, profile = await _get_valid_invite(db, token)
    email_key = invite.email.lower()

    if current_user:
        if (current_user.email or "").strip().lower() != email_key:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Signed-in email does not match this invite. Log out and try again.",
            )
        signup = current_user
        created = False
    else:
        if not password or len(password) < 8:
            raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")
        name = (full_name or invite.display_name or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="Full name is required.")
        if not mobile or len(mobile.strip()) < 8:
            raise HTTPException(status_code=400, detail="Mobile number is required.")

        existing = await db.execute(
            select(SignupRequest).where(
                SignupRequest.email == email_key,
                SignupRequest.persona == Persona.school,
            )
        )
        signup = existing.scalar_one_or_none()

        if signup:
            owner = await db.execute(select(SchoolProfile).where(SchoolProfile.id == signup.id))
            if owner.scalar_one_or_none():
                raise HTTPException(
                    status_code=400,
                    detail="This email is the school principal account. Use that login instead of an invite link.",
                )

        created = signup is None
        now = datetime.utcnow()
        school_kyc = KycStatus.approved  # inherit trust from org invite; principal KYC covers school

        if created:
            signup = SignupRequest(
                persona=Persona.school,
                full_name=name,
                mobile=mobile.strip(),
                email=email_key,
                password_hash=hash_password(password),
                address_line1=profile.school_name[:300],
                address_line2="School portal member",
                city=profile.city,
                state=profile.district,
                pincode="000000",
                country="India",
                kyc_status=school_kyc,
                created_at=now,
                updated_at=now,
            )
            db.add(signup)
            await db.flush()
        else:
            signup.full_name = name
            signup.mobile = mobile.strip()
            signup.password_hash = hash_password(password)
            if signup.kyc_status == KycStatus.pending:
                signup.kyc_status = school_kyc
            signup.updated_at = now

    mem_res = await db.execute(
        select(SchoolPortalMember).where(
            SchoolPortalMember.id == invite.member_id,
        )
    )
    member = mem_res.scalar_one_or_none()
    if not member:
        member = SchoolPortalMember(
            school_id=invite.school_id,
            email=email_key,
            display_name=invite.display_name,
            portal_role=invite.portal_role,
            invited_by_user_id=invite.invited_by_user_id,
        )
        db.add(member)
        await db.flush()
        invite.member_id = member.id

    member.user_id = signup.id
    member.portal_role = invite.portal_role
    member.display_name = invite.display_name
    invite.accepted_at = datetime.utcnow()
    await db.flush()
    return signup, created
