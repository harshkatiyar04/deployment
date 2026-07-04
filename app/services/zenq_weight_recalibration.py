"""ZenQ weight recalibration proposals + admin approval (Phase 5)."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.algorithms.zenq.constants import DEFAULT_WEIGHTS
from app.algorithms.zenq.recalibration import compute_component_correlations, recalibrate_weights
from app.core.settings import settings
from app.db.session import SessionLocal
from app.models.zenq import ZenqComputationSnapshot, ZenqWeightConfig
from app.services.zenq_backfill import backfill_all_circles

logger = logging.getLogger(__name__)

COMPONENT_KEYS = ("T", "A", "S", "Cm", "In", "E", "C")
MIN_SNAPSHOT_SAMPLES = 30
MAX_SNAPSHOT_SAMPLES = 500
SNAPSHOT_LOOKBACK_DAYS = 90
MIN_WEIGHT_DELTA = 0.005


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def _load_active_weights(db: AsyncSession) -> dict[str, float]:
    res = await db.execute(
        select(ZenqWeightConfig)
        .where(ZenqWeightConfig.status == "active")
        .order_by(ZenqWeightConfig.created_at.desc())
        .limit(1)
    )
    row = res.scalar_one_or_none()
    if row and row.weights_json:
        return {str(k): float(v) for k, v in row.weights_json.items()}
    return dict(DEFAULT_WEIGHTS)


def _weight_delta(a: dict[str, float], b: dict[str, float]) -> float:
    keys = set(a) | set(b)
    return max(abs(float(a.get(k, 0.0)) - float(b.get(k, 0.0))) for k in keys)


async def gather_recalibration_dataset(
    db: AsyncSession,
) -> tuple[dict[str, list[float]], list[float], int]:
    since = _utcnow() - timedelta(days=SNAPSHOT_LOOKBACK_DAYS)
    res = await db.execute(
        select(ZenqComputationSnapshot)
        .where(
            ZenqComputationSnapshot.scope_type == "circle",
            ZenqComputationSnapshot.created_at >= since,
        )
        .order_by(ZenqComputationSnapshot.created_at.asc())
        .limit(MAX_SNAPSHOT_SAMPLES)
    )
    snapshots = res.scalars().all()

    component_history: dict[str, list[float]] = {k: [] for k in COMPONENT_KEYS}
    spd_outcomes: list[float] = []

    for snap in snapshots:
        outputs = snap.outputs_json or {}
        sponsors = outputs.get("sponsors") or []
        if not sponsors:
            continue

        per_component: dict[str, list[float]] = {k: [] for k in COMPONENT_KEYS}
        for sponsor in sponsors:
            components = sponsor.get("components") or {}
            for key in COMPONENT_KEYS:
                if key in components:
                    per_component[key].append(float(components[key]))

        if not any(per_component[k] for k in COMPONENT_KEYS):
            continue

        for key in COMPONENT_KEYS:
            vals = per_component[key]
            component_history[key].append(sum(vals) / len(vals) if vals else 0.0)
        spd_outcomes.append(float(outputs.get("spd_avg") or 0.0))

    sample_size = len(spd_outcomes)
    return component_history, spd_outcomes, sample_size


def _compute_correlations(
    component_history: dict[str, list[float]],
    spd_outcomes: list[float],
) -> dict[str, float]:
    return compute_component_correlations(
        component_history,
        spd_outcomes,
        min_samples=MIN_SNAPSHOT_SAMPLES,
    )


async def list_weight_configs(
    db: AsyncSession,
    *,
    limit: int = 20,
) -> dict[str, Any]:
    res = await db.execute(
        select(ZenqWeightConfig)
        .order_by(ZenqWeightConfig.created_at.desc())
        .limit(limit)
    )
    rows = res.scalars().all()
    active = None
    proposed: list[dict[str, Any]] = []
    history: list[dict[str, Any]] = []

    for row in rows:
        item = _weight_row_to_dict(row)
        if row.status == "active" and active is None:
            active = item
        elif row.status == "proposed":
            proposed.append(item)
        elif row.status in {"superseded", "rejected"}:
            history.append(item)

    pending_count = int(
        (
            await db.execute(
                select(func.count(ZenqWeightConfig.id)).where(ZenqWeightConfig.status == "proposed")
            )
        ).scalar()
        or 0
    )
    return {
        "active": active,
        "proposed": proposed,
        "history": history[:10],
        "pending_proposals": pending_count,
    }


def _weight_row_to_dict(row: ZenqWeightConfig) -> dict[str, Any]:
    return {
        "id": row.id,
        "status": row.status,
        "weights": row.weights_json or {},
        "analysis": row.analysis_json or {},
        "proposed_by": row.proposed_by,
        "approved_by": row.approved_by,
        "notes": row.notes,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "approved_at": row.approved_at.isoformat() if row.approved_at else None,
    }


async def propose_weight_recalibration(
    db: AsyncSession,
    *,
    proposed_by: str = "scheduler",
    notes: Optional[str] = None,
    force: bool = False,
) -> dict[str, Any]:
    if not settings.zenq_recalibration_enabled and not force:
        return {"ok": False, "reason": "recalibration_disabled"}

    current = await _load_active_weights(db)
    component_history, spd_outcomes, sample_size = await gather_recalibration_dataset(db)
    if sample_size < MIN_SNAPSHOT_SAMPLES:
        return {
            "ok": False,
            "reason": "insufficient_samples",
            "sample_size": sample_size,
            "required": MIN_SNAPSHOT_SAMPLES,
        }

    proposed_weights = recalibrate_weights(component_history, spd_outcomes, current)
    delta = _weight_delta(current, proposed_weights)
    correlations = _compute_correlations(component_history, spd_outcomes)

    if delta < MIN_WEIGHT_DELTA and not force:
        return {
            "ok": False,
            "reason": "no_material_change",
            "sample_size": sample_size,
            "max_delta": round(delta, 4),
        }

    recent_res = await db.execute(
        select(ZenqWeightConfig)
        .where(
            ZenqWeightConfig.status == "proposed",
            ZenqWeightConfig.created_at >= _utcnow() - timedelta(days=7),
        )
        .limit(1)
    )
    if recent_res.scalar_one_or_none() and not force:
        return {"ok": False, "reason": "proposal_already_pending"}

    row = ZenqWeightConfig(
        status="proposed",
        weights_json=proposed_weights,
        analysis_json={
            "sample_size": sample_size,
            "lookback_days": SNAPSHOT_LOOKBACK_DAYS,
            "correlations": correlations,
            "previous_weights": current,
            "max_delta": round(delta, 4),
        },
        proposed_by=proposed_by,
        notes=notes or "Correlation-guided recalibration proposal (admin approval required).",
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return {
        "ok": True,
        "proposal_id": row.id,
        "sample_size": sample_size,
        "max_delta": round(delta, 4),
        "weights": proposed_weights,
        "correlations": correlations,
    }


async def approve_weight_proposal(
    db: AsyncSession,
    proposal_id: str,
    *,
    approved_by: str,
    notes: Optional[str] = None,
) -> dict[str, Any]:
    res = await db.execute(select(ZenqWeightConfig).where(ZenqWeightConfig.id == proposal_id))
    proposal = res.scalar_one_or_none()
    if not proposal or proposal.status != "proposed":
        return {"ok": False, "error": "Proposal not found or not pending"}

    active_res = await db.execute(
        select(ZenqWeightConfig).where(ZenqWeightConfig.status == "active")
    )
    for active in active_res.scalars().all():
        active.status = "superseded"

    now = _utcnow()
    proposal.status = "active"
    proposal.approved_by = approved_by
    proposal.approved_at = now
    if notes:
        proposal.notes = notes
    await db.commit()

    asyncio.create_task(_backfill_after_weight_change())
    return {"ok": True, "proposal_id": proposal_id, "weights": proposal.weights_json}


async def reject_weight_proposal(
    db: AsyncSession,
    proposal_id: str,
    *,
    rejected_by: str,
    notes: Optional[str] = None,
) -> dict[str, Any]:
    res = await db.execute(select(ZenqWeightConfig).where(ZenqWeightConfig.id == proposal_id))
    proposal = res.scalar_one_or_none()
    if not proposal or proposal.status != "proposed":
        return {"ok": False, "error": "Proposal not found or not pending"}

    proposal.status = "rejected"
    proposal.approved_by = rejected_by
    proposal.approved_at = _utcnow()
    if notes:
        proposal.notes = notes
    await db.commit()
    return {"ok": True, "proposal_id": proposal_id}


async def run_scheduled_recalibration_proposal() -> dict[str, Any]:
    if not settings.zenq_recalibration_enabled:
        return {"ok": False, "reason": "recalibration_disabled"}
    async with SessionLocal() as db:
        return await propose_weight_recalibration(db, proposed_by="weekly_scheduler")


async def _backfill_after_weight_change() -> None:
    try:
        async with SessionLocal() as db:
            result = await backfill_all_circles(db)
        logger.info("[ZenQ recalibration] backfill after weight approval: %s", result)
    except Exception:
        logger.exception("[ZenQ recalibration] backfill after weight approval failed")
