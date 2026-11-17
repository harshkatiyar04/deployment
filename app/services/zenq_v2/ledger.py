"""Event ledger append + day/month aggregates + PCS rebuild (Tech Guide §§2–5)."""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def _as_uuid(value: Optional[str]) -> Optional[UUID]:
    if value is None or value == "":
        return None
    return UUID(str(value))

from app.algorithms.zenq_v2.fade import fade_factor
from app.algorithms.zenq_v2.language import WALL_LANGUAGE_BANS
from app.algorithms.zenq_v2.params import ALGORITHM_VERSION, LAUNCH_PARAMS
from app.algorithms.zenq_v2.scoring import credits_member_pcs, score_event
from app.core.settings import settings
from app.services.zenq_v2.weights import load_params

logger = logging.getLogger(__name__)

_CLASS_COLS = {
    "presence": "ip_presence",
    "learning": "ip_learning",
    "chat": "ip_chat",
    "kia": "ip_kia",
    "funding": "ip_funding",
    "growth": "ip_growth",
    "spark": "ip_spark",
}

_LANGUAGE_BANS = list(WALL_LANGUAGE_BANS)


def _month_start(d: date) -> date:
    return date(d.year, d.month, 1)


def _pcs_display(pcs: float, params: Optional[dict[str, Any]] = None) -> float:
    p = params or LAUNCH_PARAMS
    div = float(p.get("display_divisor") or 1)
    return float(pcs) / div if div else float(pcs)


async def _find_by_idempotency(db: AsyncSession, key: str) -> Optional[int]:
    row = (
        await db.execute(
            text(
                """
                SELECT id FROM "ZENK"."zenq_v2_event_ledger"
                WHERE quality_json->>'idempotency_key' = :k
                LIMIT 1
                """
            ),
            {"k": key},
        )
    ).scalar()
    return int(row) if row is not None else None


