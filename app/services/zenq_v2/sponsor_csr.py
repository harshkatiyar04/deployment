"""Phase 6 — sponsor / CSR tools (flags false at launch)."""

from __future__ import annotations

import json
from datetime import date
from typing import Any, Optional, Sequence
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.algorithms.zenq_v2.csr import (
    DEFAULT_CSR_WEIGHTS,
    csr_allocation,
    equal_split_allocations,
    impact_proxy,
)
from app.algorithms.zenq_v2.language import funder_claim_language
from app.algorithms.zenq_v2.params import LAUNCH_PARAMS
from app.core.settings import settings
from app.services.zenq_v2.weights import load_params

_STUDENT_KEYS = ("student_id", "student_ids", "child_id", "child_ids", "enrollment_id")


def _display(lifetime_ip: float, params: Optional[dict[str, Any]] = None) -> float:
    div = float((params or LAUNCH_PARAMS).get("display_divisor") or 1)
    return float(lifetime_ip or 0) / div


def _strip_student_keys(payload: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in payload.items() if k not in _STUDENT_KEYS}


async def list_sponsors_for_admin(db: AsyncSession, *, limit: int = 200) -> dict[str, Any]:
    """Sponsors by display name for Admin Lab (no UUID hunting)."""
    rows = (
        await db.execute(
            text(
                """
                SELECT DISTINCT ON (cm.user_id)
                    cm.user_id::text AS sponsor_id,
                    COALESCE(NULLIF(sr.full_name, ''), sr.email, cm.user_id::text) AS name
                FROM "ZENK"."circle_members" cm
                JOIN "ZENK"."signup_requests" sr ON sr.id = cm.user_id
                WHERE lower(cm.role) IN ('sponsor', 'sponsor_leader', 'lead')
                ORDER BY cm.user_id, sr.full_name ASC NULLS LAST
                LIMIT :lim
                """
            ),
            {"lim": limit},
        )
    ).mappings().all()
    items = sorted(
        [{"sponsor_id": r["sponsor_id"], "name": r["name"]} for r in rows],
        key=lambda x: (x["name"] or "").lower(),
    )
    return {"items": items, "claim_language": funder_claim_language()}


async def list_sponsor_circles(db: AsyncSession, sponsor_id: str) -> dict[str, Any]:
    params = await load_params(db)
    flags = params.get("flags") or {}
    yield_on = bool(flags.get("sponsor_yield"))
    rows = (
        await db.execute(
            text(
                """
                SELECT DISTINCT ON (cm.circle_id)
                    cm.circle_id::text AS circle_id,
                    sc.name AS circle_name,
                    cm.lifetime_zenq,
                    cm.yield_per_lakh,
                    cm.milestone,
                    cm.sgi_band,
                    cm.k,
                    cm.return_pct,
                    cm.contribution_cum,
                    cm.month,
                    cm.earnings
                FROM "ZENK"."zenq_v2_circle_month" cm
                JOIN "ZENK"."sponsor_circles" sc ON sc.id = cm.circle_id
                JOIN "ZENK"."circle_members" mem
                  ON mem.circle_id = cm.circle_id
                 AND mem.user_id = CAST(:sponsor_id AS uuid)
                 AND lower(mem.role) IN ('sponsor', 'sponsor_leader', 'lead')
                ORDER BY cm.circle_id, cm.month DESC
                LIMIT 100
                """
            ),
            {"sponsor_id": sponsor_id},
        )
    ).mappings().all()

    items: list[dict[str, Any]] = []
    for r in rows:
        life = float(r["lifetime_zenq"] or 0)
        ret = r["return_pct"]
        item = _strip_student_keys(
            {
                "circle_id": r["circle_id"],
                "circle_name": r["circle_name"],
                "lifetime": life,
                "lifetime_display": _display(life, params),
                "milestone": r["milestone"],
                "sgi_band": r["sgi_band"],
                "k": float(r["k"] or 1.0),
                "contribution_cum": float(r["contribution_cum"] or 0),
                "return_pct": float(ret) if ret is not None else None,
                "return_label": (
                    f"{float(ret) * 100:.0f}%" if ret is not None else "newly listed"
                ),
                "as_of_month": r["month"].isoformat() if r["month"] else None,
            }
        )
        if yield_on:
            item["yield_per_lakh"] = (
                float(r["yield_per_lakh"]) if r["yield_per_lakh"] is not None else None
            )
        items.append(item)

    return {
        "sponsor_id": sponsor_id,
        "items": items,
        "sponsor_yield_visible": yield_on,
        "csr_tool_visible": bool(flags.get("csr_tool")),
        "claim_language": funder_claim_language(),
        "product_flag": bool(settings.zenq_v2_product),
    }


