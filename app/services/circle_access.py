"""Circle membership access rules for sponsor leader / member dashboards."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.models import CircleMember, SponsorCircle
from app.models.enums import KycStatus, Persona
from app.models.signup import SignupRequest
from app.services.circle_budget import LEADER_ROLES, _can_set_budget
from app.services.circle_member_invite import LEADER_APPROVED, LEADER_REJECTED, parse_invite_note


# Persona → post-login dashboard (must match zenkimpact_FE dashboardRoutes.js)
PERSONA_DASHBOARD: dict[Persona, str] = {
    Persona.school: "/school-dashboard",
    Persona.mentor: "/mentor-dashboard",
    Persona.vendor: "/dashboard/vendor-portal",
    Persona.corporate: "/corporate-dashboard",
    Persona.student: "/dashboard/resources",
    Persona.sponsor: "/dashboard/home",
    Persona.sponsor_leader: "/sponsor-leader?tab=My%20Circle",
    Persona.sponsor_member: "/sponsor-circle",
}


async def _in_circle(db: AsyncSession, circle_id: str, user_id: str) -> bool:
    res = await db.execute(
        select(CircleMember.id).where(
            CircleMember.circle_id == circle_id,
            CircleMember.user_id == user_id,
        )
    )
    return res.scalar_one_or_none() is not None


async def _primary_circle_for_user(db: AsyncSession, user_id: str) -> Optional[tuple[SponsorCircle, str]]:
    res = await db.execute(
        select(SponsorCircle, CircleMember.role)
        .join(CircleMember, CircleMember.circle_id == SponsorCircle.id)
        .where(CircleMember.user_id == user_id)
        .order_by(SponsorCircle.name)
    )
    rows = res.all()
    if not rows:
        return None
    for circle, role in rows:
        if _can_set_budget(role):
            return circle, role
    return rows[0][0], rows[0][1]


def _dashboard_path(persona: Persona) -> str:
    return PERSONA_DASHBOARD.get(persona, "/dashboard/home")


def _redirect_for_state(state: str, persona: Persona) -> str:
    if state == "verification":
        return "/verification-status"
    if state == "waiting_leader":
        return "/waiting-for-leader"
    if state == "leader_declined":
        return "/waiting-for-leader?status=declined"
    if state == "dashboard_leader":
        return PERSONA_DASHBOARD[Persona.sponsor_leader]
    if state == "dashboard_member":
        return PERSONA_DASHBOARD[Persona.sponsor_member]
    return _dashboard_path(persona)


async def resolve_circle_access(db: AsyncSession, signup: SignupRequest) -> dict[str, Any]:
    """
    Compute safe redirect + flags for frontend routing.
    Does not grant access beyond what RBAC allows.
    """
    persona = signup.persona
    kyc = signup.kyc_status.value if hasattr(signup.kyc_status, "value") else str(signup.kyc_status)

    if kyc in (
        KycStatus.pending.value,
        KycStatus.rejected.value,
        KycStatus.info_required.value,
    ):
        return {
            "access_state": "verification",
            "redirect_to": _redirect_for_state("verification", persona),
            "in_circle": False,
            "circle_id": None,
            "circle_name": None,
            "leader_status": None,
            "is_leader": False,
        }

    if persona == Persona.sponsor_member:
        invite_cid, leader_status = parse_invite_note(signup.admin_note)
        in_circle = False
        circle_name = None
        if invite_cid:
            in_circle = await _in_circle(db, invite_cid, signup.id)
            if in_circle:
                leader_status = LEADER_APPROVED
            c_res = await db.execute(select(SponsorCircle.name).where(SponsorCircle.id == invite_cid))
            circle_name = c_res.scalar_one_or_none()

        if leader_status == LEADER_REJECTED:
            state = "leader_declined"
        elif not in_circle:
            state = "waiting_leader"
        else:
            state = "dashboard_member"

        return {
            "access_state": state,
            "redirect_to": _redirect_for_state(state, persona),
            "in_circle": in_circle,
            "circle_id": invite_cid or None,
            "circle_name": circle_name,
            "leader_status": leader_status,
            "is_leader": False,
        }

    if persona == Persona.sponsor_leader:
        row = await _primary_circle_for_user(db, signup.id)
        in_circle = row is not None
        circle_id = row[0].id if row else None
        circle_name = row[0].name if row else None
        is_leader = bool(row and _can_set_budget(row[1]))
        if in_circle and not is_leader:
            state = "verification"
        else:
            state = "dashboard_leader"
        return {
            "access_state": state,
            "redirect_to": _redirect_for_state(state, persona),
            "in_circle": in_circle,
            "circle_id": circle_id,
            "circle_name": circle_name,
            "leader_status": None,
            "is_leader": is_leader,
        }

    # School, mentor, vendor, student, legacy sponsor, etc.
    return {
        "access_state": "dashboard",
        "redirect_to": _dashboard_path(persona),
        "in_circle": False,
        "circle_id": None,
        "circle_name": None,
        "leader_status": None,
        "is_leader": False,
    }
