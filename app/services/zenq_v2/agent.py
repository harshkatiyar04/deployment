"""Agent run — R1–R5 proposals; approve applies next-month weights when agent.apply=true."""

from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any, Optional, Set
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.algorithms.zenq_v2.agent_rules import apply_deltas, propose_weight_deltas
from app.algorithms.zenq_v2.params import W_BASE
from app.services.zenq_v2.weights import (
    assert_weights_shape,
    compute_neutrality,
    load_params,
    weights_from_row,
)

logger = logging.getLogger(__name__)


def _next_month_start(month: date) -> date:
    if month.month == 12:
        return date(month.year + 1, 1, 1)
    return date(month.year, month.month + 1, 1)


def _add_months(month: date, n: int) -> date:
    y, m = month.year, month.month + n
    while m > 12:
        m -= 12
        y += 1
    while m < 1:
        m += 12
        y -= 1
    return date(y, m, 1)


async def run_agent_for_month(
    db: AsyncSession,
    month: date,
    signals: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    Analyse closed month data; write agent_run for month+1 (proposal target).
    Never mutates factor_weights_month here — apply happens on approve when agent_apply.
    """
    signal_month = date(month.year, month.month, 1)
    target_month = _next_month_start(signal_month)
    params = await load_params(db)
    apply_flag = bool(params.get("agent_apply"))
    sig = signals or await _default_signals(db, signal_month)
    blocked = await _cooldown_blocked_rules(db, target_month, int(params.get("agent_cooldown_months") or 3))
    deltas, fired, reasoning = propose_weight_deltas(sig, params, blocked_rules=blocked)

    w_row = (
        await db.execute(
            text(
                'SELECT * FROM "ZENK"."zenq_v2_factor_weights_month" WHERE month = :m'
            ),
            {"m": signal_month},
        )
    ).mappings().first()
    current = weights_from_row(dict(w_row)) if w_row else dict(W_BASE)
    proposed = apply_deltas(current, deltas)
    assert_weights_shape(proposed)

    run_id = str(uuid4())
    status = "LOGGED"
    await db.execute(
        text(
            """
            INSERT INTO "ZENK"."zenq_v2_agent_run"(
                id, month, signals_json, rules_fired_json, proposed_json,
                reasoning_text, status
            ) VALUES (
                CAST(:id AS uuid), :month, CAST(:sig AS jsonb), CAST(:fired AS jsonb),
                CAST(:prop AS jsonb), :reason, :status
            )
            """
        ),
        {
            "id": run_id,
            "month": target_month,
            "sig": json.dumps({**sig, "signal_month": signal_month.isoformat()}),
            "fired": json.dumps(fired),
            "prop": json.dumps({"deltas": deltas, "weights": proposed}),
            "reason": reasoning,
            "status": status,
        },
    )
    await db.commit()

    return {
        "id": run_id,
        "month": target_month.isoformat(),
        "signal_month": signal_month.isoformat(),
        "rules_fired": fired,
        "proposed": proposed,
        "deltas": deltas,
        "reasoning_text": reasoning,
        "status": status,
        "agent_apply": apply_flag,
        "applied_to_live_weights": False,
        "cooldown_blocked": sorted(blocked),
    }


async def list_agent_runs(db: AsyncSession, limit: int = 20) -> list[dict[str, Any]]:
    rows = (
        await db.execute(
            text(
                """
                SELECT id::text, month, signals_json, rules_fired_json, proposed_json,
                       reasoning_text, status, reviewed_by, created_at
                FROM "ZENK"."zenq_v2_agent_run"
                ORDER BY created_at DESC LIMIT :lim
                """
            ),
            {"lim": limit},
        )
    ).mappings().all()
    out = []
    for r in rows:
        out.append(
            {
                "id": r["id"],
                "month": r["month"].isoformat() if r["month"] else None,
                "signals": r["signals_json"],
                "rules_fired": r["rules_fired_json"],
                "proposed": r["proposed_json"],
                "reasoning_text": r["reasoning_text"],
                "status": r["status"],
                "reviewed_by": r["reviewed_by"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            }
        )
    return out


async def review_agent_run(
    db: AsyncSession, run_id: str, *, reviewed_by: str, approve_note: bool = True
) -> dict[str, Any]:
    """
    Mark reviewed. When approve + params.agent_apply, upsert approved weights into
    factor_weights_month for the run's target month (source=AGENT) so resolve_weights
    / next close uses them.
    """
    row = (
        await db.execute(
            text(
                """
                SELECT id::text AS id, month, proposed_json, status
                FROM "ZENK"."zenq_v2_agent_run"
                WHERE id = CAST(:id AS uuid)
                """
            ),
            {"id": run_id},
        )
    ).mappings().first()
    if not row:
        return {
            "id": run_id,
            "ok": False,
            "reason": "run not found",
            "applied_to_live_weights": False,
        }

    new_status = "APPROVED" if approve_note else "REJECTED"
    applied = False
    apply_flag = False
    source = None
    target_month = row["month"]

    if approve_note:
        params = await load_params(db)
        apply_flag = bool(params.get("agent_apply"))
        if apply_flag:
            prop = row["proposed_json"]
            if isinstance(prop, str):
                prop = json.loads(prop)
            weights = (prop or {}).get("weights") or prop
            if isinstance(weights, dict) and all(k in weights for k in W_BASE):
                w = {k: float(weights[k]) for k in W_BASE}
                assert_weights_shape(w)
                prev_month = (
                    date(target_month.year, target_month.month - 1, 1)
                    if target_month.month > 1
                    else date(target_month.year - 1, 12, 1)
                )
                prev_row = (
                    await db.execute(
                        text(
                            'SELECT * FROM "ZENK"."zenq_v2_factor_weights_month" WHERE month = :m'
                        ),
                        {"m": prev_month},
                    )
                ).mappings().first()
                prev_w = weights_from_row(dict(prev_row)) if prev_row else dict(W_BASE)
                nu = compute_neutrality(w, prev_w)
                await db.execute(
                    text(
                        """
                        INSERT INTO "ZENK"."zenq_v2_factor_weights_month"(
                            month, presence, learning, chat, kia, funding, growth, student,
                            neutrality_scale, source, proposal_id, closed_at
                        ) VALUES (
                            :month, :presence, :learning, :chat, :kia, :funding, :growth, :student,
                            :nu, 'AGENT', CAST(:proposal_id AS uuid), NOW()
                        )
                        ON CONFLICT (month) DO UPDATE SET
                            presence = EXCLUDED.presence,
                            learning = EXCLUDED.learning,
                            chat = EXCLUDED.chat,
                            kia = EXCLUDED.kia,
                            funding = EXCLUDED.funding,
                            growth = EXCLUDED.growth,
                            student = EXCLUDED.student,
                            neutrality_scale = EXCLUDED.neutrality_scale,
                            source = 'AGENT',
                            proposal_id = EXCLUDED.proposal_id,
                            closed_at = NOW()
                        """
                    ),
                    {
                        "month": target_month,
                        "presence": w["presence"],
                        "learning": w["learning"],
                        "chat": w["chat"],
                        "kia": w["kia"],
                        "funding": w["funding"],
                        "growth": w["growth"],
                        "student": w["student"],
                        "nu": nu,
                        "proposal_id": run_id,
                    },
                )
                applied = True
                source = "AGENT"
                new_status = "APPLIED"

    await db.execute(
        text(
            """
            UPDATE "ZENK"."zenq_v2_agent_run"
            SET status = :st, reviewed_by = :who, reviewed_at = NOW()
            WHERE id = CAST(:id AS uuid)
            """
        ),
        {"st": new_status, "who": reviewed_by, "id": run_id},
    )
    await db.commit()
    return {
        "id": run_id,
        "status": new_status,
        "month": target_month.isoformat() if target_month else None,
        "applied_to_live_weights": applied,
        "agent_apply": apply_flag,
        "source": source,
        "agent_apply_unchanged": not apply_flag,
    }


async def _cooldown_blocked_rules(
    db: AsyncSession, target_month: date, cooldown_months: int
) -> Set[str]:
    if cooldown_months <= 0:
        return set()
    since = _add_months(target_month, -cooldown_months)
    rows = (
        await db.execute(
            text(
                """
                SELECT rules_fired_json FROM "ZENK"."zenq_v2_agent_run"
                WHERE month >= :since AND month < :tgt
                  AND status IN ('LOGGED', 'APPROVED', 'APPLIED', 'REVIEWED_OK', 'REJECTED', 'REVIEWED_REJECT')
                """
            ),
            {"since": since, "tgt": target_month},
        )
    ).mappings().all()
    blocked: Set[str] = set()
    for r in rows:
        fired = r["rules_fired_json"]
        if isinstance(fired, str):
            fired = json.loads(fired)
        if isinstance(fired, list):
            blocked.update(str(x) for x in fired)
    return blocked


async def _default_signals(db: AsyncSession, month: date) -> dict[str, Any]:
    """Shares from member_month class IP × current weights / baseline (Tech Guide run_agent)."""
    w_row = (
        await db.execute(
            text(
                'SELECT * FROM "ZENK"."zenq_v2_factor_weights_month" WHERE month = :m'
            ),
            {"m": month},
        )
    ).mappings().first()
    w = weights_from_row(dict(w_row)) if w_row else dict(W_BASE)

    agg = (
        await db.execute(
            text(
                """
                SELECT
                    COALESCE(SUM(ip_presence),0) AS presence,
                    COALESCE(SUM(ip_learning),0) AS learning,
                    COALESCE(SUM(ip_chat),0) AS chat,
                    COALESCE(SUM(ip_kia),0) AS kia,
                    COALESCE(SUM(ip_funding),0) AS funding,
                    COALESCE(SUM(ip_growth),0) AS growth
                FROM "ZENK"."zenq_v2_member_month"
                WHERE month = :m AND closed_at IS NOT NULL
                """
            ),
            {"m": month},
        )
    ).mappings().first() or {}

    def _share(key: str) -> float:
        pts = float(agg.get(key) or 0)
        return pts * (float(w.get(key, W_BASE[key])) / float(W_BASE[key]))

    weighted = {k: _share(k) for k in ("presence", "learning", "chat", "kia", "funding", "growth")}
    mip = sum(weighted.values()) or 1.0

    gr_row = (
        await db.execute(
            text(
                """
                SELECT
                    AVG(growth_ratio) FILTER (WHERE growth_ratio IS NOT NULL) AS mean_gr,
                    COUNT(*) FILTER (WHERE growth_ratio IS NOT NULL) AS n_impact,
                    COUNT(*) FILTER (WHERE growth_ratio IS NOT NULL AND growth_ratio < 0.5) AS n_regress
                FROM "ZENK"."zenq_v2_circle_month"
                WHERE month = :m AND closed_at IS NOT NULL
                """
            ),
            {"m": month},
        )
    ).mappings().first() or {}

    prev3 = _add_months(month, -3)
    gr_prev = (
        await db.execute(
            text(
                """
                SELECT AVG(growth_ratio) FILTER (WHERE growth_ratio IS NOT NULL) AS mean_gr
                FROM "ZENK"."zenq_v2_circle_month"
                WHERE month = :m AND closed_at IS NOT NULL
                """
            ),
            {"m": prev3},
        )
    ).mappings().first()

    ref_window = 3
    ref_from = _add_months(month, -(ref_window - 1))
    nxt = _next_month_start(month)
    refs = (
        await db.execute(
            text(
                """
                SELECT COUNT(*)::int AS n
                FROM "ZENK"."zenq_v2_event_ledger"
                WHERE event_code = 'REFERRAL_ACTIVATED'
                  AND ts >= :a AND ts < :b
                """
            ),
            {"a": ref_from, "b": nxt},
        )
    ).mappings().first()

    n_impact = int(gr_row.get("n_impact") or 0)
    n_regress = int(gr_row.get("n_regress") or 0)
    mean_gr = gr_row.get("mean_gr")
    mean_gr_3m = (gr_prev or {}).get("mean_gr")

    return {
        "chat_share": weighted["chat"] / mip,
        "presence_share": weighted["presence"] / mip,
        "learning_share": weighted["learning"] / mip,
        "funding_share": weighted["funding"] / mip,
        "kia_share": weighted["kia"] / mip,
        "growth_share": weighted["growth"] / mip,
        "mean_growth_ratio": float(mean_gr) if mean_gr is not None else None,
        "mean_growth_ratio_3m": float(mean_gr_3m) if mean_gr_3m is not None else None,
        "regress_share": (n_regress / n_impact) if n_impact else 0.0,
        "referral_activations": int((refs or {}).get("n") or 0),
        "new_circles_in_window": 0,
    }