async def append_event(
    db: AsyncSession,
    *,
    event_code: str,
    actor_id: Optional[str],
    circle_id: str,
    quantity: float = 1.0,
    minutes: Optional[float] = None,
    quality_json: Optional[dict[str, Any]] = None,
    partner_flag: Optional[str] = None,
    session_id: Optional[str] = None,
    verified_by: Optional[str] = None,
    student_id: Optional[str] = None,
    reversal_of: Optional[int] = None,
    bracket: str = "B",
    streak_weeks: int = 0,
    ts: Optional[datetime] = None,
) -> dict[str, Any]:
    if not settings.zenq_v2_ledger:
        return {"ok": False, "skipped": True, "reason": "ZENQ_V2_LEDGER off"}

    qj = dict(quality_json or {})
    idem = qj.get("idempotency_key")
    if idem:
        existing = await _find_by_idempotency(db, str(idem))
        if existing is not None:
            return {
                "ok": True,
                "skipped": True,
                "reason": "idempotent",
                "event_id": existing,
            }

    # Phase 5: SPARK is irreversible — never reverse a SPARK ledger row
    if event_code == "REVERSAL" and reversal_of is not None:
        orig = (
            await db.execute(
                text(
                    'SELECT event_code FROM "ZENK"."zenq_v2_event_ledger" WHERE id = :id'
                ),
                {"id": reversal_of},
            )
        ).scalar()
        if orig == "SPARK":
            return {
                "ok": False,
                "skipped": True,
                "reason": "SPARK irreversible",
                "reversal_of": reversal_of,
            }

    params = await load_params(db)
    event = {
        "code": event_code,
        "minutes": minutes,
        "outcome": qj.get("outcome"),
        "pledge": qj.get("pledge"),
        "partner_flag": partner_flag,
        "class": qj.get("class"),
        "ip_final": qj.get("ip_final"),
    }
    cls, ip_final = score_event(event, bracket, streak_weeks, params)

    when = ts or datetime.now(timezone.utc)
    # Pass real UUID/None so asyncpg can type nullable uuid columns
    res = await db.execute(
        text(
            """
            INSERT INTO "ZENK"."zenq_v2_event_ledger"(
                ts, event_code, actor_id, circle_id, student_id, quantity, minutes,
                quality_json, partner_flag, session_id, verified_by, reversal_of
            ) VALUES (
                :ts, :code, :actor, :circle, :student, :qty, :minutes,
                CAST(:qj AS jsonb), :partner, :session, :verified, :rev
            )
            RETURNING id
            """
        ),
        {
            "ts": when,
            "code": event_code,
            "actor": _as_uuid(actor_id),
            "circle": _as_uuid(circle_id),
            "student": _as_uuid(student_id),
            "qty": quantity,
            "minutes": minutes,
            "qj": json.dumps(qj),
            "partner": partner_flag,
            "session": _as_uuid(session_id),
            "verified": verified_by,
            "rev": reversal_of,
        },
    )
    event_id = int(res.scalar_one())

    await db.execute(
        text(
            """
            INSERT INTO "ZENK"."zenq_v2_event_points"(
                event_id, weights_version_id, class, ip_base, bracket_weight,
                streak_mult, ip_final
            ) VALUES (
                :eid, :vid, :cls, :ip, 1.0, 1.0, :ip
            )
            """
        ),
        {"eid": event_id, "vid": ALGORITHM_VERSION, "cls": cls, "ip": ip_final},
    )

    # Always log chat/kia even when ip_final=0 (launch dials); only bump when IP moves.
    # T8: ENGAGED partner sessions never bump member_day / home PCS — circle close reads event_points.
    if actor_id and ip_final != 0 and credits_member_pcs(partner_flag) and cls != "partner":
        await _bump_aggregates(
            db,
            member_id=actor_id,
            circle_id=circle_id,
            day=when.date(),
            cls=cls,
            ip=ip_final,
            params=params,
        )
    elif actor_id and cls in ("chat", "kia") and ip_final == 0:
        # Ensure day row can mark activity for logged-but-unscored events? Launch: no —
        # unscored chat does not set active. Leave aggregates alone.
        pass

    await db.commit()

    # Realtime walls: recompute + WS push (fail-soft; never break chat/emit)
    if circle_id:
        try:
            from app.services.zenq_v2.live import (
                maybe_auto_activate_referral,
                maybe_grant_kia_effective,
                refresh_live_scores,
            )

            if event_code in ("SESSION", "PLEDGE_PAID") and actor_id:
                await maybe_auto_activate_referral(
                    db, actor_id=actor_id, circle_id=circle_id
                )
            if event_code in ("SESSION", "KIA_PRACTICE", "KIA_PREP") and actor_id:
                await maybe_grant_kia_effective(
                    db, actor_id=actor_id, circle_id=circle_id
                )
            await refresh_live_scores(db, circle_id=circle_id, actor_id=actor_id)
        except Exception:
            logger.exception(
                "[zenq_v2] live refresh after emit failed circle=%s event=%s",
                circle_id,
                event_code,
            )

    return {
        "ok": True,
        "event_id": event_id,
        "class": cls,
        "ip_final": ip_final,
        "scored": ip_final != 0,
    }


