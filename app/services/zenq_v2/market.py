"""Phase 3 — market layer. Pilot: ranks from first live circle (mins=1, no seal)."""

from __future__ import annotations

from datetime import date
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.algorithms.zenq_v2.language import market_language_ban_notes
from app.algorithms.zenq_v2.params import LAUNCH_PARAMS
from app.services.zenq_v2.weights import load_params


def ladder_thresholds(params: Optional[dict[str, Any]] = None) -> tuple[int, int]:
    p = params or LAUNCH_PARAMS
    return (
        int(p.get("ladder_min_circles") or 5),
        int(p.get("awards_min_circles") or 5),
    )


def ladder_visibility(eligible_count: int, *, ladder_min: int, awards_min: int) -> dict[str, Any]:
    """T10 pure helper — suppress ladder/awards when bracket below mins."""
    ladder_visible = eligible_count >= ladder_min
    awards_visible = eligible_count >= awards_min
    return {
        "eligible_count": eligible_count,
        "ladder_min": ladder_min,
        "awards_min": awards_min,
        "ladder_visible": ladder_visible,
        "awards_visible": awards_visible,
        "suppressed_reason": (
            None
            if ladder_visible
            else f"bracket has {eligible_count} < {ladder_min} circles"
        ),
    }


def season_per_member_month(
    season_zenq: float, members_n: int, months_active_in_season: int
) -> float:
    denom = max(1, int(members_n)) * max(1, int(months_active_in_season))
    return float(season_zenq or 0) / float(denom)


