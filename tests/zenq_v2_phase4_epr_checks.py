"""ZenQ v2 Phase 4 — T8 partner attribution + EPR/cap helpers.

Run: python -m tests.zenq_v2_phase4_epr_checks
"""

from __future__ import annotations

from app.algorithms.zenq_v2.params import LAUNCH_PARAMS
from app.algorithms.zenq_v2.scoring import credits_member_pcs, partner_mult, score_event
from app.services.zenq_v2.epr import (
    assert_t8_member_equals_circle,
    cap_partner_ip,
    compute_epr,
    epr_shrinkage,
    partner_session_ip,
)


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def test_t8_partner_mult() -> None:
    _assert(partner_mult("HOME", LAUNCH_PARAMS) == 1.5, "HOME×1.5")
    _assert(partner_mult("ENGAGED", LAUNCH_PARAMS) == 0.5, "ENGAGED×0.5")
    _assert(partner_mult(None, LAUNCH_PARAMS) == 1.0, "plain session")
    _assert(credits_member_pcs("HOME") is True, "HOME credits PCS")
    _assert(credits_member_pcs("ENGAGED") is False, "ENGAGED never credits PCS")


def test_t8_engaged_class_is_partner() -> None:
    cls, ip = score_event(
        {"code": "SESSION", "minutes": 60, "partner_flag": "ENGAGED"},
        "B",
        0,
        LAUNCH_PARAMS,
    )
    _assert(cls == "partner", "ENGAGED → partner class")
    _assert(ip > 0, "ENGAGED has IP for hiring circle pool")

    cls_h, ip_h = score_event(
        {"code": "SESSION", "minutes": 60, "partner_flag": "HOME"},
        "B",
        0,
        LAUNCH_PARAMS,
    )
    _assert(cls_h == "presence", "HOME → presence PCS")
    _assert(abs(ip_h / ip - 3.0) < 1e-6, "HOME/ENGAGED = own_x/ext_x = 3")


def test_t8_member_ip_equality() -> None:
    _assert(assert_t8_member_equals_circle(100.0, 100.0), "equal")
    _assert(not assert_t8_member_equals_circle(100.0, 99.0), "mismatch")


def test_partner_cap_20pct() -> None:
    _assert(cap_partner_ip(100, 50, LAUNCH_PARAMS) == 20.0, "20% cap")
    _assert(cap_partner_ip(100, 10, LAUNCH_PARAMS) == 10.0, "under cap")
    _assert(partner_session_ip(10, "HOME") == 15.0, "session HOME")
    _assert(partner_session_ip(10, "ENGAGED") == 5.0, "session ENGAGED")


def test_epr_shrinkage_and_compute() -> None:
    low = epr_shrinkage(2.0, 5)
    _assert(low["confidence_label"] == "low", "low confidence")
    _assert(1.0 < low["shrunk"] < 2.0, "shrunk toward 1")
    epr = compute_epr(track="MENTOR", mean_growth_ratio=1.0, students_n=2, months_active=2)
    _assert(0 <= epr["epr"] <= 100, "EPR bounded")
    _assert(epr["confidence_label"] in ("low", "medium", "high"), "label")
    tutor = compute_epr(track="TUTOR", mean_growth_ratio=1.2, students_n=20, months_active=12)
    _assert(tutor["confidence_label"] in ("medium", "high"), "more evidence")


def main() -> None:
    test_t8_partner_mult()
    test_t8_engaged_class_is_partner()
    test_t8_member_ip_equality()
    test_partner_cap_20pct()
    test_epr_shrinkage_and_compute()
    print("zenq_v2_phase4_epr_checks: OK (T8 + EPR)")


if __name__ == "__main__":
    main()
