"""ZenQ v2 Phase 5 — referral activation + Spark cap/irreversibility.

Run: python -m tests.zenq_v2_phase5_referral_spark_checks
"""

from __future__ import annotations

from app.algorithms.zenq_v2.params import LAUNCH_PARAMS
from app.algorithms.zenq_v2.scoring import score_event
from app.services.zenq_v2.referrals import (
    ACTIVATION_MIN_SESSIONS,
    SPARK_CAP_PER_YEAR,
    SPARK_IP,
    milestone_words_from_pcs,
    referral_ready,
    referral_words,
    spark_remaining,
    spark_words,
)


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def test_activation_gate() -> None:
    _assert(ACTIVATION_MIN_SESSIONS == 8, "8 sessions")
    _assert(not referral_ready(sessions_completed=7, first_pledge_paid=True), "need 8")
    _assert(not referral_ready(sessions_completed=8, first_pledge_paid=False), "need pledge")
    _assert(referral_ready(sessions_completed=8, first_pledge_paid=True), "ready")


def test_spark_cap_and_words() -> None:
    _assert(SPARK_CAP_PER_YEAR == 2, "cap 2")
    _assert(SPARK_IP == 60.0, "60 IP internal")
    _assert(spark_remaining(0) == 2, "2 left")
    _assert(spark_remaining(2) == 0, "full")
    w = spark_words(sparks_this_year=2)
    _assert("raw" not in w.lower() and "60" not in w, "no raw IP in words")
    _assert("two" in w.lower() or "complete" in w.lower(), "cap message")


def test_spark_scoring_ip() -> None:
    cls, ip = score_event({"code": "SPARK"}, "B", 0, LAUNCH_PARAMS)
    _assert(cls == "spark" and ip == 60.0, "spark class 60")
    cls2, ip2 = score_event({"code": "REFERRAL_ACTIVATED"}, "B", 0, LAUNCH_PARAMS)
    _assert(cls2 == "growth" and ip2 == float(LAUNCH_PARAMS["referral_ip"]), "referral IP")
    cls3, ip3 = score_event({"code": "REFERRAL_ANNIVERSARY"}, "B", 0, LAUNCH_PARAMS)
    _assert(cls3 == "growth" and ip3 == float(LAUNCH_PARAMS["anniversary_ip"]), "anniversary")


def test_member_copy_no_ip() -> None:
    rw = referral_words(activations=1, anniversaries=1)
    _assert("150" not in rw and "IP" not in rw, "referral words clean")
    mw = milestone_words_from_pcs(12.0)
    _assert("contributor" in mw.lower(), "milestone words")


def main() -> None:
    test_activation_gate()
    test_spark_cap_and_words()
    test_spark_scoring_ip()
    test_member_copy_no_ip()
    print("zenq_v2_phase5_referral_spark_checks: OK")


if __name__ == "__main__":
    main()
