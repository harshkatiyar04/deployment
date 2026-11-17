"""Phase 5 — referrals + Spark (≤2/year, irreversible 60 IP)."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.algorithms.zenq_v2.params import LAUNCH_PARAMS
from app.core.settings import settings
from app.services.zenq_v2.emitters import (
    emit_referral_activated,
    emit_referral_anniversary,
    emit_spark,
)

logger = logging.getLogger(__name__)

ACTIVATION_MIN_SESSIONS = 8
SPARK_CAP_PER_YEAR = 2
SPARK_IP = float(LAUNCH_PARAMS.get("spark_ip") or 60)


def referral_ready(*, sessions_completed: int, first_pledge_paid: bool) -> bool:
    return int(sessions_completed) >= ACTIVATION_MIN_SESSIONS and bool(first_pledge_paid)


def spark_remaining(sparks_this_year: int, *, cap: int = SPARK_CAP_PER_YEAR) -> int:
    return max(0, int(cap) - max(0, int(sparks_this_year)))


def spark_words(*, sparks_this_year: int, sparks_lifetime: int = 0) -> str:
    """Member-facing copy — never expose raw IP."""
    rem = spark_remaining(sparks_this_year)
    if sparks_lifetime <= 0 and sparks_this_year <= 0:
        return "No Sparks yet this year — up to two may be awarded."
    if rem <= 0:
        return "Two Sparks awarded this year — annual recognition complete."
    if sparks_this_year == 1:
        return "One Spark this year — one more may still be awarded."
    return f"{sparks_this_year} Spark(s) this year · {rem} remaining."


def referral_words(*, activations: int, anniversaries: int = 0) -> str:
    if activations <= 0:
        return "No referral activations yet (need ≥8 sessions and first pledge)."
    base = (
        f"{activations} circle(s) brought in through referral."
        if activations != 1
        else "One circle brought in through referral."
    )
    if anniversaries:
        base += f" · {anniversaries} anniversary recognition(s)."
    return base


def milestone_words_from_pcs(pcs_display: Optional[float]) -> str:
    """Personal contribution band in words (raw IP; display_divisor=1)."""
    if pcs_display is None:
        return "Contribution not yet scored"
    v = float(pcs_display)
    # Aligned with MILESTONES_IP Sprout / Grove / Canopy
    if v < 5000:
        return "Early contributor — building presence"
    if v < 25000:
        return "Steady contributor"
    if v < 75000:
        return "Strong contributor this season"
    return "Anchor contributor"


async def count_sparks_in_year(
    db: AsyncSession, *, actor_id: str, year: Optional[int] = None
) -> int:
    y = year or date.today().year
    start = date(y, 1, 1)
    end = date(y + 1, 1, 1)
    row = (
        await db.execute(
            text(
                """
                SELECT COUNT(*)::int AS n
                FROM "ZENK"."zenq_v2_event_ledger"
                WHERE event_code = 'SPARK'
                  AND actor_id = CAST(:a AS uuid)
                  AND ts >= :a0 AND ts < :a1
                """
            ),
            {"a": actor_id, "a0": start, "a1": end},
        )
    ).mappings().first()
    return int((row or {}).get("n") or 0)


async def count_referral_activations(
    db: AsyncSession, *, actor_id: str, circle_id: Optional[str] = None
) -> int:
    if circle_id:
        row = (
            await db.execute(
                text(
                    """
                    SELECT COUNT(*)::int AS n
                    FROM "ZENK"."zenq_v2_event_ledger"
                    WHERE event_code = 'REFERRAL_ACTIVATED'
                      AND actor_id = CAST(:a AS uuid)
                      AND circle_id = CAST(:c AS uuid)
                    """
                ),
                {"a": actor_id, "c": circle_id},
            )
        ).mappings().first()
    else:
        row = (
            await db.execute(
                text(
                    """
                    SELECT COUNT(*)::int AS n
                    FROM "ZENK"."zenq_v2_event_ledger"
                    WHERE event_code = 'REFERRAL_ACTIVATED'
                      AND actor_id = CAST(:a AS uuid)
                    """
                ),
                {"a": actor_id},
            )
        ).mappings().first()
    return int((row or {}).get("n") or 0)


async def count_referral_anniversaries(db: AsyncSession, *, actor_id: str) -> int:
    row = (
        await db.execute(
            text(
                """
                SELECT COUNT(*)::int AS n
                FROM "ZENK"."zenq_v2_event_ledger"
                WHERE event_code = 'REFERRAL_ANNIVERSARY'
                  AND actor_id = CAST(:a AS uuid)
                """
            ),
            {"a": actor_id},
        )
    ).mappings().first()
    return int((row or {}).get("n") or 0)


async def activate_referral(
    db: AsyncSession,
    *,
    actor_id: str,
    circle_id: str,
    sessions_completed: int,
    first_pledge_paid: bool,
    referred_circle_id: Optional[str] = None,
    idempotency_key: Optional[str] = None,
) -> dict[str, Any]:
    if not settings.zenq_v2_ledger and not settings.zenq_v2_product:
        return {"ok": False, "skipped": True, "reason": "ZENQ_V2_LEDGER off"}
    if not referral_ready(
        sessions_completed=sessions_completed, first_pledge_paid=first_pledge_paid
    ):
        return {
            "ok": False,
            "reason": f"need ≥{ACTIVATION_MIN_SESSIONS} sessions and first pledge",
            "referral_ready": False,
        }
    key = idempotency_key or (
        f"v2:ref:{actor_id}:{referred_circle_id or circle_id}"
        if referred_circle_id
        else None
    )
    result = await emit_referral_activated(
        db,
        actor_id=actor_id,
        circle_id=circle_id,
        idempotency_key=key,
        quality_json={
            "referred_circle_id": referred_circle_id,
            "link_only": True,
            "sessions_completed": sessions_completed,
        },
    )
    result["referral_ready"] = True
    result["member_copy"] = referral_words(activations=1)
    return result


async def grant_anniversary(
    db: AsyncSession,
    *,
    actor_id: str,
    circle_id: str,
    activation_event_id: Optional[int] = None,
    idempotency_key: Optional[str] = None,
) -> dict[str, Any]:
    if not settings.zenq_v2_ledger and not settings.zenq_v2_product:
        return {"ok": False, "skipped": True, "reason": "ZENQ_V2_LEDGER off"}
    key = idempotency_key or (
        f"v2:refann:{activation_event_id}" if activation_event_id else None
    )
    return await emit_referral_anniversary(
        db,
        actor_id=actor_id,
        circle_id=circle_id,
        idempotency_key=key,
        quality_json={"activation_event_id": activation_event_id},
    )


async def maybe_grant_due_anniversaries(
    db: AsyncSession,
    *,
    actor_id: str,
    circle_id: str,
) -> list[dict[str, Any]]:
    """Grant REFERRAL_ANNIVERSARY for activations ≥365 days old without a prior anniversary."""
    if not actor_id or not circle_id:
        return []
    if not settings.zenq_v2_ledger and not settings.zenq_v2_product:
        return []
    try:
        rows = (
            await db.execute(
                text(
                    """
                    SELECT e.id AS activation_event_id
                    FROM "ZENK"."zenq_v2_event_ledger" e
                    WHERE e.event_code = 'REFERRAL_ACTIVATED'
                      AND e.actor_id = CAST(:a AS uuid)
                      AND e.circle_id = CAST(:c AS uuid)
                      AND e.ts <= (NOW() AT TIME ZONE 'UTC') - INTERVAL '365 days'
                      AND NOT EXISTS (
                        SELECT 1 FROM "ZENK"."zenq_v2_event_ledger" a
                        WHERE a.event_code = 'REFERRAL_ANNIVERSARY'
                          AND a.actor_id = e.actor_id
                          AND a.circle_id = e.circle_id
                          AND COALESCE(
                            (a.quality_json->>'activation_event_id')::bigint, 0
                          ) = e.id
                      )
                    ORDER BY e.id
                    LIMIT 5
                    """
                ),
                {"a": actor_id, "c": circle_id},
            )
        ).mappings().all()
    except Exception:
        logger.debug("[zenq_v2] anniversary due lookup failed", exc_info=True)
        return []

    out: list[dict[str, Any]] = []
    for r in rows:
        eid = r.get("activation_event_id")
        try:
            out.append(
                await grant_anniversary(
                    db,
                    actor_id=actor_id,
                    circle_id=circle_id,
                    activation_event_id=int(eid) if eid is not None else None,
                )
            )
        except Exception:
            logger.debug(
                "[zenq_v2] grant_anniversary failed activation=%s", eid, exc_info=True
            )
    return out


async def grant_spark(
    db: AsyncSession,
    *,
    actor_id: str,
    circle_id: str,
    sparks_this_year: Optional[int] = None,
    spark_id: Optional[str] = None,
    reason: Optional[str] = None,
) -> dict[str, Any]:
    """
    Award SPARK (60 IP). Cap ≤2/calendar year. Irreversible — no REVERSAL of SPARK.
    Duplicate spark_id → idempotent skip.
    """
    if not settings.zenq_v2_ledger and not settings.zenq_v2_product:
        return {"ok": False, "skipped": True, "reason": "ZENQ_V2_LEDGER off"}

    counted = (
        sparks_this_year
        if sparks_this_year is not None
        else await count_sparks_in_year(db, actor_id=actor_id)
    )
    if counted >= SPARK_CAP_PER_YEAR:
        return {
            "ok": False,
            "reason": "Spark cap ≤2/year",
            "sparks_this_year": counted,
            "remaining": 0,
            "irreversible": True,
            "member_copy": spark_words(sparks_this_year=counted),
        }

    key = f"v2:spark:{spark_id}" if spark_id else None
    result = await emit_spark(
        db,
        actor_id=actor_id,
        circle_id=circle_id,
        idempotency_key=key,
        quality_json={
            "spark_id": spark_id,
            "reason": reason,
            "irreversible": True,
            "ip_display_forbidden": True,
        },
    )
    new_count = counted + (0 if result.get("skipped") else 1)
    result["irreversible"] = True
    result["sparks_this_year"] = new_count
    result["remaining"] = spark_remaining(new_count)
    result["spark_ip_internal"] = SPARK_IP
    result["member_copy"] = spark_words(sparks_this_year=new_count)
    # Never return raw IP as member-facing score
    result.pop("ip_final", None)
    return result


async def member_spark_referral_summary(
    db: AsyncSession, *, member_id: str, circle_id: str
) -> dict[str, Any]:
    sparks_y = await count_sparks_in_year(db, actor_id=member_id)
    sparks_life = (
        await db.execute(
            text(
                """
                SELECT COUNT(*)::int AS n FROM "ZENK"."zenq_v2_event_ledger"
                WHERE event_code = 'SPARK' AND actor_id = CAST(:a AS uuid)
                """
            ),
            {"a": member_id},
        )
    ).mappings().first()
    acts = await count_referral_activations(db, actor_id=member_id)
    anns = await count_referral_anniversaries(db, actor_id=member_id)
    life_n = int((sparks_life or {}).get("n") or 0)
    return {
        "sparks_this_year": sparks_y,
        "sparks_lifetime": life_n,
        "spark_remaining": spark_remaining(sparks_y),
        "spark_words": spark_words(sparks_this_year=sparks_y, sparks_lifetime=life_n),
        "referral_activations": acts,
        "referral_anniversaries": anns,
        "referral_words": referral_words(activations=acts, anniversaries=anns),
        "activation_min_sessions": ACTIVATION_MIN_SESSIONS,
        "spark_cap_per_year": SPARK_CAP_PER_YEAR,
    }


async def bridge_legacy_spark(
    db: AsyncSession,
    *,
    student_id: str,
    circle_id: str,
    spark_row_id: str,
    reason: Optional[str] = None,
    sponsor_actor_id: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """Fail-soft dual-write from 1.5.1 zenq_spark into v2 ledger."""
    if not settings.zenq_v2_ledger:
        return {"ok": False, "skipped": True, "reason": "ZENQ_V2_LEDGER off"}
    actor = sponsor_actor_id or student_id
    try:
        return await grant_spark(
            db,
            actor_id=actor,
            circle_id=circle_id,
            spark_id=str(spark_row_id),
            reason=reason,
        )
    except Exception:
        logger.exception("[zenq_v2] bridge_legacy_spark failed spark=%s", spark_row_id)
        return {"ok": False, "error": "bridge_failed"}
