"""resolve_weights + factor_weights_month (Tech Guide §6 / §11). Phase 2b: ν logged, agent.apply gate."""

from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.algorithms.zenq_v2.params import ALGORITHM_VERSION, LAUNCH_PARAMS, W_BASE, W_BOUNDS

logger = logging.getLogger(__name__)

_WEIGHT_KEYS = tuple(W_BASE.keys())


def _prev_month_start(month: date) -> date:
    if month.month == 1:
        return date(month.year - 1, 12, 1)
    return date(month.year, month.month - 1, 1)


def weights_from_row(row: dict[str, Any]) -> dict[str, float]:
    return {k: float(row[k]) for k in _WEIGHT_KEYS if k in row}


def weights_dict_from_row(row: dict[str, Any]) -> dict[str, float]:
    return weights_from_row(row)


def weights_equal(a: dict[str, float], b: dict[str, float], *, eps: float = 1e-6) -> bool:
    for k in _WEIGHT_KEYS:
        if abs(float(a.get(k, 0)) - float(b.get(k, 0))) > eps:
            return False
    return True


def assert_weights_shape(w: dict[str, float], bounds: Optional[dict[str, Any]] = None) -> None:
    """T5: sum ≈ 100 and each factor within bounds."""
    total = sum(float(w.get(k, 0)) for k in _WEIGHT_KEYS)
    if abs(total - 100.0) > 1e-3:
        raise AssertionError(f"weights sum {total} != 100")
    b = bounds or W_BOUNDS
    for k in _WEIGHT_KEYS:
        raw = b[k]
        lo, hi = float(raw[0]), float(raw[1])
        v = float(w[k])
        if v < lo - 1e-6 or v > hi + 1e-6:
            raise AssertionError(f"weight {k}={v} outside [{lo}, {hi}]")


def compute_neutrality(
    w_new: dict[str, float],
    w_old: dict[str, float],
    *,
    prior_actual_earnings: Optional[float] = None,
    prior_rescored_earnings: Optional[float] = None,
) -> float:
    """
    Level neutrality ν(m). Equals 1.0 while weights unchanged (launch / agent.apply=false).
    When weights change: actual ÷ rescored (Tech Guide L.3); missing rescored → 1.0.
    """
    if weights_equal(w_new, w_old):
        return 1.0
    if prior_rescored_earnings is None or prior_rescored_earnings == 0:
        logger.info("[ZenQ v2] ν=1.0 fallback (weights changed but no rescored prior month)")
        return 1.0
    actual = float(prior_actual_earnings or 0.0)
    return actual / float(prior_rescored_earnings)


def pick_weight_source(
    *,
    prev_w: dict[str, float],
    agent_apply: bool,
    approved_proposal: Optional[dict[str, float]] = None,
    manual_override: Optional[dict[str, float]] = None,
) -> tuple[dict[str, float], str, Optional[str]]:
    """
    Tech Guide resolve_weights priority: MANUAL → AGENT (if apply) → CARRIED/BASELINE.
    Returns (weights, source, proposal_id_placeholder).
    """
    if manual_override is not None:
        w = {k: float(manual_override[k]) for k in _WEIGHT_KEYS}
        assert_weights_shape(w)
        return w, "MANUAL", None
    if agent_apply and approved_proposal is not None:
        w = {k: float(approved_proposal[k]) for k in _WEIGHT_KEYS}
        assert_weights_shape(w)
        return w, "AGENT", None
    w = {k: float(prev_w[k]) for k in _WEIGHT_KEYS}
    assert_weights_shape(w)
    # Distinguish first baseline vs carried for audit
    if weights_equal(w, W_BASE) and all(
        abs(float(prev_w.get(k, 0)) - float(W_BASE[k])) < 1e-6 for k in _WEIGHT_KEYS
    ):
        # Caller sets BASELINE vs CARRIED based on whether a prior row existed
        return w, "CARRIED", None
    return w, "CARRIED", None


async def load_params(db: AsyncSession, version_id: Optional[str] = None) -> dict[str, Any]:
    vid = version_id or ALGORITHM_VERSION
    row = (
        await db.execute(
            text(
                'SELECT params_json FROM "ZENK"."zenq_v2_weights" WHERE version_id = :vid'
            ),
            {"vid": vid},
        )
    ).mappings().first()
    if not row:
        row = (
            await db.execute(
                text(
                    """
                    SELECT params_json FROM "ZENK"."zenq_v2_weights"
                    ORDER BY effective_from DESC NULLS LAST, version_id DESC
                    LIMIT 1
                    """
                )
            )
        ).mappings().first()
    if not row:
        return dict(LAUNCH_PARAMS)
    raw = row["params_json"]
    if isinstance(raw, str):
        return json.loads(raw)
    return dict(raw or LAUNCH_PARAMS)


