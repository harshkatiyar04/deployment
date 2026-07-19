"""Member-safe ZenQ / ZIQ snapshot for Kia (bands, not raw engine decimals)."""

from __future__ import annotations

from typing import Any, Optional

from app.algorithms.zenq.score_scales import score_card


def enrich_zenq_display_for_kia(display: dict[str, Any]) -> dict[str, Any]:
    """
    Convert resolve_circle_zenq_display() into Kia-safe fields.

    Members see ZIQ as an integer + public band labels for ZEQ/ZCQ/SPD.
    Raw 4-decimal engine coefficients are NOT exposed for chat teaching.
    """
    source = display.get("zenq_source") or "unknown"
    breakdown = display.get("zenq_breakdown") or {}

    ziq: Optional[int] = None
    if breakdown.get("ziq") is not None:
        ziq = int(round(float(breakdown["ziq"])))
    elif source == "engine" and display.get("zenq_score") is not None:
        ziq = int(display["zenq_score"])

    zeq = breakdown.get("zeq_avg")
    zcq = breakdown.get("zcq")
    spd = breakdown.get("spd_avg")

    ziq_card = score_card("ziq", float(ziq)) if ziq is not None else None
    zeq_card = score_card("zeq", float(zeq)) if zeq is not None else None
    zcq_card = score_card("zcq", float(zcq)) if zcq is not None else None
    spd_card = score_card("spd", float(spd)) if spd is not None else None

    out: dict[str, Any] = {
        "zenq_source": source,
        "circle_ziq": ziq,
        "zenq_available": bool(display.get("zenq_available")),
        "legacy_zqa_avg": display.get("legacy_zqa_avg"),
        # Human teaching fields — use these in chat, never raw floats.
        "ziq_band": (ziq_card or {}).get("band"),
        "ziq_band_description": (ziq_card or {}).get("band_description"),
        "zeq_band": (zeq_card or {}).get("band"),
        "zeq_band_description": (zeq_card or {}).get("band_description"),
        "zcq_band": (zcq_card or {}).get("band"),
        "zcq_band_description": (zcq_card or {}).get("band_description"),
        "spd_band": (spd_card or {}).get("band"),
        "spd_band_description": (spd_card or {}).get("band_description"),
        "public_story": (
            "ZIQ (Circle Impact) is the headline under the ZenQ umbrella. "
            "It grows when circle effort (ZEQ), the child's context (ZCQ), and "
            "student progress from their own baseline (SPD) all move in a healthy way. "
            "Never quote internal decimal coefficients to members."
        ),
        "how_to_raise_ziq": [
            "ZEQ — Post 2–3 thoughtful, student-centred chat notes this week (not one-liners).",
            "ZEQ — Join circle discussions and help with one concrete task (order, enrollment, school update).",
            "SPD — Ask the school partner for a timely quarterly update; celebrate one subject win.",
            "SPD — Support attendance gently (check-ins when the child misses school).",
            "ZCQ — You do not 'game' context; use it to care better when need is higher.",
        ],
    }

    if source == "legacy_zqa_avg":
        out["circle_ziq"] = None
        out["ziq_band"] = None
        out["caution"] = (
            "Circle Impact engine score is not materialised yet. "
            "legacy_zqa_avg is student ZQA average only — "
            "do NOT call it ZenQ, ZIQ, or Circle Impact."
        )

    return out
