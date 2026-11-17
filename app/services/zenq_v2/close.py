"""Monthly close — members then circles (Tech Guide §§6–8). Launch G≡1.0."""

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
from app.algorithms.zenq_v2.fade import fade_factor
from app.algorithms.zenq_v2.growth import G, growth_ratio, in_stretch, wmult
from app.algorithms.zenq_v2.params import ALGORITHM_VERSION, K_NEED, W_BASE
from app.algorithms.zenq_v2.sgi import compute_sgi
from app.algorithms.zenq_v2.zqa_map import holistic_to_assessment_row
from app.core.settings import settings
from app.services.zenq_v2.assessments import ensure_circle_profile, ingest_circle_assessments
from app.services.zenq_v2.epr import cap_partner_ip, close_partners_for_month, sum_engaged_partner_ip
from app.services.zenq_v2.weights import load_params, resolve_weights, weights_dict_from_row

logger = logging.getLogger(__name__)


def mean_first_two_baseline(composites: list[float]) -> Optional[float]:
    if len(composites) < 2:
        return None
    return (float(composites[0]) + float(composites[1])) / 2.0


def _next_month_start(month: date) -> date:
    if month.month == 12:
        return date(month.year + 1, 1, 1)
    return date(month.year, month.month + 1, 1)


def weighted_member_ip(pts: dict[str, float], weights: dict[str, float]) -> float:
    """Tech Guide close_members weighted sum (spark unweighted)."""
    w = weights or dict(W_BASE)
    total = 0.0
    for key in ("presence", "learning", "chat", "kia", "funding", "growth"):
        total += float(pts.get(key, 0)) * wmult(w, key)
    total += float(pts.get("spark", 0))
    return total


def assert_only_up(prev_lifetime: float, earnings: float, new_lifetime: float) -> bool:
    """T2 invariant: earnings >= 0 and lifetime never falls."""
    if earnings < 0:
        return False
    if new_lifetime + 1e-9 < prev_lifetime:
        return False
    if abs(new_lifetime - (prev_lifetime + max(0.0, earnings))) > 1e-6:
        return False
    return True


