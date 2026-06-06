"""Resolve school org + effective portal role for the logged-in user."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.signup import SignupRequest
from app.models.school import SchoolProfile, SchoolPortalMember
from app.services.school_permissions import normalize_role


@dataclass
class SchoolContext:
    school_id: str
    profile: SchoolProfile
    portal_role: str
    is_account_owner: bool
    actor_name: str
    actor_email: str

    @property
    def can_manage_portal_access(self) -> bool:
        return self.is_account_owner and self.portal_role == "principal"


async def resolve_school_context(user: SignupRequest, db: AsyncSession) -> SchoolContext:
    """Owner login (school_profiles.id == user.id) or invited portal member."""
    owner_res = await db.execute(select(SchoolProfile).where(SchoolProfile.id == user.id))
    owner_profile = owner_res.scalar_one_or_none()
    if owner_profile:
        role = normalize_role(owner_profile.portal_role)
        return SchoolContext(
            school_id=owner_profile.id,
            profile=owner_profile,
            portal_role=role,
            is_account_owner=True,
            actor_name=user.full_name or owner_profile.principal_name,
            actor_email=user.email,
        )

    email_key = (user.email or "").strip().lower()
    mem_res = await db.execute(
        select(SchoolPortalMember).where(
            or_(
                SchoolPortalMember.user_id == user.id,
                func.lower(SchoolPortalMember.email) == email_key,
            )
        )
    )
    member = mem_res.scalar_one_or_none()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="School profile not found. Ask your principal for an invite link to join the school portal.",
        )

    if member.user_id != user.id:
        member.user_id = user.id
        await db.flush()

    prof_res = await db.execute(
        select(SchoolProfile).where(SchoolProfile.id == member.school_id)
    )
    profile = prof_res.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="School profile not found.")

    role = normalize_role(member.portal_role)
    return SchoolContext(
        school_id=profile.id,
        profile=profile,
        portal_role=role,
        is_account_owner=False,
        actor_name=member.display_name or user.full_name,
        actor_email=user.email,
    )
