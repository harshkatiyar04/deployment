"""ZenQ v2 Phase 3 — T7 listing + T10 ladder suppress + language bans.

Run: python -m tests.zenq_v2_phase3_market_checks
"""

from __future__ import annotations

from datetime import date

from app.algorithms.zenq_v2.circle_earnings import impact_return
from app.algorithms.zenq_v2.language import (
    MARKET_LANGUAGE_BANS,
    assert_copy_clean,
    banned_phrases_in_text,
    market_language_ban_notes,
)
from app.algorithms.zenq_v2.params import LAUNCH_PARAMS
from app.services.zenq_v2.market import (
    ladder_thresholds,
    ladder_visibility,
    rank_ladder_rows,
    season_per_member_month,
    season_year_bounds,
    shortened_season_label,
)


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def test_t7_listing() -> None:
    _assert(impact_return([10, 10, 10, 12], 3, LAUNCH_PARAMS) is None, "tenure < 4")
    _assert(impact_return([10, 10, 10, 12], 4, LAUNCH_PARAMS) is not None, "tenure >= 4")
    listing = int(LAUNCH_PARAMS["listing_months"])
    _assert(listing == 4, "listing_months == 4")


def test_t10_pilot_first_circle() -> None:
    """Pilot: ladder/awards from first circle (mins=1); dark only when count is 0."""
    ladder_min, awards_min = ladder_thresholds(LAUNCH_PARAMS)
    _assert(ladder_min == 1 and awards_min == 1, "pilot mins = 1")
    dark = ladder_visibility(0, ladder_min=ladder_min, awards_min=awards_min)
    _assert(dark["ladder_visible"] is False, "ladder dark at 0")
    _assert(dark["awards_visible"] is False, "awards dark at 0")
    _assert(dark["suppressed_reason"], "reason present")
    live = ladder_visibility(1, ladder_min=ladder_min, awards_min=awards_min)
    _assert(live["ladder_visible"] is True and live["awards_visible"] is True, "visible at 1")


def test_rank_per_member_month() -> None:
    rows = [
        {"circle_id": "big", "season_zenq": 1000, "members_n": 10, "months_active_in_season": 10},
        {"circle_id": "small", "season_zenq": 200, "members_n": 2, "months_active_in_season": 2},
    ]
    ranked = rank_ladder_rows(rows)
    _assert(ranked[0]["circle_id"] == "small", "higher season/mm ranks first")
    _assert(ranked[0]["rank"] == 1 and ranked[1]["rank"] == 2, "ranks assigned")
    spm = season_per_member_month(200, 2, 2)
    _assert(abs(spm - 50.0) < 1e-9, "spm formula")


def test_season_reset_preview_fields() -> None:
    start, nxt, today = season_year_bounds(date(2026, 11, 3))
    _assert(start == date(2026, 1, 1), "season start Jan 1")
    _assert(nxt == date(2027, 1, 1), "next reset")
    _assert(shortened_season_label(date(2026, 5, 1), start) == "since May", "mid-year")
    _assert(shortened_season_label(date(2025, 6, 1), start) is None, "full season")


def test_ci_language_ban() -> None:
    notes = " ".join(market_language_ban_notes())
    assert_copy_clean(notes)
    hits = banned_phrases_in_text("This proves causal impact of sponsorship", MARKET_LANGUAGE_BANS)
    _assert("causal impact" in hits, "detects CI claim")
    try:
        assert_copy_clean("Our SROI is proven")
        raise AssertionError("should have banned SROI")
    except AssertionError as exc:
        _assert("banned" in str(exc).lower() or "SROI" in str(exc), "assert_copy_clean raises")


def main() -> None:
    test_t7_listing()
    test_t10_pilot_first_circle()
    test_rank_per_member_month()
    test_season_reset_preview_fields()
    test_ci_language_ban()
    print("zenq_v2_phase3_market_checks: OK (T7 + pilot ladder + language)")


if __name__ == "__main__":
    main()