async def _load_eligible_circles(
    db: AsyncSession,
    *,
    sponsor_id: Optional[str],
    as_of_month: Optional[date],
) -> list[dict[str, Any]]:
    """Live circle-months for allocation — circle name only, no child ids.

    Pilot (no seal): latest circle_month snapshot per circle is eligible even when
    closed_at is NULL.
    """
    clauses: list[str] = ["1=1"]
    binds: dict[str, Any] = {}
    join_sponsor = ""
    if sponsor_id:
        join_sponsor = """
            JOIN "ZENK"."circle_members" mem
              ON mem.circle_id = cm.circle_id
             AND mem.user_id = CAST(:sponsor_id AS uuid)
             AND lower(mem.role) IN ('sponsor', 'sponsor_leader', 'lead')
        """
        binds["sponsor_id"] = sponsor_id
    if as_of_month:
        clauses.append("cm.month = :as_of_month")
        binds["as_of_month"] = as_of_month

    where = " AND ".join(clauses)
    # Latest closed month per circle when as_of_month not set
    if as_of_month:
        sql = f"""
            SELECT cm.circle_id::text AS circle_id, sc.name AS circle_name,
                   cm.yield_per_lakh, cm.return_pct, cm.k, cm.lifetime_zenq
            FROM "ZENK"."zenq_v2_circle_month" cm
            JOIN "ZENK"."sponsor_circles" sc ON sc.id = cm.circle_id
            {join_sponsor}
            WHERE {where}
            ORDER BY sc.name ASC
            LIMIT 200
        """
    else:
        sql = f"""
            SELECT DISTINCT ON (cm.circle_id)
                   cm.circle_id::text AS circle_id, sc.name AS circle_name,
                   cm.yield_per_lakh, cm.return_pct, cm.k, cm.lifetime_zenq
            FROM "ZENK"."zenq_v2_circle_month" cm
            JOIN "ZENK"."sponsor_circles" sc ON sc.id = cm.circle_id
            {join_sponsor}
            WHERE {where}
            ORDER BY cm.circle_id, cm.month DESC
            LIMIT 200
        """
    rows = (await db.execute(text(sql), binds)).mappings().all()
    out: list[dict[str, Any]] = []
    for r in rows:
        out.append(
            {
                "circle_id": r["circle_id"],
                "circle_name": r["circle_name"],
                "yield": float(r["yield_per_lakh"] or 0),
                "avg_return": float(r["return_pct"] or 0),
                "K": float(r["k"] or 1.0),
                "eligible": True,
                "lifetime": float(r["lifetime_zenq"] or 0),
            }
        )
    return out


