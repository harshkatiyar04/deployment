"""ZQA v2 robustness checks (run: python -m tests.zqa_robustness_checks)."""

from app.algorithms.zenq.zqa import (
    compute_academic_composite,
    compute_zqa_result,
    resolve_academic_subjects,
    validate_zqa_inputs,
)
from app.algorithms.zenq.zqa_policy import publish_blocking_issues
from app.services.school_zqa_engine import assert_zqa_publishable


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def _blooms() -> dict[str, float]:
    return {
        "remember": 4,
        "understand": 4,
        "apply": 4,
        "analyse": 4,
        "evaluate": 4,
        "create": 4,
    }


def _sel() -> dict[str, float]:
    return {
        "self_awareness": 4,
        "self_management": 4,
        "social_awareness": 4,
        "relationship_skills": 4,
        "responsible_decisions": 4,
    }


def _complete_kwargs(**overrides):
    base = {
        "quarter": "Q1",
        "subject_scores": {"english": 80, "maths": 75, "science": 82, "social": 78},
        "blooms": _blooms(),
        "sel": _sel(),
        "attendance_pct": 95,
        "avg_score": 79,
        "rank_in_class": "5/30",
        "class_size": 30,
        "finalized": True,
        "prior_quarter_subjects": {},
        "narrative": "Student showed consistent progress across subjects this quarter.",
    }
    base.update(overrides)
    return base


def test_single_subject_cap() -> None:
    r = compute_zqa_result(
        quarter="Q1",
        subject_scores={"english": 98},
        blooms=_blooms(),
        sel=_sel(),
        attendance_pct=95,
        avg_score=98,
        rank_in_class="1",
        class_size=30,
        finalized=False,
        prior_quarter_subjects={},
    )
    _assert(r.zqa_composite <= 60, "single subject should be capped")
    _assert(r.academic.get("single_subject_cap_applied") == 60.0, "cap metadata missing")
    _assert(not r.zqa_published, "draft should not publish")


def test_finalized_requires_holistic() -> None:
    issues = validate_zqa_inputs(
        subject_scores={"english": 80, "maths": 75, "science": 82},
        blooms=None,
        sel=None,
        attendance_pct=90,
        avg_score=77,
        rank_in_class="5",
        class_size=30,
        finalized=True,
        narrative="Quarter summary.",
    )
    _assert("finalized_report_requires_blooms" in issues, "blooms required")
    _assert("finalized_report_requires_sel" in issues, "sel required")
    blockers = publish_blocking_issues(issues)
    _assert(len(blockers) >= 2, "publish blockers expected")


def test_narrative_required_for_finalize() -> None:
    issues = validate_zqa_inputs(
        subject_scores={"english": 80, "maths": 75, "science": 82},
        blooms=_blooms(),
        sel=_sel(),
        attendance_pct=95,
        avg_score=79,
        rank_in_class="5/30",
        class_size=30,
        finalized=True,
        narrative="   ",
    )
    _assert("finalized_report_requires_narrative" in issues, "narrative required")
    _assert(
        "finalized_report_requires_narrative" in publish_blocking_issues(issues),
        "narrative should block publish",
    )


def test_science_in_academic_composite() -> None:
    subjects, _ = resolve_academic_subjects(
        {"english": 80, "maths": 70, "science": 90, "social": 75}
    )
    composite = compute_academic_composite(subjects)
    _assert(composite > 78, "science should lift academic composite")
    _assert(subjects.get("science") == 90.0, "science should be parsed")


def test_publish_requires_all_pillars() -> None:
    r = compute_zqa_result(**_complete_kwargs())
    _assert(r.zqa_published, "complete report should publish")
    _assert(r.zqa_composite > 0, "published composite expected")
    labels = r.to_breakdown_dict().get("publish_blocker_labels") or []
    _assert(labels == [], "published report should have no blocker labels")


def test_attendance_integrity_factor() -> None:
    high = compute_zqa_result(**_complete_kwargs(attendance_pct=95))
    low = compute_zqa_result(**_complete_kwargs(attendance_pct=80))
    _assert(high.zqa_published and low.zqa_published, "attendance alone should not block publish")
    _assert(low.zqa_composite < high.zqa_composite, "low attendance should reduce composite")
    _assert(
        "attendance_below_integrity_floor" in low.validation_issues,
        "low attendance should be flagged",
    )
    _assert(
        low.pillars.get("attendance_integrity_factor", 1.0) < 1.0,
        "integrity factor should apply below floor",
    )


def test_assert_zqa_publishable_raises() -> None:
    try:
        assert_zqa_publishable(
            subject_scores={"english": 80, "maths": 75},
            blooms=None,
            sel=_sel(),
            attendance_pct=95,
            avg_score=77,
            rank_in_class="5/30",
            class_size=30,
            narrative="Summary.",
        )
        _assert(False, "assert_zqa_publishable should raise")
    except ValueError as exc:
        _assert("Bloom" in str(exc), "human-readable blooms blocker expected")


def main() -> None:
    test_single_subject_cap()
    test_finalized_requires_holistic()
    test_narrative_required_for_finalize()
    test_science_in_academic_composite()
    test_publish_requires_all_pillars()
    test_attendance_integrity_factor()
    test_assert_zqa_publishable_raises()
    print("All ZQA robustness checks passed.")


if __name__ == "__main__":
    main()
