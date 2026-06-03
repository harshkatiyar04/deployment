"""Kia priority engine checks (run: python -m tests.kia_priority_engine_checks)."""

from app.services.kia_priority_engine import compute_student_priority


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def test_critical_student() -> None:
    r = compute_student_priority(
        student_name="A",
        attendance_pct=62,
        zqa_score=38,
        zqa_baseline_delta=-8.0,
        q_report_status="Pending",
        risk_level="High",
        tutor_recommendation_pending=True,
    )
    _assert(r.score >= 80, "critical score expected")
    _assert(r.urgency == "critical", "critical urgency expected")


def test_watch_student() -> None:
    r = compute_student_priority(
        student_name="B",
        attendance_pct=96,
        zqa_score=88,
        zqa_baseline_delta=2.0,
        q_report_status="Finalized",
        risk_level="Low",
        tutor_recommendation_pending=False,
    )
    _assert(r.score < 30, "watch profile should be low score")
    _assert(r.urgency == "watch", "watch urgency expected")


def main() -> None:
    test_critical_student()
    test_watch_student()
    print("All Kia priority engine checks passed.")


if __name__ == "__main__":
    main()
