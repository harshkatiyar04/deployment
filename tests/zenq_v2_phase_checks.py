"""ZenQ v2 Phase 1–7 pure checks (python -m tests.zenq_v2_phase_checks)."""

from __future__ import annotations

from app.algorithms.zenq_v2.circle_earnings import (
    circle_month_earnings,
    impact_return,
    milestone_name,
)
from app.algorithms.zenq_v2.growth import G
from app.algorithms.zenq_v2.params import DESIGN_PARAMS, LAUNCH_PARAMS, W_BASE
from app.algorithms.zenq_v2.upgrade_dials import UPGRADE_DIALS
from app.algorithms.zenq_v2.zqa_map import holistic_to_assessment_row
from app.services.zenq_v2.close import mean_first_two_baseline
from app.services.zenq_v2.epr import cap_partner_ip, epr_shrinkage, partner_session_ip
from app.services.zenq_v2.referrals import referral_ready
from app.services.zenq_v2.status import zenq_v2_pipeline_status


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def test_t3_launch_g_unity() -> None:
    e = circle_month_earnings(
        {"presence": 100, "learning": 50, "chat": 10, "kia": 10, "funding": 10},
        partner_ip_raw=0,
        growth_raw=0,
        spark_ip=0,
        need="Developing",
        gr=1.2,
        weights=dict(W_BASE),
        params=LAUNCH_PARAMS,
    )
    e0 = circle_month_earnings(
        {"presence": 100, "learning": 50, "chat": 10, "kia": 10, "funding": 10},
        partner_ip_raw=0,
        growth_raw=0,
        spark_ip=0,
        need="Developing",
        gr=None,
        weights=dict(W_BASE),
        params=LAUNCH_PARAMS,
    )
    _assert(abs(e - e0) < 1e-6, "T3: launch G≡1 so earnings ignore GrowthRatio")
    _assert(G(1.2, params=LAUNCH_PARAMS) == 1.0, "T3 G=1")


def test_baseline_mean_first_two() -> None:
    _assert(mean_first_two_baseline([40, 50, 60]) == 45.0, "MEAN_FIRST_TWO")
    _assert(mean_first_two_baseline([40]) is None, "need two")


def test_lifetime_milestone_and_return() -> None:
    _assert(milestone_name(0) == "Seed", "seed")
    _assert(milestone_name(5000) == "Sprout", "sprout")
    _assert(impact_return([10, 10, 10, 12], 3, LAUNCH_PARAMS) is None, "tenure < listing")
    _assert(impact_return([10, 10, 10, 12], 4, LAUNCH_PARAMS) is not None, "after 4 months")


def test_epr_partner_cap() -> None:
    _assert(partner_session_ip(10, "HOME") == 15.0, "HOME 1.5")
    _assert(cap_partner_ip(100, 50, LAUNCH_PARAMS) == 20.0, "20% cap")
    shr = epr_shrinkage(2.0, 5)
    _assert(shr["confidence_label"] == "low", "low confidence")
    _assert(1.0 < shr["shrunk"] < 2.0, "shrunk toward 1")


def test_referral_and_upgrade_track() -> None:
    _assert(not referral_ready(sessions_completed=7, first_pledge_paid=True), "need 8")
    _assert(referral_ready(sessions_completed=8, first_pledge_paid=True), "ready")
    _assert(len(UPGRADE_DIALS) == 5, "five upgrade dials")
    _assert(UPGRADE_DIALS[2]["id"] == "growth_slope", "slope upgrade order")


def test_zqa_map_and_status() -> None:
    row = holistic_to_assessment_row(72.5, is_baseline=True)
    _assert(row["composite"] == 72.5 and row["language"] == 72.5, "equal split")
    st = zenq_v2_pipeline_status()
    _assert("v2 launch pipeline:" in st["v2_launch_pipeline_label"], "admin chip text")
    _assert(isinstance(st["flags"]["ZENQ_V2_PRODUCT"], bool), "product flag present")
    # Settings Field default remains False; local soft-cutover may set env true — that is OK.
    from app.core.settings import Settings

    _assert(Settings.model_fields["zenq_v2_product"].default is False, "code default product off")


def test_design_track_g_moves() -> None:
    e_l = circle_month_earnings(
        {"presence": 100, "learning": 0, "chat": 0, "kia": 0, "funding": 0},
        0,
        0,
        0,
        "Developing",
        1.0,
        params=LAUNCH_PARAMS,
    )
    e_d = circle_month_earnings(
        {"presence": 100, "learning": 0, "chat": 0, "kia": 0, "funding": 0},
        0,
        0,
        0,
        "Developing",
        1.0,
        params=DESIGN_PARAMS,
    )
    _assert(e_d > e_l, "design track G slope multiplies earnings")


def run_all() -> None:
    test_t3_launch_g_unity()
    test_baseline_mean_first_two()
    test_lifetime_milestone_and_return()
    test_epr_partner_cap()
    test_referral_and_upgrade_track()
    test_zqa_map_and_status()
    test_design_track_g_moves()
    print("zenq_v2_phase_checks: all checks passed")


if __name__ == "__main__":
    run_all()