async def close_month(
    db: AsyncSession,
    month: date,
    *,
    circle_ids: Optional[list[str]] = None,
    admin_trigger: bool = False,
) -> dict[str, Any]:
    """Orchestrator: resolve_weights → close_members → close_circles."""
    if not settings.zenq_v2_close and not admin_trigger:
        return {"ok": False, "skipped": True, "reason": "ZENQ_V2_CLOSE off"}

    month = date(month.year, month.month, 1)
    params_early = await load_params(db)
    # Pilot: never freeze months — Admin Close / cron must not write closed_at.
    if bool(params_early.get("pilot_no_seal", True)):
        return {
            "ok": False,
            "skipped": True,
            "reason": "pilot_no_seal",
            "month": month.isoformat(),
            "hint": "Pilot scores from first circle/member without month seal",
        }

    # When seals re-enabled: never seal the in-progress calendar month.
    current_month = date(datetime.now(timezone.utc).year, datetime.now(timezone.utc).month, 1)
    if month >= current_month:
        return {
            "ok": False,
            "skipped": True,
            "reason": "cannot_seal_current_month",
            "month": month.isoformat(),
            "hint": "Close prior months only; current month stays open for live scoring",
        }

    weight_row = await resolve_weights(db, month)
    weights = weights_dict_from_row(weight_row)
    nu = float(weight_row.get("neutrality_scale") or 1.0)
    params = await load_params(db)

    if circle_ids:
        ids = list(circle_ids)
    else:
        rows = (
            await db.execute(
                text(
                    """
                    SELECT DISTINCT circle_id::text AS id FROM "ZENK"."zenq_v2_member_day"
                    WHERE day >= :m AND day < :nxt
                    UNION
                    SELECT DISTINCT circle_id::text AS id FROM "ZENK"."zenq_v2_member_month"
                    WHERE month = :m
                    UNION
                    SELECT circle_id::text FROM "ZENK"."zenq_v2_circle_profile"
                    """
                ),
                {"m": month, "nxt": _next_month_start(month)},
            )
        ).mappings().all()
        ids = [r["id"] for r in rows if r.get("id")]

    members_closed = await close_members(
        db, month, weights=weights, nu=nu, params=params, circle_ids=ids or None
    )

    closed = []
    skipped = []
    errors = []
    for cid in ids:
        existing = (
            await db.execute(
                text(
                    """
                    SELECT closed_at FROM "ZENK"."zenq_v2_circle_month"
                    WHERE circle_id = CAST(:c AS uuid) AND month = :m
                    """
                ),
                {"c": cid, "m": month},
            )
        ).mappings().first()
        if existing and existing["closed_at"] is not None:
            skipped.append(cid)
            continue

        try:
            await ensure_circle_profile(db, cid)
            try:
                await ingest_circle_assessments(db, cid)
            except Exception:
                logger.exception(
                    "[zenq_v2] assessment ingest failed for %s — continuing close", cid
                )
            result = await _close_one_circle(
                db, cid, month, weights=weights, nu=nu, params=params
            )
            if result.get("error"):
                errors.append(result)
            else:
                closed.append(result)
        except Exception as exc:
            logger.exception("[zenq_v2] close failed for circle %s", cid)
            errors.append({"circle_id": cid, "error": str(exc)})

    await db.commit()
    partners = {"ok": True, "partners_closed": 0}
    try:
        partners = await close_partners_for_month(db, month, params=params)
    except Exception as exc:
        logger.exception("[zenq_v2] close_partners failed for %s", month)
        partners = {"ok": False, "error": str(exc), "partners_closed": 0}

    recal = {"ok": True, "skipped": False}
    try:
        from app.services.zenq_v2.recalibration import generate_recalibration_proposal

        recal = await generate_recalibration_proposal(
            db,
            notes=f"Post-close recalibration log for {month.isoformat()}",
            month=month,
        )
    except Exception as exc:
        logger.exception("[zenq_v2] recalibration log failed for %s", month)
        recal = {"ok": False, "skipped": True, "reason": str(exc)}

    return {
        "ok": len(errors) == 0,
        "month": month.isoformat(),
        "weights_version_id": ALGORITHM_VERSION,
        "g_launch_unity": float(params.get("g_slope") or 0) == 0.0,
        "members_closed": members_closed,
        "closed": closed,
        "skipped_immutable": skipped,
        "errors": errors,
        "partners": partners,
        "recalibration": recal,
    }


