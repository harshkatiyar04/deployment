"""Realtime ZenQ v2 walls — live snapshots without month seal.

Every score bumps member aggregates, upserts live circle_month (closed_at NULL),
and rebuilds PCS. Admin Close / month-end seal stay off under pilot_no_seal.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.algorithms.zenq_v2.circle_earnings import (
    circle_month_earnings,
    impact_return,
    milestone_name,
    yield_per_lakh,
)
from app.algorithms.zenq_v2.growth import G, growth_ratio, in_stretch
from app.algorithms.zenq_v2.language import funder_claim_language, market_language_ban_notes
from app.algorithms.zenq_v2.params import ALGORITHM_VERSION, K_NEED, LAUNCH_PARAMS
from app.algorithms.zenq_v2.sgi import compute_sgi
from app.services.zenq_v2.assessments import ensure_circle_profile
from app.services.zenq_v2.epr import cap_partner_ip, sum_engaged_partner_ip
from app.services.zenq_v2.market import ladder_status_for_circle
from app.services.zenq_v2.weights import load_params, resolve_weights, weights_dict_from_row

logger = logging.getLogger(__name__)


def _display(ip: float, params: Optional[dict] = None) -> float:
    div = float((params or LAUNCH_PARAMS).get("display_divisor") or 1)
    return float(ip) / div if div else float(ip)


def _month_start(d: Optional[date] = None) -> date:
    today = d or datetime.now(timezone.utc).date()
    return date(today.year, today.month, 1)


def _next_month_start(month: date) -> date:
    if month.month == 12:
        return date(month.year + 1, 1, 1)
    return date(month.year, month.month + 1, 1)


async def _load_assessment_composites(db: AsyncSession, circle_id: str) -> list[float]:
    rows = (
        await db.execute(
            text(
                """
                SELECT composite FROM "ZENK"."zenq_v2_assessments"
                WHERE circle_id = CAST(:c AS uuid)
                ORDER BY assessed_on
                """
            ),
            {"c": circle_id},
        )
    ).mappings().all()
    return [float(r["composite"]) for r in rows if r.get("composite") is not None]


async def compute_live_circle_month(
    db: AsyncSession,
    circle_id: str,
    *,
    month: Optional[date] = None,
) -> dict[str, Any]:
    """Provisional circle earnings for open month (no closed_at write)."""
    month = _month_start(month)
    params = await load_params(db)
    weight_row = await resolve_weights(db, month)
    weights = weights_dict_from_row(weight_row)
    nu = float(weight_row.get("neutrality_scale") or 1.0)

    profile = await ensure_circle_profile(db, circle_id)
    need = profile.get("need_band") or "Developing"
    bracket = str(profile.get("bracket") or "B").upper()[:1] or "B"
    k = float(profile.get("k") or K_NEED.get(need, 1.0))

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
                    COALESCE(SUM(ip_growth),0) AS growth,
                    COALESCE(SUM(ip_spark),0) AS spark
                FROM "ZENK"."zenq_v2_member_month"
                WHERE circle_id = CAST(:c AS uuid) AND month = :m
                """
            ),
            {"c": circle_id, "m": month},
        )
    ).mappings().first()

    pts = {
        "presence": float(agg["presence"] or 0),
        "learning": float(agg["learning"] or 0),
        "chat": float(agg["chat"] or 0),
        "kia": float(agg["kia"] or 0),
        "funding": float(agg["funding"] or 0),
    }
    growth_raw = float(agg["growth"] or 0)
    spark_ip = float(agg["spark"] or 0)

    try:
        partner_ip_raw = await sum_engaged_partner_ip(
            db, circle_id=circle_id, month=month, next_month=_next_month_start(month)
        )
    except Exception:
        partner_ip_raw = 0.0

    assessments = await _load_assessment_composites(db, circle_id)
    from app.services.zenq_v2.close import mean_first_two_baseline

    baseline = mean_first_two_baseline(assessments)
    latest = assessments[-1] if assessments else None
    n = len(assessments)
    gr = growth_ratio(baseline, latest, n, bracket)

    prev_cm = (
        await db.execute(
            text(
                """
                SELECT lifetime_zenq, season_zenq, contribution_cum, earnings, growth_ratio
                FROM "ZENK"."zenq_v2_circle_month"
                WHERE circle_id = CAST(:c AS uuid) AND month < :m
                ORDER BY month DESC LIMIT 1
                """
            ),
            {"c": circle_id, "m": month},
        )
    ).mappings().first()

    prev_gr = (
        float(prev_cm["growth_ratio"])
        if prev_cm and prev_cm.get("growth_ratio") is not None
        else None
    )
    stretch = in_stretch(prev_gr, n, params)
    g_val = G(gr, weights, params)
    sgi, sgi_band = compute_sgi(
        baseline=baseline, latest=latest, n_assessments=n, bracket=bracket
    )
    phase = "EFFORT" if gr is None else "IMPACT"

    earnings = max(
        0.0,
        float(
            circle_month_earnings(
                pts,
                partner_ip_raw,
                growth_raw,
                spark_ip,
                need,
                gr,
                weights=weights,
                nu=nu,
                stretch=stretch,
                params=params,
            )
        ),
    )

    prev_life = float((prev_cm or {}).get("lifetime_zenq") or 0)
    prev_season = float((prev_cm or {}).get("season_zenq") or 0)
    contrib = float((prev_cm or {}).get("contribution_cum") or 0)
    try:
        pledge_sum = (
            await db.execute(
                text(
                    """
                    SELECT COALESCE(SUM((quality_json->>'pledge')::float), 0)
                    FROM "ZENK"."zenq_v2_event_ledger"
                    WHERE circle_id = CAST(:c AS uuid)
                      AND event_code = 'PLEDGE_PAID'
                      AND ts >= CAST(:m AS date)
                      AND ts < CAST(:nxt AS date)
                    """
                ),
                {"c": circle_id, "m": month, "nxt": _next_month_start(month)},
            )
        ).scalar()
        contrib = contrib + float(pledge_sum or 0)
    except Exception:
        pass

    lifetime = prev_life + earnings
    season = earnings if month.month == 1 else prev_season + earnings
    member_ip = sum(pts.values())
    partner_ip_capped = cap_partner_ip(member_ip, partner_ip_raw, params)

    hist_rows = (
        await db.execute(
            text(
                """
                SELECT earnings FROM "ZENK"."zenq_v2_circle_month"
                WHERE circle_id = CAST(:c AS uuid) AND month < :m
                ORDER BY month
                """
            ),
            {"c": circle_id, "m": month},
        )
    ).mappings().all()
    hist = [float(r["earnings"] or 0) for r in hist_rows] + [earnings]
    tenure = len(hist)
    ret = impact_return(hist, tenure, params)
    ypl = (
        yield_per_lakh(lifetime, contrib, params)
        if (params.get("flags") or {}).get("sponsor_yield")
        else None
    )
    mile = milestone_name(lifetime, params)

    if bool(params.get("pilot_no_seal", True)):
        official = False
    else:
        sealed_now = (
            await db.execute(
                text(
                    """
                    SELECT closed_at FROM "ZENK"."zenq_v2_circle_month"
                    WHERE circle_id = CAST(:c AS uuid) AND month = :m
                    """
                ),
                {"c": circle_id, "m": month},
            )
        ).scalar()
        official = sealed_now is not None

    return {
        "circle_id": circle_id,
        "month": month,
        "earnings": earnings,
        "lifetime": lifetime,
        "season_zenq": season,
        "milestone": mile,
        "g": float(g_val or 1),
        "k": k,
        "sgi": sgi,
        "sgi_band": sgi_band,
        "phase": phase,
        "in_stretch": bool(stretch),
        "return_pct": ret,
        "yield_per_lakh": ypl,
        "spark_ip": spark_ip,
        "growth_ip": growth_raw,
        "member_ip": member_ip,
        "partner_ip_raw": float(partner_ip_raw or 0),
        "partner_ip_capped": float(partner_ip_capped or 0),
        "contribution_cum": contrib,
        "growth_ratio": gr,
        "prev_earnings": float((prev_cm or {}).get("earnings") or 0) if prev_cm else None,
        "official": official,
        "live": not official,
        "params": params,
        "weights": weights,
        "weights_version_id": ALGORITHM_VERSION,
    }


