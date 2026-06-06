"""Gamified chat persona helpers (no router imports — avoids circular deps)."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.models import GamifiedPersona
from app.models.enums import Persona
from app.models.signup import SignupRequest


async def get_or_create_persona(user: SignupRequest, db: AsyncSession) -> GamifiedPersona:
    """Get existing GamifiedPersona for user, or create one."""
    result = await db.execute(
        select(GamifiedPersona).where(GamifiedPersona.user_id == user.id)
    )
    persona = result.scalar_one_or_none()
    if persona is None:
        if user.persona == Persona.student:
            nickname = f"student_{str(uuid.uuid4())[:6]}"
        else:
            prefix = user.email.split("@")[0][:8]
            nickname = f"{prefix}_{str(uuid.uuid4())[:4]}"
        avatar_key = f"avatar_{str(uuid.uuid4())[:8]}"
        persona = GamifiedPersona(
            user_id=user.id,
            nickname=nickname,
            avatar_key=avatar_key,
        )
        db.add(persona)
        await db.flush()
    return persona
