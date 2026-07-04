"""Human-readable score bands and algorithm reference scales (ZenQ product + admin)."""

from __future__ import annotations

from typing import Any, Optional


ZIQ_BANDS = (
    {"min": 0, "max": 35, "label": "Emerging", "description": "Circle impact is building"},
    {"min": 35, "max": 60, "label": "Developing", "description": "Steady mentorship momentum"},
    {"min": 60, "max": 85, "label": "Strong", "description": "Consistent student-centred impact"},
    {"min": 85, "max": 9999, "label": "Exceptional", "description": "Outstanding circle outcomes"},
)

ZEQ_BANDS = (
    {"min": 0.0, "max": 0.45, "label": "Developing", "description": "Early sponsor engagement"},
    {"min": 0.45, "max": 0.70, "label": "Active", "description": "Regular meaningful contribution"},
    {"min": 0.70, "max": 1.00, "label": "Committed", "description": "Strong sustained effort"},
    {"min": 1.00, "max": 1.35, "label": "Exemplary", "description": "Top-tier mentorship presence"},
)

RAS_BANDS = (
    {"min": 0.0, "max": 0.45, "label": "Low effort", "description": "Brief or generic message"},
    {"min": 0.45, "max": 0.70, "label": "Moderate", "description": "Some relevance to the student"},
    {"min": 0.70, "max": 0.88, "label": "Strong", "description": "Thoughtful, student-centred reply"},
    {"min": 0.88, "max": 1.01, "label": "Excellent", "description": "Deep, authentic mentorship"},
)

ZCQ_BANDS = (
    {"min": 0.0, "max": 0.55, "label": "Standard context", "description": "Typical circle need profile"},
    {"min": 0.55, "max": 0.85, "label": "Elevated need", "description": "Higher support multiplier"},
    {"min": 0.85, "max": 2.0, "label": "High need", "description": "Critical student / attendance factors"},
)

SPD_BANDS = (
    {"min": 0.60, "max": 0.90, "label": "Below baseline", "description": "Student progress below start point"},
    {"min": 0.90, "max": 1.10, "label": "On track", "description": "Near expected ZQA trajectory"},
    {"min": 1.10, "max": 1.45, "label": "Accelerating", "description": "Student outpacing baseline"},
)


def _band_for(value: float, bands: tuple[dict[str, Any], ...]) -> dict[str, str]:
    for band in bands:
        if band["min"] <= value < band["max"]:
            return {"label": band["label"], "description": band["description"]}
    last = bands[-1]
    return {"label": last["label"], "description": last["description"]}


def score_card(
    metric: str,
    value: Optional[float],
    *,
    display_value: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    if value is None:
        return None
    v = float(value)
    if metric == "ziq":
        band = _band_for(v, ZIQ_BANDS)
        visual_pct = min(100, max(0, int(v)))
        shown = display_value or str(int(round(v)))
    elif metric == "zeq":
        band = _band_for(v, ZEQ_BANDS)
        visual_pct = min(100, max(0, int((v / 1.3) * 100)))
        shown = display_value or f"{v:.2f}"
    elif metric == "ras":
        band = _band_for(v, RAS_BANDS)
        visual_pct = min(100, max(0, int(v * 100)))
        shown = display_value or f"{v:.2f}"
    elif metric == "zcq":
        band = _band_for(v, ZCQ_BANDS)
        visual_pct = min(100, max(0, int((v / 1.3) * 100)))
        shown = display_value or f"{v:.2f}"
    elif metric == "spd":
        band = _band_for(v, SPD_BANDS)
        visual_pct = min(100, max(0, int(((v - 0.6) / 0.8) * 100)))
        shown = display_value or f"{v:.2f}"
    else:
        return None

    titles = {
        "ziq": "Circle Impact (ZIQ)",
        "zeq": "Your Effort (ZEQ)",
        "ras": "Message Quality (RAS)",
        "zcq": "Circle Context (ZCQ)",
        "spd": "Student Progress (SPD)",
    }
    return {
        "metric": metric,
        "title": titles.get(metric, metric.upper()),
        "value": shown,
        "raw": round(v, 4),
        "band": band["label"],
        "band_description": band["description"],
        "scale_percent": visual_pct,
    }


def algorithm_reference() -> dict[str, Any]:
    """Admin observatory — full scale legend and component glossary."""
    return {
        "master_formula": "ZIQ = 100 × ZEQ × ZCQ × SPD",
        "components": {
            "ZEQ": "Sponsor effort — time, targets, streak, communication (RAS), inspire, equity, commitment",
            "ZCQ": "Circle context — student need, attendance, group size",
            "SPD": "Student progress delta vs baseline ZQA",
            "RAS": "Per-message authenticity & mentoring value (Kia AI + platform rules, 0–1)",
        },
        "ras_scoring": {
            "method": "Kia AI and platform rules",
            "provider": "kia",
            "ai_weight": 0.62,
            "heuristic_weight": 0.38,
            "factors": [
                "Student-centred relevance",
                "Actionable mentorship",
                "Authentic tone (not spam/generic)",
                "Length & effort appropriateness",
                "Shield moderation outcome",
            ],
        },
        "scales": {
            "ziq": list(ZIQ_BANDS),
            "zeq": list(ZEQ_BANDS),
            "zcq": list(ZCQ_BANDS),
            "spd": list(SPD_BANDS),
            "ras": list(RAS_BANDS),
        },
        "zeq_weights": {
            "T": "Time quality",
            "A": "Target achievement",
            "S": "Continuity / streak",
            "Cm": "Communication (uses RAS)",
            "In": "Inspire actions",
            "E": "Effort equity",
            "C": "Commitment factor",
        },
    }
