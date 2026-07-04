"""Golden-path tests for ZenQ orchestrator (run: python -m tests.zenq_golden)."""

from app.algorithms.zenq.constants import BASE_IMPACT
from app.algorithms.zenq.core import compute_spd, compute_ziq
from app.algorithms.zenq.orchestrator import (
    SponsorMetricsSnapshot,
    StudentContextSnapshot,
    compute_circle_zenq,
    compute_sponsor_zeq,
    student_spd_from_zqa,
)


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def test_spd_neutral_first_quarter() -> None:
    _assert(student_spd_from_zqa(None, 72.0) == 1.0, "first quarter SPD should be neutral")


def test_spd_improvement_clamped() -> None:
    spd = student_spd_from_zqa(60.0, 90.0)
    _assert(0.60 <= spd <= 1.40, f"SPD out of bounds: {spd}")
    _assert(spd > 1.0, "improvement should raise SPD above 1")


def test_zeq_components_bounded() -> None:
    metrics = SponsorMetricsSnapshot(
        user_id="u1",
        session_mins=45,
        message_count=20,
        substantive_message_count=12,
        streak_days=14,
        target_status="full",
        effort_weight=10.0,
    )
    result = compute_sponsor_zeq(metrics, effort_shares=[1.0])
    _assert(0.0 <= result.zeq <= 1.30, f"ZEQ out of bounds: {result.zeq}")
    _assert(all(0 <= v <= 2 for v in result.components.values()), "component out of range")


def test_circle_ziq_formula() -> None:
    sponsors = [
        SponsorMetricsSnapshot(user_id="a", session_mins=30, message_count=10, effort_weight=5),
        SponsorMetricsSnapshot(user_id="b", session_mins=20, message_count=5, effort_weight=3),
    ]
    students = [
        StudentContextSnapshot(
            student_id="s1",
            zqa_composite=75,
            baseline_zqa=65,
            spd=student_spd_from_zqa(65, 75),
            need_band="developing",
            attendance_30d=95,
        )
    ]
    comp = compute_circle_zenq(
        circle_id="c1",
        circle_name="Test Circle",
        sponsor_metrics=sponsors,
        students=students,
    )
    expected = round(BASE_IMPACT * comp.zeq_avg * comp.zcq * comp.spd_avg, 2)
    _assert(abs(comp.ziq - expected) < 0.01, f"ZIQ mismatch: {comp.ziq} vs {expected}")
    _assert(comp.ziq >= 0, "ZIQ must be non-negative")


def test_compute_ziq_direct() -> None:
    _assert(compute_ziq(0.8, 0.5, 1.1) == round(BASE_IMPACT * 0.8 * 0.5 * 1.1, 2), "direct ZIQ")


def run_all() -> None:
    test_spd_neutral_first_quarter()
    test_spd_improvement_clamped()
    test_zeq_components_bounded()
    test_circle_ziq_formula()
    test_compute_ziq_direct()
    print("zenq_golden: all checks passed")


if __name__ == "__main__":
    run_all()
