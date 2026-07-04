"""Sponsor-facing ZenQ display — engine ZIQ with legacy ZQA fallback (Phase 3)."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.models import SponsorCircle
from app.core.settings import settings
from app.models.school import SchoolStudent
from app.models.zenq import ZenqCircleScore, ZenqComputationSnapshot
from app.services.zenq_materializer import materialize_circle_by_id


async def _legacy_zqa_avg(db: AsyncSession, circle_id: str) -> Optional[float]:
    avg_res = await db.execute(
        select(func.avg(SchoolStudent.zqa_score)).where(SchoolStudent.circle_id == circle_id)
    )
    raw = avg_res.scalar_one()
    if raw is None:
        return None
    return round(float(raw), 1)


async def _zenq_change_from_snapshots(db: AsyncSession, circle_id: str) -> Optional[int]:
    res = await db.execute(
        select(ZenqComputationSnapshot)
        .where(
            ZenqComputationSnapshot.circle_id == circle_id,
            ZenqComputationSnapshot.scope_type == "circle",
        )
        .order_by(ZenqComputationSnapshot.created_at.desc())
        .limit(2)
    )
    snaps = res.scalars().all()
    if len(snaps) < 2:
        return None
    cur = float((snaps[0].outputs_json or {}).get("ziq") or 0)
    prev = float((snaps[1].outputs_json or {}).get("ziq") or 0)
    return int(round(cur - prev))


async def _load_engine_row(
    db: AsyncSession,
    circle_id: str,
) -> Optional[ZenqCircleScore]:
    res = await db.execute(
        select(ZenqCircleScore).where(ZenqCircleScore.circle_id == circle_id)
    )
    return res.scalar_one_or_none()


async def ensure_circle_materialized(
    db: AsyncSession,
    circle_id: str,
) -> Optional[ZenqCircleScore]:
    row = await _load_engine_row(db, circle_id)
    if row is not None:
        return row
    circle_res = await db.execute(select(SponsorCircle).where(SponsorCircle.id == circle_id))
    circle = circle_res.scalar_one_or_none()
    if not circle:
        return None
    await materialize_circle_by_id(db, circle_id, trigger_source="product_read")
    return await _load_engine_row(db, circle_id)


async def _engine_display_from_row(
    db: AsyncSession,
    engine_row: ZenqCircleScore,
    *,
    student_count: int,
    legacy_avg: Optional[float],
) -> dict[str, Any]:
    ziq = int(round(float(engine_row.ziq or 0)))
    change = await _zenq_change_from_snapshots(db, engine_row.circle_id)
    summary = engine_row.summary_json or {}
    zcq_inputs = summary.get("zcq_inputs") or {}
    return {
        "zenq_score": ziq,
        "zenq_available": ziq > 0 or student_count > 0 or engine_row.sponsor_count > 0,
        "zenq_source": "engine",
        "zenq_change": change,
        "zenq_breakdown": {
            "ziq": round(float(engine_row.ziq or 0), 2),
            "zeq_avg": round(float(engine_row.zeq_avg or 0), 4),
            "zcq": round(float(engine_row.zcq or 0), 4),
            "spd_avg": round(float(engine_row.spd_avg or 0), 4),
            "ziq_per_member": round(float(engine_row.ziq_per_member or 0), 2),
            "formula": "ZIQ = 100 × ZEQ × ZCQ × SPD",
            "need_band": zcq_inputs.get("need_band"),
            "attendance_30d_ratio": zcq_inputs.get("attendance_30d_ratio"),
        },
        "legacy_zqa_avg": int(legacy_avg) if legacy_avg is not None else None,
    }


async def resolve_circle_zenq_display(
    db: AsyncSession,
    circle_id: str,
    *,
    student_count: int,
    materialize_if_missing: bool = True,
) -> dict[str, Any]:
    """
    Product ZenQ score for a circle.
    Uses materialized ZIQ when a row exists (e.g. after admin backfill).
    Falls back to legacy average ZQA only when no materialized score yet.
    On-demand materialization runs only when ZENQ_ENGINE_ENABLED=true.
    """
    legacy_avg = await _legacy_zqa_avg(db, circle_id) if student_count > 0 else None

    engine_row = await _load_engine_row(db, circle_id)
    if engine_row is None and settings.zenq_engine_enabled and materialize_if_missing:
        engine_row = await ensure_circle_materialized(db, circle_id)

    if engine_row is not None:
        return await _engine_display_from_row(
            db, engine_row, student_count=student_count, legacy_avg=legacy_avg
        )

    return {
        "zenq_score": int(legacy_avg) if legacy_avg is not None else None,
        "zenq_available": student_count > 0 and legacy_avg is not None,
        "zenq_source": "legacy_zqa_avg",
        "zenq_change": None,
        "zenq_breakdown": None,
        "legacy_zqa_avg": int(legacy_avg) if legacy_avg is not None else None,
    }


async def list_engine_league_rows(
    db: AsyncSession,
    my_circle_id: str,
    *,
    limit: int = 25,
) -> list[dict[str, Any]]:
    res = await db.execute(
        select(ZenqCircleScore)
        .order_by(ZenqCircleScore.ziq.desc(), ZenqCircleScore.updated_at.desc())
        .limit(limit)
    )
    rows = res.scalars().all()
    out: list[dict[str, Any]] = []
    for idx, row in enumerate(rows, start=1):
        out.append(
            {
                "rank": idx,
                "circle_name": row.circle_name or "Circle",
                "impact_score": int(round(float(row.ziq or 0))),
                "student_count": int(row.student_count or 0),
                "zenq_avg": int(round(float(row.ziq or 0))),
                "is_mine": row.circle_id == my_circle_id,
            }
        )
    return out
