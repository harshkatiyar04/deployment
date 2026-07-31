"""Circle chat display names — KYC real names for sponsors; pseudonyms for students."""

from __future__ import annotations

import json
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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


def mention_handle(display_or_nick: str) -> str:
    """Word-safe @handle (spaces → underscore) for message tokens."""
    raw = (display_or_nick or "").strip()
    if not raw:
        return "member"
    return re.sub(r"\s+", "_", raw)


def parse_dm_persona_ids(dm_for: str | None) -> list[str]:
    if not dm_for:
        return []
    try:
        data = json.loads(dm_for)
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    if not isinstance(data, list):
        return []
    return [str(x) for x in data if x]


async def channel_display_label(
    db: AsyncSession,
    *,
    channel_name: str,
    dm_for: str | None,
    viewer_persona_id: str | None,
) -> str:
    """
    Human label for channel chips.
    Public channels keep their name; DMs show the other person's display name.
    """
    pair = parse_dm_persona_ids(dm_for)
    if not pair:
        return channel_name

    other_id = None
    viewer = str(viewer_persona_id) if viewer_persona_id else None
    for pid in pair:
        if viewer and pid == viewer:
            continue
        other_id = pid
        break
    if other_id is None:
        other_id = pair[0]

    res = await db.execute(
        select(GamifiedPersona, SignupRequest)
        .join(SignupRequest, GamifiedPersona.user_id == SignupRequest.id)
        .where(GamifiedPersona.id == other_id)
        .limit(1)
    )
    row = res.first()
    if not row:
        return "Direct message"
    persona, signup = row
    return chat_display_name(signup, persona)