async def _bump_aggregates(
    db: AsyncSession,
    *,
    member_id: str,
    circle_id: str,
    day: date,
    cls: str,
    ip: float,
    params: dict[str, Any],
) -> None:
    col = _CLASS_COLS.get(cls)
    if not col:
        return

    month = _month_start(day)
    # Pilot: always bump (never freeze). Clear any leftover closed_at so walls stay live.
    # When pilot_no_seal is False later, prior sealed months stay immutable again.
    if bool(params.get("pilot_no_seal", True)):
        await db.execute(
            text(
                """
                UPDATE "ZENK"."zenq_v2_member_month"
                SET closed_at = NULL
                WHERE member_id = CAST(:m AS uuid) AND circle_id = CAST(:c AS uuid)
                  AND month = :mo AND closed_at IS NOT NULL
                """
            ),
            {"m": member_id, "c": circle_id, "mo": month},
        )
        await db.execute(
            text(
                """
                UPDATE "ZENK"."zenq_v2_circle_month"
                SET closed_at = NULL
                WHERE circle_id = CAST(:c AS uuid) AND month = :mo AND closed_at IS NOT NULL
                """
            ),
            {"c": circle_id, "mo": month},
        )
    else:
        current_month = _month_start(datetime.now(timezone.utc).date())
        if month < current_month:
            closed = (
                await db.execute(
                    text(
                        """
                        SELECT closed_at FROM "ZENK"."zenq_v2_member_month"
                        WHERE member_id = CAST(:m AS uuid) AND circle_id = CAST(:c AS uuid) AND month = :mo
                        """
                    ),
                    {"m": member_id, "c": circle_id, "mo": month},
                )
            ).scalar()
            if closed is not None:
                logger.info(
                    "[zenq_v2] skip aggregate bump — prior member_month sealed member=%s circle=%s month=%s",
                    member_id,
                    circle_id,
                    month,
                )
                return

    apply_ip = float(ip)
    if cls == "chat":
        cap = float(params.get("chat_cap_day") or 8)
        cur = (
            await db.execute(
                text(
                    """
                    SELECT ip_chat FROM "ZENK"."zenq_v2_member_day"
                    WHERE member_id = CAST(:m AS uuid) AND circle_id = CAST(:c AS uuid) AND day = :d
                    """
                ),
                {"m": member_id, "c": circle_id, "d": day},
            )
        ).scalar()
        already = float(cur or 0)
        room = max(0.0, cap - already)
        apply_ip = min(apply_ip, room)

    if cls == "kia":
        cap_m = float(params.get("kia_cap_month") or 60)
        cur = (
            await db.execute(
                text(
                    """
                    SELECT ip_kia FROM "ZENK"."zenq_v2_member_month"
                    WHERE member_id = CAST(:m AS uuid) AND circle_id = CAST(:c AS uuid) AND month = :mo
                    """
                ),
                {"m": member_id, "c": circle_id, "mo": month},
            )
        ).scalar()
        already = float(cur or 0)
        room = max(0.0, cap_m - already)
        apply_ip = min(apply_ip, room)

    if apply_ip == 0 and ip != 0:
        return

    active = cls in ("presence", "learning", "chat", "kia", "funding")
    await db.execute(
        text(
            f"""
            INSERT INTO "ZENK"."zenq_v2_member_day"(
                member_id, circle_id, day, {col}, active
            ) VALUES (
                CAST(:m AS uuid), CAST(:c AS uuid), :d, :ip, :active
            )
            ON CONFLICT (member_id, circle_id, day) DO UPDATE SET
                {col} = "ZENK"."zenq_v2_member_day".{col} + EXCLUDED.{col},
                active = "ZENK"."zenq_v2_member_day".active OR EXCLUDED.active
            """
        ),
        {"m": member_id, "c": circle_id, "d": day, "ip": apply_ip, "active": active},
    )

    month = _month_start(day)
    await db.execute(
        text(
            f"""
            INSERT INTO "ZENK"."zenq_v2_member_month"(
                member_id, circle_id, month, {col}, ip_total
            ) VALUES (
                CAST(:m AS uuid), CAST(:c AS uuid), :mo, :ip, :ip
            )
            ON CONFLICT (member_id, circle_id, month) DO UPDATE SET
                {col} = "ZENK"."zenq_v2_member_month".{col} + EXCLUDED.{col},
                ip_total = "ZENK"."zenq_v2_member_month".ip_total + EXCLUDED.ip_total
            """
        ),
        {"m": member_id, "c": circle_id, "mo": month, "ip": apply_ip},
    )


