"""Student pseudonym validation and updates (privacy-safe display name)."""

from __future__ import annotations

import re
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.gamified_persona import get_or_create_persona
from app.chat.models import GamifiedPersona
from app.models.signup import SignupRequest

PSEUDONYM_MIN_LEN = 8
PSEUDONYM_MAX_LEN = 24
PSEUDONYM_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]{7,23}$")
AUTO_NICKNAME_PATTERN = re.compile(r"^student_[a-f0-9]{6}$", re.I)
RESERVED_NICKNAMES = frozenset(
    {"kia", "zenk", "admin", "moderator", "support", "system", "anonymous", "student"}
)


def _name_tokens(full_name: str) -> list[str]:
    raw = re.sub(r"[^A-Za-z\s]", " ", full_name or "")
    tokens = [t.strip().lower() for t in raw.split() if len(t.strip()) >= 2]
    return tokens


def pseudonym_needs_setup(nickname: Optional[str]) -> bool:
    if not nickname:
        return True
    return bool(AUTO_NICKNAME_PATTERN.match(nickname.strip()))


def validate_pseudonym_format(pseudonym: str) -> str:
    value = (pseudonym or "").strip()
    if len(value) < PSEUDONYM_MIN_LEN:
        raise HTTPException(
            status_code=400,
            detail=f"Pseudonym must be at least {PSEUDONYM_MIN_LEN} characters.",
        )
    if len(value) > PSEUDONYM_MAX_LEN:
        raise HTTPException(
            status_code=400,
            detail=f"Pseudonym must be at most {PSEUDONYM_MAX_LEN} characters.",
        )
    if not PSEUDONYM_PATTERN.match(value):
        raise HTTPException(
            status_code=400,
            detail=(
                "Use 8–24 characters: start with a letter, then letters, numbers, or underscores only."
            ),
        )
    if value.lower() in RESERVED_NICKNAMES:
        raise HTTPException(status_code=400, detail="This pseudonym is reserved. Choose another.")
    return value


def validate_pseudonym_against_name(pseudonym: str, full_name: str) -> None:
    nick_lower = pseudonym.lower()
    for token in _name_tokens(full_name):
        if token in nick_lower or nick_lower in token:
            raise HTTPException(
                status_code=400,
                detail="Your pseudonym cannot include any part of your real name.",
            )


async def check_pseudonym_available(
    db: AsyncSession,
    pseudonym: str,
    *,
    exclude_user_id: Optional[str] = None,
) -> dict:
    value = validate_pseudonym_format(pseudonym)
    q = select(GamifiedPersona).where(func.lower(GamifiedPersona.nickname) == value.lower())
    if exclude_user_id:
        q = q.where(GamifiedPersona.user_id != exclude_user_id)
    res = await db.execute(q.limit(1))
    taken = res.scalar_one_or_none() is not None
    return {
        "available": not taken,
        "pseudonym": value,
        "min_length": PSEUDONYM_MIN_LEN,
        "max_length": PSEUDONYM_MAX_LEN,
    }


async def set_student_pseudonym(
    db: AsyncSession,
    student: SignupRequest,
    pseudonym: str,
) -> GamifiedPersona:
    value = validate_pseudonym_format(pseudonym)
    validate_pseudonym_against_name(value, student.full_name)

    avail = await check_pseudonym_available(db, value, exclude_user_id=student.id)
    if not avail["available"]:
        raise HTTPException(status_code=409, detail="This pseudonym is already taken. Try another.")

    persona = await get_or_create_persona(student, db)
    persona.nickname = value
    await db.flush()

    from app.models.student_onboarding import StudentCircleInterestRequest

    pending = await db.execute(
        select(StudentCircleInterestRequest).where(
            StudentCircleInterestRequest.student_signup_id == student.id,
            StudentCircleInterestRequest.status.in_(("pending_leader", "probing")),
        )
    )
    for req in pending.scalars().all():
        req.pseudonym = value

    await db.commit()
    await db.refresh(persona)
    return persona


def pseudonym_meta(nickname: Optional[str]) -> dict:
    return {
        "pseudonym_needs_setup": pseudonym_needs_setup(nickname),
        "pseudonym_min_length": PSEUDONYM_MIN_LEN,
        "pseudonym_max_length": PSEUDONYM_MAX_LEN,
    }