async def close_members(
    db: AsyncSession,
    month: date,
    *,
    weights: dict[str, float],
    nu: float,
    params: dict[str, Any],
    circle_ids: Optional[list[str]] = None,
) -> int:
    """Tech Guide §7 — recompute member_month from member_day; set PCS + closed_at."""
    month = date(month.year, month.month, 1)
    nxt = _next_month_start(month)
    kia_cap = float(params.get("kia_cap_month") or 60)

    q = """
        SELECT member_id::text AS member_id, circle_id::text AS circle_id,
               COALESCE(SUM(ip_presence),0) AS presence,
               COALESCE(SUM(ip_learning),0) AS learning,
               COALESCE(SUM(ip_chat),0) AS chat,
               COALESCE(SUM(ip_kia),0) AS kia,
               COALESCE(SUM(ip_funding),0) AS funding,
               COALESCE(SUM(ip_growth),0) AS growth,
               COALESCE(SUM(ip_spark),0) AS spark,
               BOOL_OR(active) AS any_active
        FROM "ZENK"."zenq_v2_member_day"
        WHERE day >= :m AND day < :nxt
    """
    binds: dict[str, Any] = {"m": month, "nxt": nxt}
    if circle_ids:
        # Close only requested circles' members
        q += " AND circle_id = ANY(CAST(:circles AS uuid[]))"
        binds["circles"] = circle_ids
    q += " GROUP BY member_id, circle_id"

    # Prefer simpler filter without uuid[] for portability
    if circle_ids:
        rows = []
        for cid in circle_ids:
            part = (
                await db.execute(
                    text(
                        """
                        SELECT member_id::text AS member_id, circle_id::text AS circle_id,
                               COALESCE(SUM(ip_presence),0) AS presence,
                               COALESCE(SUM(ip_learning),0) AS learning,
                               COALESCE(SUM(ip_chat),0) AS chat,
                               COALESCE(SUM(ip_kia),0) AS kia,
                               COALESCE(SUM(ip_funding),0) AS funding,
                               COALESCE(SUM(ip_growth),0) AS growth,
                               COALESCE(SUM(ip_spark),0) AS spark,
                               BOOL_OR(active) AS any_active
                        FROM "ZENK"."zenq_v2_member_day"
                        WHERE day >= :m AND day < :nxt AND circle_id = CAST(:c AS uuid)
                        GROUP BY member_id, circle_id
                        """
                    ),
                    {"m": month, "nxt": nxt, "c": cid},
                )
            ).mappings().all()
            rows.extend(part)
    else:
        rows = (
            await db.execute(
                text(
                    """
                    SELECT member_id::text AS member_id, circle_id::text AS circle_id,
                           COALESCE(SUM(ip_presence),0) AS presence,
                           COALESCE(SUM(ip_learning),0) AS learning,
                           COALESCE(SUM(ip_chat),0) AS chat,
                           COALESCE(SUM(ip_kia),0) AS kia,
                           COALESCE(SUM(ip_funding),0) AS funding,
                           COALESCE(SUM(ip_growth),0) AS growth,
                           COALESCE(SUM(ip_spark),0) AS spark,
                           BOOL_OR(active) AS any_active
                    FROM "ZENK"."zenq_v2_member_day"
                    WHERE day >= :m AND day < :nxt
                    GROUP BY member_id, circle_id
                    """
                ),
                {"m": month, "nxt": nxt},
            )
        ).mappings().all()

    count = 0
    for r in rows:
        # Skip if already closed
        existing = (
            await db.execute(
                text(
                    """
                    SELECT closed_at, pcs_cumulative, months_silent
                    FROM "ZENK"."zenq_v2_member_month"
                    WHERE member_id = CAST(:m AS uuid) AND circle_id = CAST(:c AS uuid) AND month = :mo
                    """
                ),
                {"m": r["member_id"], "c": r["circle_id"], "mo": month},
            )
        ).mappings().first()
        if existing and existing.get("closed_at") is not None:
            continue

        kia = min(float(r["kia"]), kia_cap)
        pts = {
            "presence": float(r["presence"]),
            "learning": float(r["learning"]),
            "chat": float(r["chat"]),
            "kia": kia,
            "funding": float(r["funding"]),
            "growth": float(r["growth"]),
            "spark": float(r["spark"]),
        }
        weighted = weighted_member_ip(pts, weights) * float(nu)

        prev = (
            await db.execute(
                text(
                    """
                    SELECT pcs_cumulative, months_silent
                    FROM "ZENK"."zenq_v2_member_month"
                    WHERE member_id = CAST(:m AS uuid) AND circle_id = CAST(:c AS uuid) AND month < :mo
                    ORDER BY month DESC LIMIT 1
                    """
                ),
                {"m": r["member_id"], "c": r["circle_id"], "mo": month},
            )
        ).mappings().first()
        prev_pcs = float((prev or {}).get("pcs_cumulative") or 0)
        prev_silent = int((prev or {}).get("months_silent") or 0)
        any_active = bool(r["any_active"])
        months_silent = 0 if any_active else prev_silent + 1
        fade = fade_factor(months_silent, params)
        pcs = (prev_pcs + weighted) * fade
        ip_total = sum(pts[k] for k in ("presence", "learning", "chat", "kia", "funding", "growth", "spark"))

        await db.execute(
            text(
                """
                INSERT INTO "ZENK"."zenq_v2_member_month"(
                    member_id, circle_id, month,
                    ip_presence, ip_learning, ip_chat, ip_kia, ip_funding, ip_growth, ip_spark,
                    ip_total, streak_weeks_end, fade_factor, pcs_cumulative, months_silent, closed_at
                ) VALUES (
                    CAST(:mem AS uuid), CAST(:cir AS uuid), :mo,
                    :presence, :learning, :chat, :kia, :funding, :growth, :spark,
                    :ip_total, 0, :fade, :pcs, :silent, NOW()
                )
                ON CONFLICT (member_id, circle_id, month) DO UPDATE SET
                    ip_presence = EXCLUDED.ip_presence,
                    ip_learning = EXCLUDED.ip_learning,
                    ip_chat = EXCLUDED.ip_chat,
                    ip_kia = EXCLUDED.ip_kia,
                    ip_funding = EXCLUDED.ip_funding,
                    ip_growth = EXCLUDED.ip_growth,
                    ip_spark = EXCLUDED.ip_spark,
                    ip_total = EXCLUDED.ip_total,
                    fade_factor = EXCLUDED.fade_factor,
                    pcs_cumulative = EXCLUDED.pcs_cumulative,
                    months_silent = EXCLUDED.months_silent,
                    closed_at = COALESCE("ZENK"."zenq_v2_member_month".closed_at, NOW())
                WHERE "ZENK"."zenq_v2_member_month".closed_at IS NULL
                """
            ),
            {
                "mem": r["member_id"],
                "cir": r["circle_id"],
                "mo": month,
                **pts,
                "ip_total": ip_total,
                "fade": fade,
                "pcs": pcs,
                "silent": months_silent,
            },
        )
        count += 1
    return count