async def get_circle_live(db: AsyncSession, circle_id: str) -> dict[str, Any]:
    """Dashboard payload that is always scored when any live IP or sealed history exists."""
    month = _month_start()
    live = await compute_live_circle_month(db, circle_id, month=month)
    params = live["params"]
    flags = params.get("flags") or {}

    ip_sum = (
        await db.execute(
            text(
                """
                SELECT COALESCE(SUM(ip_total),0) FROM "ZENK"."zenq_v2_member_month"
                WHERE circle_id = CAST(:c AS uuid) AND month = :m
                """
            ),
            {"c": circle_id, "m": month},
        )
    ).scalar()
    has_activity = (
        live["earnings"] > 0
        or live["lifetime"] > 0
        or live["spark_ip"] > 0
        or float(ip_sum or 0) > 0
    )

    # Always show live board (primary scores are realtime)
    scored = True
    this_earn = float(live["earnings"])
    prev_earn = live["prev_earnings"]
    change = (this_earn - prev_earn) if prev_earn is not None else None
    lifetime = float(live["lifetime"])

    from app.services.zenq_v2.dashboard import _next_milestone

    miles = _next_milestone(lifetime)

    return {
        "scored": scored,
        "live": bool(live["live"]),
        "official": bool(live["official"]),
        "circle_id": circle_id,
        "lifetime": lifetime,
        "lifetime_display": _display(lifetime, params),
        "milestone": live["milestone"],
        "milestone_next": miles,
        "claim_language": funder_claim_language(),
        "sponsor_yield_visible": bool(flags.get("sponsor_yield")),
        "csr_tool_visible": bool(flags.get("csr_tool")),
        "yield_per_lakh": (
            float(live["yield_per_lakh"])
            if flags.get("sponsor_yield") and live["yield_per_lakh"] is not None
            else None
        ),
        "season_zenq": float(live["season_zenq"]),
        "season_display": _display(float(live["season_zenq"]), params),
        "this_month": {
            "month": month.isoformat(),
            "earnings": this_earn,
            "earnings_display": _display(this_earn, params),
            "change": change,
            "g": float(live["g"] or 1),
            "sgi_band": live["sgi_band"],
            "phase": live["phase"],
            "in_stretch": bool(live["in_stretch"]),
        },
        "gain_6m": None,
        "gain_6m_display": None,
        "return_pct": live["return_pct"],
        "hours_note": "Hours come from SESSION minutes on the member wall; not substituted from ZQA.",
        "history_6m": [],
        "ladder": await ladder_status_for_circle(db, circle_id),
        "spark_words": (
            "Circle Sparks are named in words on member walls — raw Spark IP is never shown."
            if float(live["spark_ip"] or 0) > 0
            else "No Sparks recorded this month yet."
        ),
        "language_bans": market_language_ban_notes()
        + ["Do not show raw Spark IP on the member wall"],
        "has_activity": bool(has_activity),
    }


