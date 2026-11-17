"""Member-safe ZenQ snapshot for Kia — ZenQ v2 wording (1.5.1 bands archived)."""

from __future__ import annotations

from typing import Any, Optional


def enrich_zenq_display_for_kia(display: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """v2-only teaching fields — no legacy ZIQ/ZEQ/SPD coefficient cards."""
    display = display or {}
    this_month = display.get("this_month") or {}
    member = display.get("member") or {}

    lifetime_display = display.get("lifetime_display")
    if lifetime_display is None and display.get("lifetime") is not None:
        lifetime_display = display.get("lifetime")

    this_month_display = this_month.get("earnings_display")
    if this_month_display is None and this_month.get("earnings") is not None:
        this_month_display = this_month.get("earnings")

    pcs_display = member.get("pcs_display")
    if pcs_display is None and member.get("pcs") is not None:
        pcs_display = member.get("pcs")

    return {
        "zenq_source": "zenq_v2",
        # Explicitly null — Kia must not invent legacy cards
        "circle_ziq": None,
        "ziq_band": None,
        "zeq_band": None,
        "zcq_band": None,
        "spd_band": None,
        "legacy_zqa_avg": None,
        "zenq_available": bool(display.get("scored")),
        "lifetime_display": lifetime_display,
        "this_month_display": this_month_display,
        "pcs_display": pcs_display,
        "milestone": display.get("milestone"),
        "sgi_band": this_month.get("sgi_band") or display.get("sgi_band"),
        "return_pct": display.get("return_pct"),
        "yield_per_lakh": display.get("yield_per_lakh"),
        "public_story": (
            "Circle impact is ZenQ: lifetime, this month's earnings, and milestones "
            "from scored activity. Your contribution is PCS. Student ZQA/SGI is separate. "
            "Legacy SPD no longer multiplies circle ZenQ."
        ),
        "how_to_raise_zenq": [
            "Complete verified sessions and learning targets with the student.",
            "Keep encouraging chat substantive (not one-liners).",
            "Support Sparks and referrals when the circle is ready; keep pledges current.",
        ],
        # Alias for older prompt paths that still read this key
        "how_to_raise_ziq": [
            "Complete verified sessions and learning targets with the student.",
            "Keep encouraging chat substantive (not one-liners).",
            "Support Sparks and referrals when the circle is ready; keep pledges current.",
        ],
    }