async def _approved_agent_proposal(
    db: AsyncSession, month: date
) -> Optional[tuple[dict[str, float], str]]:
    row = (
        await db.execute(
            text(
                """
                SELECT id::text AS id, proposed_json, status
                FROM "ZENK"."zenq_v2_agent_run"
                WHERE month = :m
                  AND status IN ('APPROVED', 'REVIEWED_OK')
                ORDER BY created_at DESC
                LIMIT 1
                """
            ),
            {"m": month},
        )
    ).mappings().first()
    if not row:
        return None
    prop = row["proposed_json"]
    if isinstance(prop, str):
        prop = json.loads(prop)
    weights = (prop or {}).get("weights") or prop
    if not isinstance(weights, dict) or not all(k in weights for k in _WEIGHT_KEYS):
        return None
    return {k: float(weights[k]) for k in _WEIGHT_KEYS}, row["id"]


async def resolve_weights(
    db: AsyncSession,
    month: date,
    *,
    agent_apply: Optional[bool] = None,
    manual_override: Optional[dict[str, float]] = None,
) -> dict[str, Any]:
    """
    Return weight row for month. ν = 1.0 while weights unchanged / agent not applying.
    Never reads AGENT proposals when agent_apply is false (T15).
    """
    month = date(month.year, month.month, 1)
    existing = (
        await db.execute(
            text(
                'SELECT * FROM "ZENK"."zenq_v2_factor_weights_month" WHERE month = :m'
            ),
            {"m": month},
        )
    ).mappings().first()
    if existing:
        out = dict(existing)
        out["agent_apply"] = bool(
            agent_apply
            if agent_apply is not None
            else (await load_params(db)).get("agent_apply")
        )
        return out

    params = await load_params(db)
    apply = bool(params.get("agent_apply")) if agent_apply is None else bool(agent_apply)

    prev_month = _prev_month_start(month)
    prev_row = (
        await db.execute(
            text(
                'SELECT * FROM "ZENK"."zenq_v2_factor_weights_month" WHERE month = :m'
            ),
            {"m": prev_month},
        )
    ).mappings().first()
    had_prev = prev_row is not None
    prev_w = weights_from_row(dict(prev_row)) if prev_row else dict(W_BASE)

    approved: Optional[dict[str, float]] = None
    proposal_id: Optional[str] = None
    if apply:
        got = await _approved_agent_proposal(db, month)
        if got:
            approved, proposal_id = got

    if manual_override is not None:
        w, source, _ = pick_weight_source(
            prev_w=prev_w,
            agent_apply=False,
            manual_override=manual_override,
        )
    elif apply and approved is not None:
        w, source, _ = pick_weight_source(
            prev_w=prev_w,
            agent_apply=True,
            approved_proposal=approved,
        )
    else:
        w = dict(prev_w)
        assert_weights_shape(w)
        source = "BASELINE" if not had_prev else "CARRIED"
        proposal_id = None

    nu = compute_neutrality(w, prev_w)

    await db.execute(
        text(
            """
            INSERT INTO "ZENK"."zenq_v2_factor_weights_month"(
                month, presence, learning, chat, kia, funding, growth, student,
                neutrality_scale, source, proposal_id, closed_at
            ) VALUES (
                :month, :presence, :learning, :chat, :kia, :funding, :growth, :student,
                :nu, :source, :proposal_id, NOW()
            )
            ON CONFLICT (month) DO NOTHING
            """
        ),
        {
            "month": month,
            "presence": w["presence"],
            "learning": w["learning"],
            "chat": w["chat"],
            "kia": w["kia"],
            "funding": w["funding"],
            "growth": w["growth"],
            "student": w["student"],
            "nu": nu,
            "source": source,
            "proposal_id": proposal_id,  # UUID or None
        },
    )
    await db.commit()
    return {
        "month": month,
        **w,
        "neutrality_scale": nu,
        "source": source,
        "proposal_id": proposal_id,
        "agent_apply": apply,
    }


async def get_latest_factor_weights(db: AsyncSession) -> Optional[dict[str, Any]]:
    row = (
        await db.execute(
            text(
                """
                SELECT * FROM "ZENK"."zenq_v2_factor_weights_month"
                ORDER BY month DESC LIMIT 1
                """
            )
        )
    ).mappings().first()
    if not row:
        return None
    d = dict(row)
    m = d.get("month")
    if isinstance(m, date):
        d["month"] = m.isoformat()
    closed = d.get("closed_at")
    if closed is not None and hasattr(closed, "isoformat"):
        d["closed_at"] = closed.isoformat()
    if d.get("proposal_id") is not None:
        d["proposal_id"] = str(d["proposal_id"])
    return d


async def list_factor_weights(db: AsyncSession, limit: int = 12) -> list[dict[str, Any]]:
    rows = (
        await db.execute(
            text(
                """
                SELECT * FROM "ZENK"."zenq_v2_factor_weights_month"
                ORDER BY month DESC LIMIT :lim
                """
            ),
            {"lim": limit},
        )
    ).mappings().all()
    out = []
    for row in rows:
        d = dict(row)
        m = d.get("month")
        if isinstance(m, date):
            d["month"] = m.isoformat()
        closed = d.get("closed_at")
        if closed is not None and hasattr(closed, "isoformat"):
            d["closed_at"] = closed.isoformat()
        if d.get("proposal_id") is not None:
            d["proposal_id"] = str(d["proposal_id"])
        out.append(d)
    return out
