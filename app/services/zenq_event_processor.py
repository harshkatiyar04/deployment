"""Process ZenQ events and debounced circle recomputation (Phase 1)."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import settings
from app.db.session import SessionLocal
from app.models.zenq import ZenqEvent
from app.services.zenq_materializer import materialize_circle_by_id

logger = logging.getLogger(__name__)

_DEBOUNCE_SECONDS = 2.5
_pending_recomputes: dict[str, asyncio.Task] = {}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def record_zenq_event(
    db: AsyncSession,
    *,
    event_type: str,
    circle_id: Optional[str],
    actor_id: Optional[str],
    payload: dict,
    idempotency_key: Optional[str] = None,
    commit: bool = True,
) -> Optional[str]:
    if idempotency_key:
        existing = await db.execute(
            select(ZenqEvent.id).where(ZenqEvent.idempotency_key == idempotency_key)
        )
        if existing.scalar_one_or_none():
            return None

    row = ZenqEvent(
        event_type=event_type,
        circle_id=circle_id,
        actor_id=actor_id,
        idempotency_key=idempotency_key,
        payload_json=payload,
        processed_at=_utcnow(),
    )
    db.add(row)
    if commit:
        await db.commit()
    return row.id


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

    await record_zenq_event(
        db,
        event_type="chat_message",
        circle_id=circle_id,
        actor_id=actor_user_id,
        idempotency_key=f"chat:{message_id}",
        payload={
            "message_id": message_id,
            "ras_score": ras_score,
            "substantive": substantive,
            "shield_action": shield_action,
        },
        commit=True,
    )
    schedule_circle_recompute(circle_id)


def schedule_circle_recompute(circle_id: str, *, trigger_source: str = "chat_message") -> None:
    if not settings.zenq_live_events:
        return
    if circle_id in _pending_recomputes and not _pending_recomputes[circle_id].done():
        return

    async def _debounced() -> None:
        try:
            await asyncio.sleep(_DEBOUNCE_SECONDS)
            async with SessionLocal() as db:
                await materialize_circle_by_id(
                    db,
                    circle_id,
                    trigger_source=trigger_source,
                )
        except Exception:
            logger.exception("[ZenQ] debounced recompute failed for circle %s", circle_id)
        finally:
            _pending_recomputes.pop(circle_id, None)

    _pending_recomputes[circle_id] = asyncio.create_task(_debounced())


async def run_chat_message_zenq_pipeline(
    *,
    message_id: str,
    circle_id: str,
    actor_user_id: str,
    ras_score: float,
    substantive: bool,
    shield_action: str,
) -> None:
    """Background task entry — own DB session, never blocks WebSocket."""
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
        logger.exception("[ZenQ] chat_message pipeline failed for %s", message_id)


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
    await record_zenq_event(
        db,
        event_type="mentor_session",
        circle_id=circle_id,
        actor_id=mentor_user_id,
        idempotency_key=f"mentor_session:{session_id}",
        payload={
            "session_id": session_id,
            "duration_hrs": duration_hrs,
        },
        commit=True,
    )
    schedule_circle_recompute(circle_id, trigger_source="mentor_session")


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
            await record_zenq_event(
                db,
                event_type="target_achievement",
                circle_id=circle_id,
                actor_id=sponsor_user_id,
                idempotency_key=f"target:{log_id}",
                payload={
                    "log_id": log_id,
                    "target_status": target_status,
                },
                commit=True,
            )
        schedule_circle_recompute(circle_id, trigger_source="target_achievement")
    except Exception:
        logger.exception("[ZenQ] target_log pipeline failed for %s", log_id)


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
        logger.exception("[ZenQ] mentor_session pipeline failed for %s", session_id)