async def upsert_live_circle_month(
    db: AsyncSession,
    circle_id: str,
    *,
    month: Optional[date] = None,
) -> dict[str, Any]:
    """Persist live circle_month snapshot with closed_at always NULL (no seal)."""
    live = await compute_live_circle_month(db, circle_id, month=month)
    month = live["month"]
    await db.execute(
        text(
            """
            INSERT INTO "ZENK"."zenq_v2_circle_month"(
                circle_id, month, weights_version_id, member_ip, partner_ip_raw,
                partner_ip_capped, growth_ip, spark_ip, k, g, growth_ratio, phase,
                in_stretch, earnings, lifetime_zenq, season_zenq, return_pct,
                contribution_cum, yield_per_lakh, milestone, sgi, sgi_band, closed_at
            ) VALUES (
                CAST(:c AS uuid), :m, :vid, :member_ip, :partner_raw, :partner_cap,
                :growth, :spark, :k, :g, :gr, :phase, :stretch, :earn, :life, :season,
                :ret, :contrib, :ypl, :mile, :sgi, :sgi_band, NULL
            )
            ON CONFLICT (circle_id, month) DO UPDATE SET
                weights_version_id = EXCLUDED.weights_version_id,
                member_ip = EXCLUDED.member_ip,
                partner_ip_raw = EXCLUDED.partner_ip_raw,
                partner_ip_capped = EXCLUDED.partner_ip_capped,
                growth_ip = EXCLUDED.growth_ip,
                spark_ip = EXCLUDED.spark_ip,
                k = EXCLUDED.k,
                g = EXCLUDED.g,
                growth_ratio = EXCLUDED.growth_ratio,
                phase = EXCLUDED.phase,
                in_stretch = EXCLUDED.in_stretch,
                earnings = EXCLUDED.earnings,
                lifetime_zenq = EXCLUDED.lifetime_zenq,
                season_zenq = EXCLUDED.season_zenq,
                return_pct = EXCLUDED.return_pct,
                contribution_cum = EXCLUDED.contribution_cum,
                yield_per_lakh = EXCLUDED.yield_per_lakh,
                milestone = EXCLUDED.milestone,
                sgi = EXCLUDED.sgi,
                sgi_band = EXCLUDED.sgi_band,
                closed_at = NULL
            """
        ),
        {
            "c": circle_id,
            "m": month,
            "vid": live.get("weights_version_id") or ALGORITHM_VERSION,
            "member_ip": float(live.get("member_ip") or 0),
            "partner_raw": float(live.get("partner_ip_raw") or 0),
            "partner_cap": float(live.get("partner_ip_capped") or 0),
            "growth": float(live.get("growth_ip") or 0),
            "spark": float(live.get("spark_ip") or 0),
            "k": float(live.get("k") or 1),
            "g": float(live.get("g") or 1),
            "gr": live.get("growth_ratio"),
            "phase": live.get("phase") or "EFFORT",
            "stretch": bool(live.get("in_stretch")),
            "earn": float(live.get("earnings") or 0),
            "life": float(live.get("lifetime") or 0),
            "season": float(live.get("season_zenq") or 0),
            "ret": live.get("return_pct"),
            "contrib": float(live.get("contribution_cum") or 0),
            "ypl": live.get("yield_per_lakh"),
            "mile": live.get("milestone"),
            "sgi": live.get("sgi"),
            "sgi_band": live.get("sgi_band"),
        },
    )
    return live


