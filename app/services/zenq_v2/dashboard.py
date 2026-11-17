"""P.0 circle dashboard + statement (Tech Guide / Standalone)."""

from __future__ import annotations

from datetime import date
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.algorithms.zenq_v2.params import LAUNCH_PARAMS, MILESTONE_NAMES, MILESTONES_IP


def _display(ip: float, params: Optional[dict] = None) -> float:
    div = float((params or LAUNCH_PARAMS).get("display_divisor") or 1)
    return float(ip) / div if div else float(ip)


def _next_milestone(lifetime_ip: float) -> dict[str, Any]:
    name = MILESTONE_NAMES[0]
    next_thr = MILESTONES_IP[0]
    next_name = MILESTONE_NAMES[0]
    for i, (thr, nm) in enumerate(zip(MILESTONES_IP, MILESTONE_NAMES)):
        if lifetime_ip >= thr:
            name = nm
            if i + 1 < len(MILESTONES_IP):
                next_thr = MILESTONES_IP[i + 1]
                next_name = MILESTONE_NAMES[i + 1]
            else:
                next_thr = thr
                next_name = nm
    return {
        "current": name,
        "next": next_name,
        "next_at_ip": next_thr,
        "next_at_display": _display(next_thr),
    }


async def get_circle_dashboard(db: AsyncSession, circle_id: str) -> dict[str, Any]:
    """Primary product surface = live rolling scores (no Admin Close required)."""
    from app.services.zenq_v2.live import get_circle_live

    live = await get_circle_live(db, circle_id)
    pilot = bool(LAUNCH_PARAMS.get("pilot_no_seal", True))

    # Live snapshots (closed_at NULL) are first-class under pilot_no_seal.
    hist = (
        await db.execute(
            text(
                """
                SELECT month, earnings, lifetime_zenq, return_pct, sgi_band, milestone, g,
                       phase, in_stretch
                FROM "ZENK"."zenq_v2_circle_month"
                WHERE circle_id = CAST(:c AS uuid)
                  AND (:pilot OR closed_at IS NOT NULL OR earnings > 0 OR lifetime_zenq > 0)
                ORDER BY month DESC LIMIT 6
                """
            ),
            {"c": circle_id, "pilot": pilot},
        )
    ).mappings().all()
    months = list(reversed(hist))
    lifetime = float(live.get("lifetime") or 0)
    first_life = float(months[0]["lifetime_zenq"] or 0) if months else 0
    gain_6m = lifetime - first_life if months else None

    # Include current live month when no circle_month history yet
    history_6m = [
        {
            "month": r["month"].isoformat() if r["month"] else None,
            "earnings": float(r["earnings"] or 0),
            "earnings_display": _display(float(r["earnings"] or 0)),
            "lifetime": float(r["lifetime_zenq"] or 0),
            "sgi_band": r["sgi_band"],
            "in_stretch": bool(r["in_stretch"]) if "in_stretch" in r else None,
        }
        for r in months
    ]
    if not history_6m and float(live.get("lifetime") or 0) > 0:
        tm = live.get("this_month") or {}
        history_6m = [
            {
                "month": tm.get("month") or live.get("month"),
                "earnings": float(tm.get("earnings") or live.get("lifetime") or 0),
                "earnings_display": _display(
                    float(tm.get("earnings") or live.get("lifetime") or 0)
                ),
                "lifetime": lifetime,
                "sgi_band": tm.get("sgi_band") or live.get("sgi_band"),
                "in_stretch": bool(tm.get("in_stretch")) if tm.get("in_stretch") is not None else None,
            }
        ]

    live["gain_6m"] = gain_6m
    live["gain_6m_display"] = _display(gain_6m) if gain_6m is not None else None
    live["history_6m"] = history_6m
    return live


async def get_circle_statement(
    db: AsyncSession, circle_id: str, month: Optional[date] = None
) -> dict[str, Any]:
    pilot = bool(LAUNCH_PARAMS.get("pilot_no_seal", True))
    if month is None:
        row = (
            await db.execute(
                text(
                    """
                    SELECT * FROM "ZENK"."zenq_v2_circle_month"
                    WHERE circle_id = CAST(:c AS uuid)
                      AND (:pilot OR closed_at IS NOT NULL)
                    ORDER BY month DESC LIMIT 1
                    """
                ),
                {"c": circle_id, "pilot": pilot},
            )
        ).mappings().first()
    else:
        m = date(month.year, month.month, 1)
        row = (
            await db.execute(
                text(
                    """
                    SELECT * FROM "ZENK"."zenq_v2_circle_month"
                    WHERE circle_id = CAST(:c AS uuid) AND month = :m
                    """
                ),
                {"c": circle_id, "m": m},
            )
        ).mappings().first()

    # Pilot fallback: synthesize statement from live walls when no circle_month row
    if not row:
        if not pilot:
            return {"scored": False, "message": "not yet scored", "circle_id": circle_id}
        from app.services.zenq_v2.live import get_circle_live

        live = await get_circle_live(db, circle_id)
        life = float(live.get("lifetime") or 0)
        if life <= 0 and not live.get("scored"):
            return {"scored": False, "message": "not yet scored", "circle_id": circle_id}
        tm = live.get("this_month") or {}
        earn = float(tm.get("earnings") or life)
        opening = life - earn
        return {
            "scored": True,
            "live": True,
            "official": False,
            "circle_id": circle_id,
            "month": tm.get("month") or live.get("month"),
            "opening_lifetime": opening,
            "opening_display": _display(opening),
            "closing_lifetime": life,
            "closing_display": _display(life),
            "member_ip": life,
            "partner_ip_capped": 0.0,
            "growth_ip": 0.0,
            "spark_ip": 0.0,
            "k": float(live.get("k") or 1),
            "g": float(tm.get("g") or live.get("g") or 1),
            "earnings": earn,
            "earnings_display": _display(earn),
            "lifetime_zenq": life,
            "sgi_band": tm.get("sgi_band") or live.get("sgi_band"),
            "milestone": live.get("milestone"),
            "phase": tm.get("phase") or live.get("phase"),
            "in_stretch": bool(tm.get("in_stretch")) if tm.get("in_stretch") is not None else False,
            "weights_version_id": None,
        }

    if (not pilot) and row.get("closed_at") is None:
        return {"scored": False, "message": "not yet scored", "circle_id": circle_id}

    earn = float(row["earnings"] or 0)
    life = float(row["lifetime_zenq"] or 0)
    opening = life - earn
    return {
        "scored": True,
        "live": bool(pilot) or row.get("closed_at") is None,
        "official": False if pilot else row.get("closed_at") is not None,
        "circle_id": circle_id,
        "month": row["month"].isoformat() if row["month"] else None,
        "opening_lifetime": opening,
        "opening_display": _display(opening),
        "closing_lifetime": life,
        "closing_display": _display(life),
        "member_ip": float(row["member_ip"] or 0),
        "partner_ip_capped": float(row["partner_ip_capped"] or 0),
        "growth_ip": float(row["growth_ip"] or 0),
        "spark_ip": float(row["spark_ip"] or 0),
        "k": float(row["k"] or 1),
        "g": float(row["g"] or 1),
        "earnings": earn,
        "earnings_display": _display(earn),
        "lifetime_zenq": life,
        "sgi_band": row["sgi_band"],
        "milestone": row["milestone"],
        "phase": row["phase"],
        "in_stretch": bool(row["in_stretch"]),
        "weights_version_id": row["weights_version_id"],
    }