async def csr_allocation_run(
    db: AsyncSession,
    *,
    budget_inr: float,
    notes: Optional[str] = None,
    sponsor_id: Optional[str] = None,
    weights: Optional[Sequence[float]] = None,
    as_of_month: Optional[date] = None,
    force: bool = False,
) -> dict[str, Any]:
    params = await load_params(db)
    flags = params.get("flags") or {}
    csr_on = bool(flags.get("csr_tool"))
    if not csr_on and not force:
        return {
            "ok": False,
            "skipped": True,
            "reason": "flags.csr_tool=false — pass force=true for dry-run verify only",
            "claim_language": funder_claim_language(),
            "csr_tool_visible": False,
        }

    w = list(weights) if weights is not None else list(DEFAULT_CSR_WEIGHTS)
    circles = await _load_eligible_circles(
        db, sponsor_id=sponsor_id, as_of_month=as_of_month
    )
    if not circles:
        return {
            "ok": False,
            "skipped": False,
            "reason": "no closed circle months eligible for allocation",
            "claim_language": funder_claim_language(),
            "allocations": [],
            "status": "EMPTY",
        }

    shares = csr_allocation(circles, float(budget_inr), weights=w)
    yields = [float(c["yield"]) for c in circles]
    equal = equal_split_allocations(len(circles), float(budget_inr))
    expected = impact_proxy(shares, yields)
    equal_impact = impact_proxy(equal, yields)
    allocations = [
        _strip_student_keys(
            {
                "circle_id": c["circle_id"],
                "circle_name": c["circle_name"],
                "amount_inr": round(amt, 2),
                "yield_used": c["yield"],
                "k": c["K"],
                "avg_return": c["avg_return"],
            }
        )
        for c, amt in zip(circles, shares)
    ]

    run_id = str(uuid4())
    status = "DRY_RUN" if (force and not csr_on) or csr_on else "DRY_RUN"
    await db.execute(
        text(
            """
            INSERT INTO "ZENK"."zenq_v2_csr_allocation_run" (
                run_id, sponsor_id, budget, weights_json, as_of_month,
                allocations_json, expected_impact, equal_split_impact, notes, status
            ) VALUES (
                CAST(:run_id AS uuid),
                CASE WHEN :sponsor_id IS NULL THEN NULL ELSE CAST(:sponsor_id AS uuid) END,
                :budget,
                CAST(:weights_json AS jsonb),
                :as_of_month,
                CAST(:allocations_json AS jsonb),
                :expected_impact,
                :equal_split_impact,
                :notes,
                :status
            )
            """
        ),
        {
            "run_id": run_id,
            "sponsor_id": sponsor_id,
            "budget": float(budget_inr),
            "weights_json": json.dumps(w),
            "as_of_month": as_of_month,
            "allocations_json": json.dumps(allocations),
            "expected_impact": expected,
            "equal_split_impact": equal_impact,
            "notes": notes,
            "status": status,
        },
    )
    await db.commit()

    return {
        "ok": True,
        "run_id": run_id,
        "budget_inr": float(budget_inr),
        "notes": notes,
        "sponsor_id": sponsor_id,
        "weights": w,
        "as_of_month": as_of_month.isoformat() if as_of_month else None,
        "allocations": allocations,
        "expected_impact": expected,
        "equal_split_impact": equal_impact,
        "status": status,
        "forced": bool(force and not csr_on),
        "claim_language": funder_claim_language(),
        "csr_tool_visible": csr_on,
    }


async def list_csr_runs(
    db: AsyncSession, *, limit: int = 20, sponsor_id: Optional[str] = None
) -> dict[str, Any]:
    binds: dict[str, Any] = {"lim": limit}
    where = ""
    if sponsor_id:
        where = "WHERE sponsor_id = CAST(:sponsor_id AS uuid)"
        binds["sponsor_id"] = sponsor_id
    rows = (
        await db.execute(
            text(
                f"""
                SELECT run_id::text AS run_id, sponsor_id::text AS sponsor_id,
                       budget, weights_json, as_of_month, allocations_json,
                       expected_impact, equal_split_impact, notes, status, created_at
                FROM "ZENK"."zenq_v2_csr_allocation_run"
                {where}
                ORDER BY created_at DESC
                LIMIT :lim
                """
            ),
            binds,
        )
    ).mappings().all()
    items = []
    for r in rows:
        alloc = r["allocations_json"]
        if isinstance(alloc, str):
            alloc = json.loads(alloc)
        items.append(
            {
                "run_id": r["run_id"],
                "sponsor_id": r["sponsor_id"],
                "budget": float(r["budget"] or 0),
                "weights": r["weights_json"],
                "as_of_month": r["as_of_month"].isoformat() if r["as_of_month"] else None,
                "allocations": alloc or [],
                "expected_impact": r["expected_impact"],
                "equal_split_impact": r["equal_split_impact"],
                "notes": r["notes"],
                "status": r["status"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            }
        )
    return {"items": items, "claim_language": funder_claim_language()}


async def csr_status(db: AsyncSession) -> dict[str, Any]:
    params = await load_params(db)
    flags = params.get("flags") or {}
    return {
        "sponsor_yield": bool(flags.get("sponsor_yield")),
        "csr_tool": bool(flags.get("csr_tool")),
        "claim_language": funder_claim_language(),
        "product_flag": bool(settings.zenq_v2_product),
        "launch_flags_off": (
            not bool(flags.get("sponsor_yield")) and not bool(flags.get("csr_tool"))
        ),
    }
