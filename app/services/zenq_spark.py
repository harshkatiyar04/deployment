"""Student ZenQ Spark — breakthrough recognition (Phase 4)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.algorithms.zenq.constants import SPARK_COOLDOWN_DAYS, SPARK_DURATION_DAYS
from app.models.zenq import ZenqSparkEvent


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def circle_has_active_spark(db: AsyncSession, circle_id: str) -> bool:
    now = _utcnow()
    res = await db.execute(
        select(ZenqSparkEvent.id)
        .where(
            ZenqSparkEvent.circle_id == circle_id,
            ZenqSparkEvent.expires_at > now,
        )
        .limit(1)
    )
    return res.scalar_one_or_none() is not None


async def active_spark_student_ids(db: AsyncSession, circle_id: str) -> set[str]:
    now = _utcnow()
    res = await db.execute(
        select(ZenqSparkEvent.student_id).where(
            ZenqSparkEvent.circle_id == circle_id,
            ZenqSparkEvent.expires_at > now,
        )
    )
    return {row[0] for row in res.all()}


async def create_student_spark(
    db: AsyncSession,
    *,
    student_id: str,
    circle_id: str,
    reason: Optional[str] = None,
) -> dict[str, Any]:
    now = _utcnow()
    cooldown_since = now - timedelta(days=SPARK_COOLDOWN_DAYS)
    recent = await db.execute(
        select(ZenqSparkEvent)
        .where(
            ZenqSparkEvent.student_id == student_id,
            ZenqSparkEvent.created_at >= cooldown_since,
        )
        .order_by(ZenqSparkEvent.created_at.desc())
        .limit(1)
    )
    if recent.scalar_one_or_none():
        raise HTTPException(
            status_code=429,
            detail=f"ZenQ Spark can be triggered once every {SPARK_COOLDOWN_DAYS} days.",
        )

    expires_at = now + timedelta(days=SPARK_DURATION_DAYS)
    row = ZenqSparkEvent(
        student_id=student_id,
        circle_id=circle_id,
        reason=(reason or "").strip() or None,
        expires_at=expires_at,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)

    from app.services.zenq_event_processor import schedule_circle_recompute

    schedule_circle_recompute(circle_id, trigger_source="zenq_spark")
    return {
        "id": row.id,
        "student_id": student_id,
        "circle_id": circle_id,
        "reason": row.reason,
        "expires_at": row.expires_at.isoformat(),
        "active_days": SPARK_DURATION_DAYS,
    }
