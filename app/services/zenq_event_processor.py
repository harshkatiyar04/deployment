"""Live ZenQ event hooks — v2 ledger only (legacy materializer archived)."""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import settings
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

# Roles that feed chat → ZenQ v2 chat mapping (circle supporters + members).
# Quality (RAS / substantive / shield) still gates which messages earn IP.
ZENQ_SCORING_ROLES = frozenset(
    {
        "sponsor",
        "sponsor_leader",
        "sponsor_member",
        "member",
        "lead",
        "mentor",
        "tutor",
        "partner",
    }
)


async def process_chat_message_event(
    db: AsyncSession,
    *,
    message_id: str,
    circle_id: str,
    actor_user_id: str,
    ras_score: float,
    substantive: bool,
    shield_action: str,
) -> None:
    if not settings.zenq_live_events:
        return
    try:
        from app.services.zenq_v2.bridge import bridge_chat_message

        await bridge_chat_message(
            db,
            message_id=message_id,
            circle_id=circle_id,
            actor_user_id=actor_user_id,
            ras_score=ras_score,
            substantive=substantive,
            shield_action=shield_action,
        )
    except Exception:
        logger.exception("[ZenQ v2] chat bridge failed for %s", message_id)


def schedule_circle_recompute(circle_id: str, *, trigger_source: str = "chat_message") -> None:
    """No-op: 1.5.1 materializer archived. Monthly close scores circles."""
    return


async def run_chat_message_zenq_pipeline(
    *,
    message_id: str,
    circle_id: str,
    actor_user_id: str,
    ras_score: float,
    substantive: bool,
    shield_action: str,
) -> None:
    if not settings.zenq_live_events:
        return
    try:
        async with SessionLocal() as db:
            await process_chat_message_event(
                db,
                message_id=message_id,
                circle_id=circle_id,
                actor_user_id=actor_user_id,
                ras_score=ras_score,
                substantive=substantive,
                shield_action=shield_action,
            )
    except Exception:
        logger.exception("[ZenQ v2] chat_message pipeline failed for %s", message_id)


async def process_mentor_session_event(
    db: AsyncSession,
    *,
    session_id: str,
    circle_id: str,
    mentor_user_id: str,
    duration_hrs: float,
) -> None:
    if not settings.zenq_live_events:
        return
    try:
        from app.services.zenq_v2.bridge import bridge_mentor_session

        await bridge_mentor_session(
            db,
            session_id=session_id,
            circle_id=circle_id,
            mentor_user_id=mentor_user_id,
            duration_hrs=duration_hrs,
        )
    except Exception:
        logger.exception("[ZenQ v2] session bridge failed for %s", session_id)


async def process_target_log_event(
    *,
    circle_id: str,
    sponsor_user_id: str,
    target_status: str,
    log_id: str,
) -> None:
    if not settings.zenq_live_events:
        return
    try:
        async with SessionLocal() as db:
            from app.services.zenq_v2.bridge import bridge_target

            await bridge_target(
                db,
                circle_id=circle_id,
                sponsor_user_id=sponsor_user_id,
                target_status=target_status,
                log_id=log_id,
            )
    except Exception:
        logger.exception("[ZenQ v2] target_log pipeline failed for %s", log_id)


async def run_mentor_session_zenq_pipeline(
    *,
    session_id: str,
    mentor_user_id: str,
    student_circle: str,
    duration_hrs: float,
) -> None:
    if not settings.zenq_live_events:
        return
    try:
        from app.models.mentor import MentorProfile
        from app.services.zenq_sponsor_enrichment import resolve_circle_for_mentor

        async with SessionLocal() as db:
            res = await db.execute(
                select(MentorProfile).where(MentorProfile.id == mentor_user_id)
            )
            profile = res.scalar_one_or_none()
            circle_id = await resolve_circle_for_mentor(
                db,
                mentor_circle_id=profile.circle_id if profile else None,
                student_circle_name=student_circle,
            )
            if not circle_id:
                return
            await process_mentor_session_event(
                db,
                session_id=session_id,
                circle_id=circle_id,
                mentor_user_id=mentor_user_id,
                duration_hrs=duration_hrs,
            )
    except Exception:
        logger.exception("[ZenQ v2] mentor_session pipeline failed for %s", session_id)
