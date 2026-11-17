"""Phase 7 — recalibration logged from day one; apply only ≥200 pairs + review."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.algorithms.zenq_v2.params import LAUNCH_PARAMS
from app.algorithms.zenq_v2.schedule_recalibration import (
    STATUS_APPROVED,
    STATUS_ELIGIBLE,
    STATUS_LOGGED,
    STATUS_REJECTED,
    build_proposal_payload,
    propose_equalisation,
)
from app.services.zenq_v2.weights import load_params


def _month_start(d: Optional[date] = None) -> date:
    today = d or date.today()
    return date(today.year, today.month, 1)


def _content_hash(label: str, value: Any) -> str:
    blob = json.dumps({"label": label, "value": value}, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _row_to_dict(r: Any) -> dict[str, Any]:
    def _j(v: Any) -> Any:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return v
        return v

    return {
        "id": r["id"],
        "month": r["month"].isoformat() if r["month"] else None,
        "pairs": int(r["pairs"] or 0),
        "min_pairs": int(r["min_pairs"] or 200),
        "proposed_shift": _j(r["proposed_shift_json"]) or {},
        "equalisation": _j(r["equalisation_json"]) or {},
        "evidence": _j(r["evidence_json"]) or {},
        "status": r["status"],
        "reasoning_text": r["reasoning_text"],
        "reviewed_by": r["reviewed_by"],
        "reviewed_at": r["reviewed_at"].isoformat() if r["reviewed_at"] else None,
        "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        "eligible_to_apply": r["status"] == STATUS_ELIGIBLE,
        "auto_applied": False,
        "weights_mutated": False,
    }


async def count_evidence_pairs(db: AsyncSession) -> int:
    """Sponsor–student (circle, student) pairs with ≥2 assessment composites."""
    row = (
        await db.execute(
            text(
                """
                SELECT COUNT(*)::int AS n FROM (
                    SELECT circle_id, student_id
                    FROM "ZENK"."zenq_v2_assessments"
                    WHERE student_id IS NOT NULL
                    GROUP BY circle_id, student_id
                    HAVING COUNT(*) >= 2
                ) t
                """
            )
        )
    ).mappings().first()
    return int((row or {}).get("n") or 0)


async def log_recalibration(
    db: AsyncSession,
    *,
    pairs: Optional[int] = None,
    proposed_shift: Optional[dict[str, float]] = None,
    notes: Optional[str] = None,
    month: Optional[date] = None,
    equalisation_hints: Optional[dict[str, float]] = None,
) -> dict[str, Any]:
    params = await load_params(db)
    min_pairs = int(
        params.get("recalibration_min_pairs") or LAUNCH_PARAMS["recalibration_min_pairs"]
    )
    max_shift = float(params.get("recalibration_max_shift") or 0.05)
    eq_bounds = params.get("eq_bounds") or LAUNCH_PARAMS.get("eq_bounds") or [0.8, 1.25]

    if pairs is None:
        pairs = await count_evidence_pairs(db)
    pairs = int(pairs)
    shift = dict(proposed_shift or {})
    eq = propose_equalisation(equalisation_hints, bounds=eq_bounds)
    evidence = {
        "pairs_source": "zenq_v2_assessments",
        "counted_pairs": pairs,
        "shift_provided": bool(proposed_shift),
    }
    payload = build_proposal_payload(
        pairs=pairs,
        proposed_shift=shift,
        equalisation=eq,
        min_pairs=min_pairs,
        max_shift=max_shift,
        eq_bounds=eq_bounds,
        evidence=evidence,
    )
    run_id = str(uuid4())
    m = _month_start(month)
    reason = notes or (
        f"Recalibration {payload['status']}: {pairs}/{min_pairs} evidence pairs "
        "(weights not mutated; Phase 7 audit only)."
    )
    await db.execute(
        text(
            """
            INSERT INTO "ZENK"."zenq_v2_recalibration_run"(
                id, month, pairs, min_pairs, proposed_shift_json, equalisation_json,
                evidence_json, status, reasoning_text
            ) VALUES (
                CAST(:id AS uuid), :month, :pairs, :min_pairs,
                CAST(:shift AS jsonb), CAST(:eq AS jsonb), CAST(:ev AS jsonb),
                :status, :reason
            )
            """
        ),
        {
            "id": run_id,
            "month": m,
            "pairs": pairs,
            "min_pairs": min_pairs,
            "shift": json.dumps(payload["proposed_shift"]),
            "eq": json.dumps(payload["equalisation"]),
            "ev": json.dumps(payload["evidence"]),
            "status": payload["status"],
            "reason": reason,
        },
    )
    await db.commit()
    return {
        "id": run_id,
        "month": m.isoformat(),
        **payload,
        "reasoning_text": reason,
        "applied": False,
        "weights_mutated": False,
    }


async def generate_recalibration_proposal(
    db: AsyncSession, *, notes: Optional[str] = None, month: Optional[date] = None
) -> dict[str, Any]:
    """Best-effort monthly log (used after close). Never raises to callers."""
    try:
        return await log_recalibration(db, pairs=None, proposed_shift={}, notes=notes, month=month)
    except Exception as exc:  # noqa: BLE001 — close must not fail
        return {"ok": False, "skipped": True, "reason": str(exc)}


async def review_recalibration(
    db: AsyncSession,
    run_id: str,
    *,
    reviewed_by: str,
    approve: bool,
) -> dict[str, Any]:
    row = (
        await db.execute(
            text(
                """
                SELECT id::text AS id, status, pairs, min_pairs
                FROM "ZENK"."zenq_v2_recalibration_run"
                WHERE id = CAST(:id AS uuid)
                """
            ),
            {"id": run_id},
        )
    ).mappings().first()
    if not row:
        return {"ok": False, "reason": "run not found"}
    if row["status"] != STATUS_ELIGIBLE:
        return {
            "ok": False,
            "reason": f"only ELIGIBLE runs can be reviewed (status={row['status']})",
            "id": run_id,
            "status": row["status"],
        }
    new_status = STATUS_APPROVED if approve else STATUS_REJECTED
    note = (
        "Approved — apply-eligible for the next weights version / schedule review. "
        "Does not auto-mutate live zenq_v2_weights; promote via a new version_id when ready."
        if approve
        else "Rejected — no schedule change."
    )
    await db.execute(
        text(
            """
            UPDATE "ZENK"."zenq_v2_recalibration_run"
            SET status = :st,
                reviewed_by = :by,
                reviewed_at = NOW(),
                reasoning_text = COALESCE(reasoning_text, '') || E'\n' || :note
            WHERE id = CAST(:id AS uuid)
            """
        ),
        {"st": new_status, "by": reviewed_by, "note": note, "id": run_id},
    )
    await db.commit()
    latest = await get_recalibration_by_id(db, run_id)
    return {
        "ok": True,
        "id": run_id,
        "status": new_status,
        "weights_mutated": False,
        "run": latest,
    }


async def get_recalibration_by_id(db: AsyncSession, run_id: str) -> Optional[dict[str, Any]]:
    row = (
        await db.execute(
            text(
                """
                SELECT id::text AS id, month, pairs, min_pairs, proposed_shift_json,
                       equalisation_json, evidence_json, status, reasoning_text,
                       reviewed_by, reviewed_at, created_at
                FROM "ZENK"."zenq_v2_recalibration_run"
                WHERE id = CAST(:id AS uuid)
                """
            ),
            {"id": run_id},
        )
    ).mappings().first()
    return _row_to_dict(row) if row else None


async def get_latest_recalibration(db: AsyncSession) -> dict[str, Any]:
    row = (
        await db.execute(
            text(
                """
                SELECT id::text AS id, month, pairs, min_pairs, proposed_shift_json,
                       equalisation_json, evidence_json, status, reasoning_text,
                       reviewed_by, reviewed_at, created_at
                FROM "ZENK"."zenq_v2_recalibration_run"
                ORDER BY created_at DESC
                LIMIT 1
                """
            )
        )
    ).mappings().first()
    if not row:
        pairs = await count_evidence_pairs(db)
        min_pairs = int(LAUNCH_PARAMS["recalibration_min_pairs"])
        return {
            "run": None,
            "pairs": pairs,
            "min_pairs": min_pairs,
            "status": STATUS_LOGGED if pairs < min_pairs else STATUS_ELIGIBLE,
            "message": "no recalibration runs yet",
        }
    return {"run": _row_to_dict(row)}


async def list_recalibration_runs(db: AsyncSession, *, limit: int = 20) -> dict[str, Any]:
    rows = (
        await db.execute(
            text(
                """
                SELECT id::text AS id, month, pairs, min_pairs, proposed_shift_json,
                       equalisation_json, evidence_json, status, reasoning_text,
                       reviewed_by, reviewed_at, created_at
                FROM "ZENK"."zenq_v2_recalibration_run"
                ORDER BY created_at DESC
                LIMIT :lim
                """
            ),
            {"lim": limit},
        )
    ).mappings().all()
    return {"items": [_row_to_dict(r) for r in rows]}


async def seal_prediction(
    db: AsyncSession,
    label: str,
    value: Any,
    *,
    month_6: bool = True,
) -> dict[str, Any]:
    pred_id = str(uuid4())
    h = _content_hash(label, value)
    await db.execute(
        text(
            """
            INSERT INTO "ZENK"."zenq_v2_sealed_prediction"(
                id, label, value_json, content_hash, engine, open_at_month_6
            ) VALUES (
                CAST(:id AS uuid), :label, CAST(:val AS jsonb), :hash, 'FOUNDERS', :m6
            )
            """
        ),
        {
            "id": pred_id,
            "label": label,
            "val": json.dumps(value, default=str),
            "hash": h,
            "m6": bool(month_6),
        },
    )
    await db.commit()
    return {
        "id": pred_id,
        "label": label,
        "value": value,
        "content_hash": h,
        "engine": "FOUNDERS",
        "open_at_month_6": bool(month_6),
        "sealed_at": datetime.now(timezone.utc).isoformat(),
        "source": "Foundations sealed predictions",
    }


async def list_sealed_predictions(db: AsyncSession, *, limit: int = 100) -> list[dict[str, Any]]:
    rows = (
        await db.execute(
            text(
                """
                SELECT id::text AS id, label, value_json, content_hash, engine,
                       open_at_month_6, sealed_at, opened_at
                FROM "ZENK"."zenq_v2_sealed_prediction"
                ORDER BY sealed_at DESC
                LIMIT :lim
                """
            ),
            {"lim": limit},
        )
    ).mappings().all()
    out: list[dict[str, Any]] = []
    for r in rows:
        val = r["value_json"]
        if isinstance(val, str):
            try:
                val = json.loads(val)
            except json.JSONDecodeError:
                pass
        out.append(
            {
                "id": r["id"],
                "label": r["label"],
                "value": val,
                "content_hash": r["content_hash"],
                "engine": r["engine"],
                "open_at_month_6": bool(r["open_at_month_6"]),
                "sealed_at": r["sealed_at"].isoformat() if r["sealed_at"] else None,
                "opened_at": r["opened_at"].isoformat() if r["opened_at"] else None,
                "source": "Foundations sealed predictions",
            }
        )
    return out


async def monthly_recalibration_note(db: AsyncSession) -> str:
    pairs = await count_evidence_pairs(db)
    min_pairs = int(LAUNCH_PARAMS["recalibration_min_pairs"])
    latest = await get_latest_recalibration(db)
    sealed = await list_sealed_predictions(db, limit=500)
    run = latest.get("run")
    st = run["status"] if run else ("none")
    locked = pairs < min_pairs
    return (
        f"Evidence pairs {pairs}/{min_pairs} — "
        f"{'LOGGED only (below threshold)' if locked else 'ELIGIBLE for review'}. "
        f"Latest run: {st}. Sealed Foundations predictions: {len(sealed)}. "
        "Phase 7 never auto-mutates live schedule weights."
    )


async def recalibration_status(db: AsyncSession) -> dict[str, Any]:
    pairs = await count_evidence_pairs(db)
    min_pairs = int(LAUNCH_PARAMS["recalibration_min_pairs"])
    note = await monthly_recalibration_note(db)
    latest = await get_latest_recalibration(db)
    return {
        "pairs": pairs,
        "min_pairs": min_pairs,
        "locked": pairs < min_pairs,
        "status_hint": STATUS_LOGGED if pairs < min_pairs else STATUS_ELIGIBLE,
        "max_shift": float(LAUNCH_PARAMS.get("recalibration_max_shift") or 0.05),
        "eq_bounds": LAUNCH_PARAMS.get("eq_bounds") or [0.8, 1.25],
        "monthly_note": note,
        "latest": latest.get("run"),
        "weights_auto_mutate": False,
    }
