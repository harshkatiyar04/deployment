"""Phase 4 — EPR + partner attribution (HOME×1.5 / ENGAGED×0.5 + 20% cap)."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.algorithms.zenq_v2.params import LAUNCH_PARAMS
from app.algorithms.zenq_v2.scoring import partner_mult

logger = logging.getLogger(__name__)


def partner_session_ip(base_ip: float, partner_flag: str | None, params: dict | None = None) -> float:
    return float(base_ip) * partner_mult(partner_flag, params or LAUNCH_PARAMS)


def cap_partner_ip(member_ip: float, partner_ip_raw: float, params: dict | None = None) -> float:
    p = params or LAUNCH_PARAMS
    return min(float(partner_ip_raw), float(p["ext_cap"]) * float(member_ip))


def epr_shrinkage(raw_epr: float, confidence_n: int, *, k: float = 20.0) -> dict[str, Any]:
    """Bayesian-ish shrink toward 1.0 until sample grows; confidence label for marketplace."""
    w = confidence_n / (confidence_n + k) if confidence_n >= 0 else 0.0
    shrunk = 1.0 + w * (float(raw_epr) - 1.0)
    label = "low" if confidence_n < 10 else ("medium" if confidence_n < 40 else "high")
    return {
        "raw": float(raw_epr),
        "shrunk": shrunk,
        "confidence_n": confidence_n,
        "confidence_label": label,
        "note": "Paid work never credits home circle member IP as HOME partner earnings.",
    }


def compute_epr(
    *,
    track: str,
    mean_growth_ratio: Optional[float],
    mean_attendance: float = 0.8,
    sparks_per_student_year: float = 0.0,
    delivered_ratio: float = 1.0,
    feedback: float = 4.0,
    responsiveness: float = 0.8,
    students_n: int = 0,
    months_active: int = 0,
) -> dict[str, Any]:
    """Tech Guide close_partners EPR (0–100) + shrinkage toward mean until evidence."""
    track_u = (track or "MENTOR").upper()
    n = max(0, int(students_n))
    if track_u == "TUTOR":
        gr = float(mean_growth_ratio) if mean_growth_ratio is not None else 1.0
        shrunk_gr = (n * gr + 3 * 1.0) / (n + 3) if n + 3 else 1.0
        outcome = 60.0 * min(shrunk_gr / 1.5, 1.0)
        rel_w = 40.0
        shrunk_outcome = shrunk_gr
    else:
        eng = 0.7 * min(float(mean_attendance) / 0.9, 1.0) + 0.3 * min(
            float(sparks_per_student_year), 1.0
        )
        shrunk_eng = (n * eng + 3 * 0.8) / (n + 3) if n + 3 else 0.8
        outcome = 40.0 * min(shrunk_eng, 1.0)
        rel_w = 60.0
        shrunk_outcome = shrunk_eng

    reliability = rel_w * (
        0.5 * float(delivered_ratio)
        + 0.35 * (float(feedback) - 1.0) / 4.0
        + 0.15 * float(responsiveness)
    )
    epr = max(0.0, min(100.0, outcome + reliability))
    shrink = epr_shrinkage(epr / 50.0 if epr else 1.0, n)  # map toward 1.0 scale helper
    # Marketplace uses 0–100 EPR; shrink confidence_label from n / months
    conf_n = n + max(0, int(months_active))
    conf = epr_shrinkage(1.0, conf_n)
    label = (
        f"New partner — {n} student(s), {months_active} months"
        if n < 3 or months_active < 6
        else f"Established — {n} students, {months_active} months"
    )
    return {
        "track": track_u,
        "epr": round(epr, 2),
        "shrunk_outcome": round(float(shrunk_outcome), 4),
        "reliability": round(float(reliability), 2),
        "confidence_n": conf_n,
        "confidence_label": conf["confidence_label"],
        "confidence_label_detail": label,
        "shrink_meta": shrink,
    }


def assert_t8_member_equals_circle(member_ip_sum: float, circle_member_ip: float, *, eps: float = 1e-6) -> bool:
    """T8: Σ member_month class IP = circle_month.member_ip (unweighted class sum)."""
    return abs(float(member_ip_sum) - float(circle_member_ip)) <= eps


async def sum_engaged_partner_ip(
    db: AsyncSession, *, circle_id: str, month: date, next_month: date
) -> float:
    """ENGAGED session/target points credited to hiring circle partner pool only."""
    row = (
        await db.execute(
            text(
                """
                SELECT COALESCE(SUM(ep.ip_final), 0) AS raw
                FROM "ZENK"."zenq_v2_event_points" ep
                JOIN "ZENK"."zenq_v2_event_ledger" el ON el.id = ep.event_id
                WHERE el.circle_id = CAST(:c AS uuid)
                  AND el.partner_flag = 'ENGAGED'
                  AND el.ts >= :m AND el.ts < :nxt
                  AND el.event_code IN ('SESSION', 'TARGET')
                """
            ),
            {"c": circle_id, "m": month, "nxt": next_month},
        )
    ).mappings().first()
    return float((row or {}).get("raw") or 0)


async def ensure_partner_profile(
    db: AsyncSession,
    partner_id: str,
    *,
    track: str = "MENTOR",
    home_circle_id: Optional[str] = None,
    display_name: Optional[str] = None,
    fee_per_hour: float = 0.0,
) -> dict[str, Any]:
    from uuid import UUID

    home = UUID(str(home_circle_id)) if home_circle_id else None
    await db.execute(
        text(
            """
            INSERT INTO "ZENK"."zenq_v2_partner_profile"(
                partner_id, track, home_circle_id, display_name, fee_per_hour
            ) VALUES (
                CAST(:p AS uuid), :track, :home, :name, :fee
            )
            ON CONFLICT (partner_id) DO UPDATE SET
                track = COALESCE(EXCLUDED.track, "ZENK"."zenq_v2_partner_profile".track),
                display_name = COALESCE(EXCLUDED.display_name, "ZENK"."zenq_v2_partner_profile".display_name),
                updated_at = NOW()
            """
        ),
        {
            "p": partner_id,
            "track": (track or "MENTOR").upper(),
            "home": home,
            "name": display_name or f"Partner {str(partner_id)[:8]}",
            "fee": fee_per_hour,
        },
    )
    await db.commit()
    return {"partner_id": partner_id, "track": (track or "MENTOR").upper()}


async def close_partners_for_month(
    db: AsyncSession, month: date, *, params: Optional[dict[str, Any]] = None
) -> dict[str, Any]:
    """
    Recompute partner_month / EPR from ENGAGED ledger activity in month.
    Paid ENGAGED work never writes to the partner's home circle member_month (T8).
    """
    month = date(month.year, month.month, 1)
    if month.month == 12:
        nxt = date(month.year + 1, 1, 1)
    else:
        nxt = date(month.year, month.month + 1, 1)

    actors = (
        await db.execute(
            text(
                """
                SELECT DISTINCT el.actor_id::text AS partner_id,
                       COUNT(DISTINCT el.student_id) FILTER (WHERE el.student_id IS NOT NULL) AS students,
                       COUNT(*)::int AS sessions
                FROM "ZENK"."zenq_v2_event_ledger" el
                WHERE el.partner_flag = 'ENGAGED'
                  AND el.actor_id IS NOT NULL
                  AND el.ts >= :m AND el.ts < :nxt
                  AND el.event_code IN ('SESSION', 'TARGET')
                GROUP BY el.actor_id
                """
            ),
            {"m": month, "nxt": nxt},
        )
    ).mappings().all()

    closed = 0
    for a in actors:
        pid = a["partner_id"]
        if not pid:
            continue
        await ensure_partner_profile(db, pid, track="MENTOR")
        prof = (
            await db.execute(
                text(
                    'SELECT track, home_circle_id::text AS home FROM "ZENK"."zenq_v2_partner_profile" WHERE partner_id = CAST(:p AS uuid)'
                ),
                {"p": pid},
            )
        ).mappings().first()
        track = (prof or {}).get("track") or "MENTOR"
        students_n = int(a.get("students") or 0)
        # Mean GR from circles they served (hiring circles)
        gr_row = (
            await db.execute(
                text(
                    """
                    SELECT AVG(cm.growth_ratio) FILTER (WHERE cm.growth_ratio IS NOT NULL) AS mean_gr
                    FROM "ZENK"."zenq_v2_circle_month" cm
                    WHERE cm.month = :m AND cm.closed_at IS NOT NULL
                      AND cm.circle_id IN (
                        SELECT DISTINCT el.circle_id FROM "ZENK"."zenq_v2_event_ledger" el
                        WHERE el.actor_id = CAST(:p AS uuid)
                          AND el.partner_flag = 'ENGAGED'
                          AND el.ts >= :m AND el.ts < :nxt
                      )
                    """
                ),
                {"p": pid, "m": month, "nxt": nxt},
            )
        ).mappings().first()
        months_active_row = (
            await db.execute(
                text(
                    """
                    SELECT COUNT(DISTINCT date_trunc('month', ts))::int AS n
                    FROM "ZENK"."zenq_v2_event_ledger"
                    WHERE actor_id = CAST(:p AS uuid) AND partner_flag = 'ENGAGED'
                    """
                ),
                {"p": pid},
            )
        ).mappings().first()
        months_active = int((months_active_row or {}).get("n") or 1)
        epr = compute_epr(
            track=track,
            mean_growth_ratio=float(gr_row["mean_gr"]) if gr_row and gr_row.get("mean_gr") is not None else None,
            students_n=students_n,
            months_active=months_active,
        )
        await db.execute(
            text(
                """
                INSERT INTO "ZENK"."zenq_v2_partner_month"(
                    partner_id, month, students_served, months_active, mean_growth_ratio,
                    mean_attendance, sparks_per_student_year, delivered_ratio, feedback,
                    responsiveness, shrunk_outcome, reliability, epr, confidence_label,
                    sessions_count, closed_at
                ) VALUES (
                    CAST(:p AS uuid), :m, :students, :months_active, :mgr,
                    0.8, 0, 1.0, 4.0, 0.8, :shrunk, :rel, :epr, :conf,
                    :sessions, NOW()
                )
                ON CONFLICT (partner_id, month) DO UPDATE SET
                    students_served = EXCLUDED.students_served,
                    months_active = EXCLUDED.months_active,
                    mean_growth_ratio = EXCLUDED.mean_growth_ratio,
                    shrunk_outcome = EXCLUDED.shrunk_outcome,
                    reliability = EXCLUDED.reliability,
                    epr = EXCLUDED.epr,
                    confidence_label = EXCLUDED.confidence_label,
                    sessions_count = EXCLUDED.sessions_count,
                    closed_at = COALESCE("ZENK"."zenq_v2_partner_month".closed_at, NOW())
                WHERE "ZENK"."zenq_v2_partner_month".closed_at IS NULL
                """
            ),
            {
                "p": pid,
                "m": month,
                "students": students_n,
                "months_active": months_active,
                "mgr": gr_row.get("mean_gr") if gr_row else None,
                "shrunk": epr["shrunk_outcome"],
                "rel": epr["reliability"],
                "epr": epr["epr"],
                "conf": epr["confidence_label"],
                "sessions": int(a.get("sessions") or 0),
            },
        )
        closed += 1
    await db.commit()
    return {"ok": True, "month": month.isoformat(), "partners_closed": closed}


async def list_partners(
    db: AsyncSession,
    *,
    track: Optional[str] = None,
    sort: str = "epr",
    limit: int = 50,
) -> dict[str, Any]:
    """Marketplace list — no student identifiers (T13)."""
    track_u = track.upper() if track else None
    # Latest partner_month per partner (split WHERE to avoid asyncpg NULL type ambiguity)
    sql = """
                SELECT DISTINCT ON (pp.partner_id)
                    pp.partner_id::text AS partner_id,
                    pp.track,
                    pp.display_name,
                    pp.fee_per_hour,
                    pp.availability,
                    pm.epr,
                    pm.confidence_label,
                    pm.students_served,
                    pm.months_active,
                    pm.month
                FROM "ZENK"."zenq_v2_partner_profile" pp
                LEFT JOIN "ZENK"."zenq_v2_partner_month" pm ON pm.partner_id = pp.partner_id
                {where}
                ORDER BY pp.partner_id, pm.month DESC NULLS LAST
                """
    if track_u:
        rows = (
            await db.execute(
                text(sql.format(where="WHERE pp.track = :track")),
                {"track": track_u},
            )
        ).mappings().all()
    else:
        rows = (
            await db.execute(text(sql.format(where="")))
        ).mappings().all()

    items = [dict(r) for r in rows]
    if sort == "epr":
        items.sort(key=lambda x: float(x.get("epr") or 0), reverse=True)
    elif sort == "confidence":
        order_map = {"high": 0, "medium": 1, "low": 2}
        items.sort(
            key=lambda x: (
                order_map.get(str(x.get("confidence_label") or "low"), 9),
                -float(x.get("epr") or 0),
            )
        )
    items = items[: max(1, min(limit, 100))]
    for it in items:
        if it.get("month") and hasattr(it["month"], "isoformat"):
            it["month"] = it["month"].isoformat()
    return {
        "items": items,
        "sort": sort,
        "track": track_u,
        "note": "Education partners by EPR + confidence. No child ids. Paid ENGAGED work never credits home circle.",
    }