async def refresh_live_scores(
    db: AsyncSession,
    *,
    circle_id: str,
    actor_id: Optional[str] = None,
) -> dict[str, Any]:
    """Rebuild PCS, upsert live circle_month, push WS (fail-soft)."""
    try:
        if actor_id:
            from app.services.zenq_v2.ledger import rebuild_pcs
            from app.services.zenq_v2.referrals import maybe_grant_due_anniversaries

            try:
                await maybe_grant_due_anniversaries(
                    db, actor_id=actor_id, circle_id=circle_id
                )
            except Exception:
                logger.debug(
                    "[zenq_v2] anniversary check skipped actor=%s", actor_id, exc_info=True
                )
            try:
                await rebuild_pcs(db, actor_id, circle_id)
            except Exception:
                logger.debug(
                    "[zenq_v2] rebuild_pcs skipped actor=%s", actor_id, exc_info=True
                )

        try:
            await upsert_live_circle_month(db, circle_id)
            await db.commit()
        except Exception:
            logger.exception(
                "[zenq_v2] upsert_live_circle_month failed circle=%s", circle_id
            )
            try:
                await db.rollback()
            except Exception:
                pass

        dash = await get_circle_live(db, circle_id)
        member_payload = None
        if actor_id:
            from app.services.zenq_v2.ledger import get_member_me

            member_payload = await get_member_me(db, actor_id, circle_id)
            member_payload["live"] = True
            member_payload["official"] = bool(dash.get("official"))

        payload = {
            "type": "zenq_live_update",
            "payload": {
                "circle_id": circle_id,
                "actor_id": actor_id,
                "dashboard": {
                    "lifetime_display": dash.get("lifetime_display"),
                    "lifetime": dash.get("lifetime"),
                    "milestone": dash.get("milestone"),
                    "this_month": dash.get("this_month"),
                    "live": dash.get("live"),
                    "official": dash.get("official"),
                    "scored": True,
                },
                "member": (
                    {
                        "pcs_display": member_payload.get("pcs_display"),
                        "pcs": member_payload.get("pcs"),
                        "scored": member_payload.get("scored"),
                        "top_3": member_payload.get("top_3"),
                        "milestone_words": member_payload.get("milestone_words"),
                    }
                    if member_payload
                    else None
                ),
            },
        }
        try:
            from app.chat.services import manager

            await manager.broadcast(circle_id, payload)
        except Exception:
            logger.debug("[zenq_v2] WS zenq_live_update skipped", exc_info=True)
        return {"ok": True, "dashboard": dash, "member": member_payload}
    except Exception:
        logger.exception("[zenq_v2] refresh_live_scores failed circle=%s", circle_id)
        return {"ok": False, "error": "refresh_failed"}


