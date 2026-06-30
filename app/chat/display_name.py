"""Circle chat display names — KYC real names for sponsors; pseudonyms for students."""

from __future__ import annotations

from app.chat.models import GamifiedPersona
from app.models.enums import Persona
from app.models.signup import SignupRequest

LEADER_MEMBER_ROLES = frozenset({"lead", "sponsor_leader", "coordinator"})


def is_leader_member_role(role: str | None) -> bool:
    return (role or "").lower() in LEADER_MEMBER_ROLES


def chat_display_name(user: SignupRequest | None, persona: GamifiedPersona) -> str:
    """Sponsors/leaders/mentors show KYC full_name; students keep pseudonym nickname."""
    if persona.nickname == "Kia":
        return "Kia"
    if user is not None and user.persona == Persona.student:
        return persona.nickname
    if user is not None:
        full = (user.full_name or "").strip()
        if full:
            return full
    return persona.nickname
