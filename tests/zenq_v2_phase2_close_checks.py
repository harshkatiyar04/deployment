"""ZenQ v2 Phase 2 checks — T2/T3/T4/T7 + close helpers.

Run: python -m tests.zenq_v2_phase2_close_checks
"""

from __future__ import annotations

from app.algorithms.zenq_v2 import DESIGN_PARAMS, LAUNCH_PARAMS
from app.algorithms.zenq_v2.circle_earnings import circle_month_earnings, impact_return
from app.algorithms.zenq_v2.growth import G, growth_ratio, in_stretch
from app.algorithms.zenq_v2.params import CONSERVATIVE_LAUNCH_PARAMS, W_BASE
from app.algorithms.zenq_v2.sgi import compute_sgi
from app.services.zenq_v2.close import assert_only_up, mean_first_two_baseline, weighted_member_ip
from app.services.zenq_v2.close_job import previous_calendar_month
from datetime import date


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def test_t2_only_up() -> None:
    _assert(assert_only_up(100.0, 10.0, 110.0), "ok path")
    _assert(not assert_only_up(100.0, -1.0, 99.0), "negative earnings")
    _assert(not assert_only_up(100.0, 10.0, 105.0), "lifetime mismatch")
    e = circle_month_earnings(
        {"presence": 10, "learning": 0, "chat": 0, "kia": 0, "funding": 0},
        0,
        0,
        0,
        "Developing",
        None,
        params=LAUNCH_PARAMS,
    )
    _assert(e >= 0, "earnings >= 0")


def test_t3_product_g_moves() -> None:
    gr = growth_ratio(50.0, 60.0, 4, "B")
    _assert(gr is not None and gr > 0, "gr positive")
    _assert(G(gr, params=LAUNCH_PARAMS) > 1.0, "product G moves with slope 0.6")
    _assert(G(gr, params=DESIGN_PARAMS) > 1.0, "design G moves")
    _assert(G(gr, params=CONSERVATIVE_LAUNCH_PARAMS) == 1.0, "conservative G≡1")


def test_t4_stretch() -> None:
    _assert(not in_stretch(None, 5, LAUNCH_PARAMS), "no prev gr")
    _assert(not in_stretch(0.4, 2, LAUNCH_PARAMS), "n too low")
    _assert(in_stretch(0.4, 3, LAUNCH_PARAMS), "stretch on")
    _assert(not in_stretch(0.6, 5, LAUNCH_PARAMS), "recovered")
    e0 = circle_month_earnings(
        {"presence": 100, "learning": 100, "chat": 0, "kia": 0, "funding": 0},
        0,
        0,
        0,
        "Developing",
        None,
        weights=dict(W_BASE),
        stretch=False,
        params=LAUNCH_PARAMS,
    )
    e1 = circle_month_earnings(
        {"presence": 100, "learning": 100, "chat": 0, "kia": 0, "funding": 0},
        0,
        0,
        0,
        "Developing",
        None,
        weights=dict(W_BASE),
        stretch=True,
        params=LAUNCH_PARAMS,
    )
    _assert(e1 > e0, "stretch premium on presence/learning")


def test_t7_listing() -> None:
    _assert(impact_return([10, 10, 10, 12], 3, LAUNCH_PARAMS) is None, "tenure < 4")
    _assert(impact_return([10, 10, 10, 12], 4, LAUNCH_PARAMS) is not None, "tenure >= 4")


def test_baseline_and_sgi_bands() -> None:
    _assert(mean_first_two_baseline([40, 50, 60]) == 45.0, "MEAN_FIRST_TWO")
    _assert(mean_first_two_baseline([40]) is None, "need two")
    sgi, band = compute_sgi(baseline=50, latest=55, n_assessments=2, bracket="B")
    _assert(sgi is None and band == "Baseline set", "baseline set")
    sgi, band = compute_sgi(baseline=50, latest=40, n_assessments=3, bracket="B")
    _assert(band == "Needs support", f"needs support got {band}")
    sgi, band = compute_sgi(baseline=50, latest=56, n_assessments=3, bracket="B")
    _assert(band in ("Steady", "Growing", "Thriving"), f"positive band {band}")


def test_weighted_pcs_and_job_helper() -> None:
    w = weighted_member_ip({"presence": 30, "learning": 0, "chat": 0, "kia": 0, "funding": 0, "growth": 0}, dict(W_BASE))
    _assert(abs(w - 30.0) < 1e-9, f"baseline weight identity {w}")
    m = previous_calendar_month(date(2026, 11, 3))
    _assert(m == date(2026, 10, 1), f"prev month {m}")


def run_all() -> None:
    test_t2_only_up()
    test_t3_product_g_moves()
    test_t4_stretch()
    test_t7_listing()
    test_baseline_and_sgi_bands()
    test_weighted_pcs_and_job_helper()
    print("zenq_v2_phase2_close_checks: all checks passed")


if __name__ == "__main__":
    run_all()