async def rebuild_pcs(
    db: AsyncSession,
    member_id: str,
    circle_id: str,
    *,
    months_silent: int = 0,
) -> float:
    """Sum member_month.ip_total with fade; write pcs_cumulative on latest month."""
    params = await load_params(db)
    fade = fade_factor(months_silent, params)
    rows = (
        await db.execute(
            text(
                """
                SELECT month, ip_total FROM "ZENK"."zenq_v2_member_month"
                WHERE member_id = CAST(:m AS uuid) AND circle_id = CAST(:c AS uuid)
                ORDER BY month
                """
            ),
            {"m": member_id, "c": circle_id},
        )
    ).mappings().all()
    pcs = sum(float(r["ip_total"] or 0) for r in rows) * fade
    if rows:
        last = rows[-1]["month"]
        await db.execute(
            text(
                """
                UPDATE "ZENK"."zenq_v2_member_month"
                SET pcs_cumulative = :pcs, fade_factor = :fade
                WHERE member_id = CAST(:m AS uuid) AND circle_id = CAST(:c AS uuid) AND month = :mo
                """
            ),
            {"pcs": pcs, "fade": fade, "m": member_id, "c": circle_id, "mo": last},
        )
        await db.commit()
    return pcs


def pcs_from_month_totals(totals: list[float], months_silent: int = 0) -> float:
    """Pure PCS math for unit tests (sum * fade)."""
    fade = fade_factor(months_silent, LAUNCH_PARAMS)
    return sum(float(t) for t in totals) * fade


async def get_member_me(db: AsyncSession, member_id: str, circle_id: str) -> dict[str, Any]:
    """PCS hero payload — language bans: no raw ZIQ/ZQA as ZenQ."""
    params = await load_params(db)
    row = (
        await db.execute(
            text(
                """
                SELECT * FROM "ZENK"."zenq_v2_member_month"
                WHERE member_id = CAST(:m AS uuid) AND circle_id = CAST(:c AS uuid)
                ORDER BY month DESC LIMIT 1
                """
            ),
            {"m": member_id, "c": circle_id},
        )
    ).mappings().first()
    if not row:
        return {
            "scored": False,
            "message": "not yet scored",
            "pcs": None,
            "pcs_display": None,
            "bands": None,
            "top_3": [],
            "language_bans": list(_LANGUAGE_BANS),
        }

    pcs = float(row["pcs_cumulative"] or row["ip_total"] or 0)
    # Phase 5: never surface raw spark IP in top contributors — words only
    parts = [
        ("presence", float(row["ip_presence"] or 0)),
        ("learning", float(row["ip_learning"] or 0)),
        ("chat", float(row["ip_chat"] or 0)),
        ("kia", float(row["ip_kia"] or 0)),
        ("funding", float(row["ip_funding"] or 0)),
        ("growth", float(row["ip_growth"] or 0)),
    ]
    parts.sort(key=lambda x: x[1], reverse=True)
    pcs_display = _pcs_display(pcs, params)
    from app.services.zenq_v2.referrals import (
        member_spark_referral_summary,
        milestone_words_from_pcs,
    )

    spark_ref = await member_spark_referral_summary(
        db, member_id=member_id, circle_id=circle_id
    )
    official = (
        False
        if bool(params.get("pilot_no_seal", True))
        else row.get("closed_at") is not None
    )
    return {
        "scored": True,
        "live": not official,
        "official": official,
        "pcs": pcs,
        "pcs_display": pcs_display,
        "milestone_words": milestone_words_from_pcs(pcs_display),
        "month": row["month"].isoformat() if row["month"] else None,
        "bands": {
            "presence": float(row["ip_presence"] or 0),
            "learning": float(row["ip_learning"] or 0),
            "chat": float(row["ip_chat"] or 0),
            "kia": float(row["ip_kia"] or 0),
            "funding": float(row["ip_funding"] or 0),
        },
        "top_3": [{"class": k, "label": k} for k, v in parts[:3] if v > 0],
        "fade_factor": float(row["fade_factor"] or 1),
        "spark": {
            "words": spark_ref["spark_words"],
            "this_year": spark_ref["sparks_this_year"],
            "remaining": spark_ref["spark_remaining"],
        },
        "referral": {
            "words": spark_ref["referral_words"],
            "activations": spark_ref["referral_activations"],
        },
        "language_bans": list(_LANGUAGE_BANS)
        + ["Do not show raw Spark IP on the member wall"],
    }
