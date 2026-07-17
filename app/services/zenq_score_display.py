"""Sponsor-facing ZenQ score cards with scales (no formula breakdown)."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.algorithms.zenq.score_scales import algorithm_reference, score_card
from app.core.settings import settings
from app.models.zenq import ZenqSponsorScore


async def load_member_zeq(
    db: AsyncSession,
    circle_id: str,
    user_id: str,
) -> Optional[float]:
    """Personal ZEQ from materialized scores (available after backfill / live events)."""
    res = await db.execute(
        select(ZenqSponsorScore.zeq).where(
            ZenqSponsorScore.circle_id == circle_id,
            ZenqSponsorScore.user_id == user_id,
        )
    )
    raw = res.scalar_one_or_none()
    if raw is None:
        return None
    return round(float(raw), 3)


def _activity_effort_card(activity: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
    """Fallback personal card from participation hours when ZEQ not materialized yet."""
    if not activity:
        return None
    hours = float(activity.get("hours_this_month") or 0)
    pct = int(activity.get("participation_pct") or 0)
    if hours <= 0 and pct <= 0:
        return {
            "title": "Your Effort (ZEQ)",
            "value": "—",
            "band": "Building",
            "band_description": "Chat, mentor sessions, and orders this month build your score.",
            "scale_percent": 0,
            "pending": True,
        }
    proxy = min(1.3, (min(hours, 24.0) / 24.0) * 0.75 + (pct / 100.0) * 0.25)
    card = score_card("zeq", proxy)
    if not card:
        return None
    return {
        **card,
        "title": "Your activity (preview)",
        "band_description": (
            f"{hours}h this month · {pct}% of circle activity. "
            "Full ZEQ updates after live scoring runs."
        ),
        "pending": True,
    }


async def build_sponsor_scoreboard(
    db: AsyncSession,
    *,
    circle_id: str,
    user_id: str,
    zenq_display: dict[str, Any],
    activity: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    Product scoreboard: values + band labels + scale position only.
    No ZEQ×ZCQ formula exposed to sponsors.
    """
    ziq_val = zenq_display.get("zenq_score")
    is_engine = zenq_display.get("zenq_source") == "engine"
    circle_card = score_card("ziq", float(ziq_val) if ziq_val is not None else None)
    if circle_card and not is_engine:
        circle_card = {
            **circle_card,
            "title": "Circle Impact (preview)",
            "band_description": "Student ZQA average — live circle impact score coming soon",
        }
    elif circle_card and is_engine:
        circle_card = {**circle_card, "title": "Circle Impact (ZIQ)"}

    my_zeq = await load_member_zeq(db, circle_id, user_id)
    my_card = score_card("zeq", my_zeq) if my_zeq is not None else None
    if my_card:
        my_card = {**my_card, "title": "Your Effort (ZEQ)"}
    else:
        my_card = _activity_effort_card(activity)

    breakdown = zenq_display.get("zenq_breakdown") or {}
    context_cards: list[dict[str, Any]] = []
    if is_engine:
        zcq_card = score_card("zcq", breakdown.get("zcq"))
        spd_card = score_card("spd", breakdown.get("spd_avg"))
        if zcq_card:
            context_cards.append({**zcq_card, "title": "Circle context (ZCQ)"})
        if spd_card:
            context_cards.append({**spd_card, "title": "Student progress (SPD)"})

    ref = algorithm_reference()
    zeq_avg = breakdown.get("zeq_avg")
    spd_avg = breakdown.get("spd_avg")
    insight = None
    if is_engine:
        ziq_num = float(ziq_val or 0) if ziq_val is not None else 0.0
        if ziq_num >= 55 and zeq_avg is not None and float(zeq_avg) < 0.4:
            insight = (
                "Circle Impact (ZIQ) reflects student progress (ZQA), not just chat this month. "
                "Your Effort score tracks your personal mentorship activity."
            )
        elif spd_avg is not None and float(spd_avg) >= 1.1 and zeq_avg is not None and float(zeq_avg) < 0.5:
            insight = (
                "Strong student progress is lifting Circle Impact (ZIQ). "
                "More regular mentorship will raise your personal Effort score."
            )
    elif zenq_display.get("zenq_source") == "legacy_zqa_avg":
        insight = (
            "Circle score is your students' average ZQA for now. "
            "Your Effort card tracks your mentorship activity this month."
        )

    return {
        "engine_active": is_engine,
        "ras_method": "kia_blended" if settings.zenq_ai_ras_enabled and settings.groq_api_key else "heuristic",
        "circle_ziq": circle_card,
        "my_zeq": my_card,
        "context_cards": context_cards,
        "change": zenq_display.get("zenq_change"),
        "insight": insight,
        "scales": ref["scales"],
    }