async def _attach_circle_names(
    db: AsyncSession, rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Fill circle_name from sponsor_circles (ladder SQL only selects circle_id)."""
    ids = [str(r.get("circle_id") or "") for r in rows if r.get("circle_id")]
    if not ids:
        return rows
    name_rows = (
        await db.execute(
            text(
                """
                SELECT id::text AS circle_id, name
                FROM "ZENK"."sponsor_circles"
                WHERE id::text = ANY(:ids)
                """
            ),
            {"ids": ids},
        )
    ).mappings().all()
    by_id = {str(r["circle_id"]): (r["name"] or "").strip() for r in name_rows}
    for r in rows:
        cid = str(r.get("circle_id") or "")
        r["circle_name"] = by_id.get(cid) or cid
    return rows


def rank_ladder_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Tech Guide: rank by season / members_n / months_active_in_season DESC
    (season ZenQ per member-month).
    """
    enriched = []
    for r in rows:
        spm = season_per_member_month(
            float(r.get("season_zenq") or 0),
            int(r.get("members_n") or 1),
            int(r.get("months_active_in_season") or 1),
        )
        item = {
            **r,
            "season_per_member_month": spm,
            "on_ladder": True,
            "welfare_hold": bool(r.get("welfare_hold")),
        }
        enriched.append(item)
    enriched.sort(key=lambda x: x["season_per_member_month"], reverse=True)
    for i, item in enumerate(enriched, start=1):
        item["rank"] = i
    return enriched


def season_year_bounds(as_of: Optional[date] = None) -> tuple[date, date, date]:
    """Return (season_start, next_reset, as_of). Season = calendar year."""
    today = as_of or date.today()
    season_start = date(today.year, 1, 1)
    next_reset = date(today.year + 1, 1, 1)
    return season_start, next_reset, today


def shortened_season_label(activated_on: Optional[date], season_start: date) -> Optional[str]:
    if activated_on is None:
        return None
    if activated_on > season_start:
        return f"since {activated_on.strftime('%b')}"
    return None


async def _open_welfare_circle_ids(db: AsyncSession) -> set[str]:
    rows = (
        await db.execute(
            text(
                """
                SELECT DISTINCT circle_id::text AS circle_id
                FROM "ZENK"."zenq_welfare_cases"
                WHERE status = 'open'
                """
            )
        )
    ).mappings().all()
    return {r["circle_id"] for r in rows if r.get("circle_id")}


async def season_ladder(
    db: AsyncSession,
    *,
    bracket: str,
    season_key: str = "current",
    params: Optional[dict[str, Any]] = None,
    as_of: Optional[date] = None,
) -> dict[str, Any]:
    if params is None:
        params = await load_params(db)
    p = params
    ladder_min, awards_min = ladder_thresholds(p)
    season_start, _, today = season_year_bounds(as_of)
    if season_key and season_key not in ("current", str(today.year)):
        # Allow "2026" style keys
        try:
            y = int(season_key)
            season_start = date(y, 1, 1)
        except ValueError:
            pass

    # Pilot: do not park circles off-ladder for open welfare cases (still flag in payload).
    welfare_ids = set() if bool(p.get("pilot_no_seal", True)) else await _open_welfare_circle_ids(db)
    welfare_flag_ids = await _open_welfare_circle_ids(db)

    # Pilot: any month row or live member_month IP counts (no closed_at gate).
    rows = (
        await db.execute(
            text(
                """
                WITH latest AS (
                    SELECT DISTINCT ON (cm.circle_id)
                        cm.circle_id,
                        cm.month,
                        cm.season_zenq,
                        cm.lifetime_zenq,
                        cm.return_pct,
                        cm.epm,
                        cm.earnings,
                        cp.activated_on
                    FROM "ZENK"."zenq_v2_circle_month" cm
                    JOIN "ZENK"."zenq_v2_circle_profile" cp ON cp.circle_id = cm.circle_id
                    WHERE cp.bracket = :b
                      AND cm.month >= :season_start
                    ORDER BY cm.circle_id, cm.month DESC
                ),
                live_mm AS (
                    SELECT
                        mm.circle_id,
                        SUM(mm.ip_total)::float AS season_zenq,
                        SUM(mm.ip_total)::float AS lifetime_zenq,
                        COUNT(DISTINCT mm.month)::int AS months_active_in_season,
                        COUNT(DISTINCT mm.member_id)::int AS members_n,
                        MAX(mm.month) AS month
                    FROM "ZENK"."zenq_v2_member_month" mm
                    JOIN "ZENK"."zenq_v2_circle_profile" cp ON cp.circle_id = mm.circle_id
                    WHERE cp.bracket = :b
                      AND mm.month >= :season_start
                      AND mm.ip_total > 0
                    GROUP BY mm.circle_id
                ),
                merged AS (
                    SELECT
                        COALESCE(l.circle_id, lm.circle_id) AS circle_id,
                        COALESCE(l.month, lm.month) AS month,
                        GREATEST(
                            COALESCE(l.season_zenq, 0),
                            COALESCE(lm.season_zenq, 0)
                        ) AS season_zenq,
                        GREATEST(
                            COALESCE(l.lifetime_zenq, 0),
                            COALESCE(lm.lifetime_zenq, 0)
                        ) AS lifetime_zenq,
                        l.return_pct,
                        l.epm,
                        l.earnings,
                        l.activated_on,
                        COALESCE(
                            (SELECT COUNT(DISTINCT cm2.member_id)
                             FROM "ZENK"."zenq_v2_member_month" cm2
                             WHERE cm2.circle_id = COALESCE(l.circle_id, lm.circle_id)
                               AND cm2.month = COALESCE(l.month, lm.month)),
                            lm.members_n,
                            (SELECT COUNT(*) FROM "ZENK"."circle_members" m
                             WHERE m.circle_id = COALESCE(l.circle_id, lm.circle_id)),
                            1
                        ) AS members_n,
                        COALESCE(
                            (SELECT COUNT(DISTINCT h.month)
                             FROM "ZENK"."zenq_v2_member_month" h
                             WHERE h.circle_id = COALESCE(l.circle_id, lm.circle_id)
                               AND h.month >= :season_start
                               AND h.month <= COALESCE(l.month, lm.month)
                               AND h.ip_total > 0),
                            lm.months_active_in_season,
                            1
                        ) AS months_active_in_season
                    FROM latest l
                    FULL OUTER JOIN live_mm lm ON lm.circle_id = l.circle_id
                )
                SELECT
                    circle_id::text AS circle_id,
                    month,
                    season_zenq,
                    lifetime_zenq,
                    return_pct,
                    epm,
                    earnings,
                    activated_on,
                    members_n,
                    months_active_in_season
                FROM merged
                WHERE COALESCE(season_zenq, 0) > 0 OR COALESCE(lifetime_zenq, 0) > 0
                   OR COALESCE(earnings, 0) > 0
                """
            ),
            {"b": bracket, "season_start": season_start},
        )
    ).mappings().all()

    eligible: list[dict[str, Any]] = []
    held: list[dict[str, Any]] = []
    for r in rows:
        cid = r["circle_id"]
        base = {
            "circle_id": cid,
            "season_zenq": float(r["season_zenq"] or 0),
            "lifetime_zenq": float(r["lifetime_zenq"] or 0),
            "return_pct": float(r["return_pct"]) if r["return_pct"] is not None else None,
            "epm": float(r["epm"]) if r["epm"] is not None else None,
            "members_n": max(1, int(r["members_n"] or 1)),
            "months_active_in_season": max(1, int(r["months_active_in_season"] or 1)),
            "activated_on": r["activated_on"].isoformat() if r["activated_on"] else None,
            "shortened_season": shortened_season_label(r["activated_on"], season_start),
            "welfare_hold": cid in welfare_flag_ids,
        }
        if cid in welfare_ids:
            held.append({**base, "on_ladder": False, "rank": None})
        else:
            eligible.append(base)

    vis = ladder_visibility(len(eligible), ladder_min=ladder_min, awards_min=awards_min)
    ranked = rank_ladder_rows(eligible) if vis["ladder_visible"] else []
    await _attach_circle_names(db, ranked)
    await _attach_circle_names(db, held)

    awards: Optional[dict[str, Any]] = None
    if vis["awards_visible"] and ranked:
        published = [x for x in ranked if x.get("return_pct") is not None]
        if published:
            circle_of_month = max(published, key=lambda x: float(x["return_pct"]))
            awards = {
                "circle_of_month_id": circle_of_month["circle_id"],
                "return_pct": circle_of_month["return_pct"],
                "note": "Awards screen only — not shown beside lifetime on home wall",
            }

    return {
        "bracket": bracket,
        "season_key": season_key,
        "season_start": season_start.isoformat(),
        "eligible_count": len(eligible),
        "welfare_held_count": len(held),
        "ladder_visible": vis["ladder_visible"],
        "awards_visible": vis["awards_visible"],
        "items": ranked,
        "welfare_held": held,
        "awards": awards if vis["awards_visible"] else None,
        "suppressed_reason": vis["suppressed_reason"],
        "dark": not vis["ladder_visible"],
        "message": (
            None
            if vis["ladder_visible"]
            else (
                f"ladder dark — need ≥{ladder_min} scored circle(s) in this bracket "
                f"(have {len(eligible)})"
            )
        ),
        "language_bans": market_language_ban_notes(),
    }


async def season_reset_preview(
    db: AsyncSession, *, as_of: Optional[date] = None
) -> dict[str, Any]:
    season_start, next_reset, today = season_year_bounds(as_of)
    counts = (
        await db.execute(
            text(
                """
                SELECT COUNT(DISTINCT circle_id)::int AS n
                FROM "ZENK"."zenq_v2_member_month"
                WHERE month >= :s AND ip_total > 0
                """
            ),
            {"s": season_start},
        )
    ).mappings().first()
    welfare_n = len(await _open_welfare_circle_ids(db))
    return {
        "ok": True,
        "action": "season_reset",
        "as_of": today.isoformat(),
        "season_start": season_start.isoformat(),
        "next_reset": next_reset.isoformat(),
        "circles_in_season": int((counts or {}).get("n") or 0),
        "welfare_off_ladder": welfare_n,
        "lifetime_carries": True,
        "season_resets": True,
        "proration": False,
        "note": (
            "On 1 January season_zenq clocks reset; lifetime never resets. "
            "Mid-year activations play a shortened season (no proration). "
            "Circles under open welfare escalation stay off the ladder."
        ),
        "language_bans": market_language_ban_notes(),
    }


async def ladder_status_for_circle(
    db: AsyncSession, circle_id: str, params: Optional[dict[str, Any]] = None
) -> dict[str, Any]:
    """Dark-capable snippet for sponsor dashboard — no foreign lifetimes."""
    prof = (
        await db.execute(
            text(
                """
                SELECT bracket, activated_on FROM "ZENK"."zenq_v2_circle_profile"
                WHERE circle_id = CAST(:c AS uuid)
                """
            ),
            {"c": circle_id},
        )
    ).mappings().first()
    bracket = (prof or {}).get("bracket") or "B"
    ladder = await season_ladder(db, bracket=bracket, season_key="current", params=params)
    own = next((i for i in ladder.get("items") or [] if i["circle_id"] == circle_id), None)
    held = next((i for i in ladder.get("welfare_held") or [] if i["circle_id"] == circle_id), None)
    own_welfare = bool((own or {}).get("welfare_hold")) or held is not None
    season_start, next_reset, _ = season_year_bounds()
    return {
        "bracket": bracket,
        "ladder_visible": ladder["ladder_visible"],
        "dark": ladder["dark"],
        "message": ladder.get("message"),
        "suppressed_reason": ladder.get("suppressed_reason"),
        "own_rank": own["rank"] if own else None,
        "own_season_per_member_month": own["season_per_member_month"] if own else None,
        "welfare_hold": own_welfare,
        "season_start": season_start.isoformat(),
        "next_reset": next_reset.isoformat(),
        "shortened_season": shortened_season_label(
            (prof or {}).get("activated_on"), season_start
        ),
        "language_bans": market_language_ban_notes(),
    }