async def maybe_grant_kia_effective(
    db: AsyncSession,
    *,
    actor_id: str,
    circle_id: str,
) -> Optional[dict[str, Any]]:
    """Product EFFECTIVE: once/month when member has PRACTICE + PREP + a SESSION this month."""
    if not actor_id or not circle_id:
        return None
    params = await load_params(db)
    if not (params.get("flags") or {}).get("score_kia_effective", True):
        return None
    month = _month_start()
    nxt = _next_month_start(month)
    try:
        counts = (
            await db.execute(
                text(
                    """
                    SELECT
                      SUM(CASE WHEN event_code = 'KIA_PRACTICE' THEN 1 ELSE 0 END)::int AS practice,
                      SUM(CASE WHEN event_code = 'KIA_PREP' THEN 1 ELSE 0 END)::int AS prep,
                      SUM(CASE WHEN event_code = 'SESSION' THEN 1 ELSE 0 END)::int AS sessions,
                      SUM(CASE WHEN event_code = 'KIA_EFFECTIVE' THEN 1 ELSE 0 END)::int AS effective
                    FROM "ZENK"."zenq_v2_event_ledger"
                    WHERE actor_id = CAST(:a AS uuid)
                      AND circle_id = CAST(:c AS uuid)
                      AND ts >= CAST(:m AS date)
                      AND ts < CAST(:nxt AS date)
                    """
                ),
                {"a": actor_id, "c": circle_id, "m": month, "nxt": nxt},
            )
        ).mappings().first()
        if not counts:
            return None
        if int(counts.get("effective") or 0) > 0:
            return None
        if (
            int(counts.get("practice") or 0) < 1
            or int(counts.get("prep") or 0) < 1
            or int(counts.get("sessions") or 0) < 1
        ):
            return None
        from app.services.zenq_v2.bridge import bridge_kia

        return await bridge_kia(
            db,
            circle_id=circle_id,
            actor_user_id=actor_id,
            kia_kind="EFFECTIVE",
            idempotency_key=f"v2:kia:effective:{actor_id}:{month.isoformat()}",
        )
    except Exception:
        logger.debug("[zenq_v2] kia EFFECTIVE auto-grant skipped", exc_info=True)
        return None


async def maybe_auto_activate_referral(
    db: AsyncSession,
    *,
    actor_id: str,
    circle_id: str,
) -> Optional[dict[str, Any]]:
    """When actor has ≥8 SESSION events + circle has a PLEDGE_PAID, emit referral once."""
    if not actor_id or not circle_id:
        return None
    try:
        from app.services.zenq_v2.referrals import activate_referral, referral_ready

        sessions = (
            await db.execute(
                text(
                    """
                    SELECT COUNT(*)::int AS n
                    FROM "ZENK"."zenq_v2_event_ledger"
                    WHERE event_code = 'SESSION'
                      AND actor_id = CAST(:a AS uuid)
                      AND circle_id = CAST(:c AS uuid)
                    """
                ),
                {"a": actor_id, "c": circle_id},
            )
        ).scalar() or 0
        pledges = (
            await db.execute(
                text(
                    """
                    SELECT COUNT(*)::int AS n
                    FROM "ZENK"."zenq_v2_event_ledger"
                    WHERE event_code = 'PLEDGE_PAID'
                      AND circle_id = CAST(:c AS uuid)
                    """
                ),
                {"c": circle_id},
            )
        ).scalar() or 0
        if not referral_ready(
            sessions_completed=int(sessions), first_pledge_paid=int(pledges) > 0
        ):
            return None
        return await activate_referral(
            db,
            actor_id=actor_id,
            circle_id=circle_id,
            sessions_completed=int(sessions),
            first_pledge_paid=True,
            idempotency_key=f"v2:ref:auto:{actor_id}:{circle_id}",
        )
    except Exception:
        logger.debug("[zenq_v2] auto referral skipped", exc_info=True)
        return None