async def _close_one_circle(
    db: AsyncSession,
    circle_id: str,
    month: date,
    *,
    weights: dict[str, float],
    nu: float,
    params: dict[str, Any],
) -> dict[str, Any]:
    profile = await ensure_circle_profile(db, circle_id)
    need = profile.get("need_band") or "Developing"
    bracket = (profile.get("bracket") or "B")
    if isinstance(bracket, str):
        bracket = bracket.upper()[:1] or "B"
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
        "presence": float(agg["presence"]),
        "learning": float(agg["learning"]),
        "chat": float(agg["chat"]),
        "kia": float(agg["kia"]),
        "funding": float(agg["funding"]),
    }
    growth_raw = float(agg["growth"])
    spark_ip = float(agg["spark"])
    partner_ip_raw = await sum_engaged_partner_ip(
        db, circle_id=circle_id, month=month, next_month=_next_month_start(month)
    )

    assessments = await _load_assessment_composites(db, circle_id)
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
                WHERE circle_id = CAST(:c AS uuid) AND month < :m AND closed_at IS NOT NULL
                ORDER BY month DESC LIMIT 1
                """
            ),
            {"c": circle_id, "m": month},
        )
    ).mappings().first()

    prev_gr = float(prev_cm["growth_ratio"]) if prev_cm and prev_cm.get("growth_ratio") is not None else None
    # Stretch uses prior month GR (Tech Guide close_circles)
    stretch = in_stretch(prev_gr, n, params)
    g_val = G(gr, weights, params)
    sgi, sgi_band = compute_sgi(
        baseline=baseline, latest=latest, n_assessments=n, bracket=bracket
    )
    phase = "EFFORT" if gr is None else "IMPACT"

    earnings = circle_month_earnings(
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
    earnings = max(0.0, float(earnings))

    prev_life = float((prev_cm or {}).get("lifetime_zenq") or 0)
    prev_season = float((prev_cm or {}).get("season_zenq") or 0)
    contrib = float((prev_cm or {}).get("contribution_cum") or 0)

    # Pledge contribution this month (optional — from ledger PLEDGE_PAID quality)
    try:
        pledge_sum = (
            await db.execute(
                text(
                    """
                    SELECT COALESCE(SUM((quality_json->>'pledge')::float), 0)
                    FROM "ZENK"."zenq_v2_event_ledger"
                    WHERE circle_id = CAST(:c AS uuid)
                      AND event_code = 'PLEDGE_PAID'
                      AND ts >= :m AND ts < :nxt
                    """
                ),
                {"c": circle_id, "m": month, "nxt": _next_month_start(month)},
            )
        ).scalar()
        contrib = contrib + float(pledge_sum or 0)
    except Exception:
        pass

    lifetime = prev_life + earnings
    if month.month == 1:
        season = earnings
    else:
        season = prev_season + earnings

    if not assert_only_up(prev_life, earnings, lifetime):
        return {
            "circle_id": circle_id,
            "error": "only_up_invariant_failed",
            "prev_lifetime": prev_life,
            "earnings": earnings,
            "lifetime": lifetime,
        }

    hist_rows = (
        await db.execute(
            text(
                """
                SELECT earnings FROM "ZENK"."zenq_v2_circle_month"
                WHERE circle_id = CAST(:c AS uuid) AND month < :m AND closed_at IS NOT NULL
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
    # Unweighted class sum for T8; earnings still use wmult inside circle_month_earnings
    member_ip = sum(pts.values())
    partner_ip_capped = cap_partner_ip(member_ip, partner_ip_raw, params)

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
                :ret, :contrib, :ypl, :mile, :sgi, :sgi_band, NOW()
            )
            ON CONFLICT (circle_id, month) DO UPDATE SET
                member_ip = EXCLUDED.member_ip,
                partner_ip_raw = EXCLUDED.partner_ip_raw,
                partner_ip_capped = EXCLUDED.partner_ip_capped,
                earnings = EXCLUDED.earnings,
                lifetime_zenq = EXCLUDED.lifetime_zenq,
                season_zenq = EXCLUDED.season_zenq,
                g = EXCLUDED.g,
                growth_ratio = EXCLUDED.growth_ratio,
                phase = EXCLUDED.phase,
                in_stretch = EXCLUDED.in_stretch,
                sgi = EXCLUDED.sgi,
                sgi_band = EXCLUDED.sgi_band,
                return_pct = EXCLUDED.return_pct,
                contribution_cum = EXCLUDED.contribution_cum,
                milestone = EXCLUDED.milestone,
                closed_at = COALESCE("ZENK"."zenq_v2_circle_month".closed_at, NOW())
            WHERE "ZENK"."zenq_v2_circle_month".closed_at IS NULL
            """
        ),
        {
            "c": circle_id,
            "m": month,
            "vid": ALGORITHM_VERSION,
            "member_ip": member_ip,
            "partner_raw": partner_ip_raw,
            "partner_cap": partner_ip_capped,
            "growth": growth_raw,
            "spark": spark_ip,
            "k": k,
            "g": g_val,
            "gr": gr,
            "phase": phase,
            "stretch": stretch,
            "earn": earnings,
            "life": lifetime,
            "season": season,
            "ret": ret,
            "contrib": contrib,
            "ypl": ypl,
            "mile": mile,
            "sgi": sgi,
            "sgi_band": sgi_band,
        },
    )
    return {
        "circle_id": circle_id,
        "earnings": earnings,
        "lifetime_zenq": lifetime,
        "season_zenq": season,
        "g": g_val,
        "growth_ratio": gr,
        "sgi": sgi,
        "sgi_band": sgi_band,
        "milestone": mile,
        "phase": phase,
        "in_stretch": stretch,
        "return_pct": ret,
        "tenure_months": tenure,
    }


async def _load_assessment_composites(db: AsyncSession, circle_id: str) -> list[float]:
    try:
        rows = (
            await db.execute(
                text(
                    """
                    SELECT composite FROM "ZENK"."zenq_v2_assessments"
                    WHERE circle_id = CAST(:c AS uuid)
                    ORDER BY assessed_on, id
                    """
                ),
                {"c": circle_id},
            )
        ).mappings().all()
        return [float(r["composite"]) for r in rows]
    except Exception:
        return []


def map_live_zqa_for_close(holistic_composite: float, *, is_baseline: bool = False) -> dict[str, Any]:
    return holistic_to_assessment_row(holistic_composite, is_baseline=is_baseline)
