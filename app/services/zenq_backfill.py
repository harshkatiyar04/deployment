"""Backfill ZenQ materialized scores for all circles (admin-triggered, sequential)."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.models import SponsorCircle
from app.services.zenq_materializer import materialize_circle

logger = logging.getLogger(__name__)


async def backfill_all_circles(
    db: AsyncSession,
    *,
    status_filter: str = "active",
) -> dict[str, Any]:
    """Recompute every circle sequentially — safe for a single AsyncSession."""
    final: dict[str, Any] | None = None
    async for event in backfill_all_circles_progress(db, status_filter=status_filter):
        if event.get("phase") == "done":
            final = event
    if not final:
        return {"total_circles": 0, "processed": 0, "failed": 0, "errors": []}
    return {
        "total_circles": final["total_circles"],
        "processed": final["processed"],
        "failed": final["failed"],
        "errors": final.get("errors") or [],
    }


async def backfill_all_circles_progress(
    db: AsyncSession,
    *,
    status_filter: str = "active",
) -> AsyncIterator[dict[str, Any]]:
    """Yield progress events while recomputing every circle."""
    q = select(SponsorCircle).order_by(SponsorCircle.name.asc())
    if status_filter:
        q = q.where(SponsorCircle.status == status_filter)
    res = await db.execute(q)
    circles = res.scalars().all()
    total = len(circles)

    yield {
        "phase": "start",
        "total_circles": total,
        "processed": 0,
        "ok": 0,
        "failed": 0,
        "percent": 0,
        "current_circle": None,
    }

    ok_count = 0
    errors: list[dict[str, str]] = []

    for index, circle in enumerate(circles):
        try:
            await materialize_circle(db, circle, trigger_source="backfill", commit=True)
            ok_count += 1
        except Exception as exc:
            logger.exception("[ZenQ backfill] circle %s failed", circle.id)
            await db.rollback()
            errors.append({"circle_id": circle.id, "name": circle.name, "error": str(exc)[:200]})

        done = index + 1
        percent = int(round((done / total) * 100)) if total else 100
        yield {
            "phase": "progress",
            "total_circles": total,
            "processed": done,
            "ok": ok_count,
            "failed": len(errors),
            "percent": min(99, percent) if done < total else 100,
            "current_circle": circle.name,
        }

    yield {
        "phase": "done",
        "total_circles": total,
        "processed": ok_count,
        "failed": len(errors),
        "errors": errors[:20],
        "percent": 100,
        "current_circle": None,
    }
