"""
Kia golden checks — offline (no Groq / DB required).

Run: python -m tests.kia_golden_checks
"""

from __future__ import annotations

from app.services.kia import (
    CHANNEL_CONFIG,
    _build_context_block,
    _looks_like_research_deflection,
    classify_kia_intent,
)
from app.services.kia_algorithm_guide import (
    is_algorithm_question,
    score_question_focus,
)
from app.services.kia_history import role_text_rows_to_history


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


class _Msg:
    def __init__(self, role: str, text: str):
        self.role = role
        self.text = text


def test_intent_scores_and_research() -> None:
    _assert(
        classify_kia_intent("what is my zenq score") == "scores_explain",
        "zenq should be scores_explain",
    )
    _assert(
        classify_kia_intent("what is my ziq") == "scores_explain",
        "ziq should be scores_explain",
    )
    _assert(
        classify_kia_intent(
            "give me a complete breakdown for student school cost in standard 10 in jharkhand"
        )
        == "research_general",
        "jharkhand cost should be research_general",
    )
    _assert(is_algorithm_question("explain zenq"), "zenq is algorithm question")
    _assert(score_question_focus("what is my ziq") == "ziq", "focus ziq")
    _assert(score_question_focus("what is my zqa") == "zqa", "focus zqa")
    _assert(
        score_question_focus("what is my zenq score") == "umbrella",
        "zenq focus umbrella",
    )


def test_context_labels_ziq_not_zqa_as_zenq() -> None:
    ctx = {
        "circle_name": "vit",
        "member_role": "sponsor_leader",
        "has_sponsored_students": True,
        "sponsored_student_count": 1,
        "pending_enrollment_count": 0,
        "circle_zqa_summary": {"average_zqa": 75, "student_count": 1},
        "circle_zenq_display": {
            "zenq_source": "engine",
            "circle_ziq": 42,
            "zeq_avg": 0.5,
            "zcq": 0.8,
            "spd_avg": 0.9,
            "legacy_zqa_avg": 75,
            "zenq_available": True,
        },
        "sponsored_students": [
            {
                "masked_name": "Student A",
                "grade": "Grade 8",
                "zqa_score": 75,
                "attendance_pct": 76,
            }
        ],
    }
    block = _build_context_block(ctx, "CIRCLE_CHAT")
    _assert("Circle Impact (ZIQ): 42" in block, "must inject live ZIQ")
    _assert("Academic Stats: ZQA 75" in block, "student line must say ZQA")
    _assert("Academic Stats: ZenQ 75" not in block, "must not label ZQA as ZenQ")
    _assert("NOT ZenQ/ZIQ" in block, "ZQA avg caution present")
    _assert("umbrella" in block.lower() or "ZIQ+ZEQ" in block, "umbrella rule present")


def test_legacy_caution_in_context() -> None:
    ctx = {
        "circle_name": "vit",
        "member_role": "sponsor",
        "has_sponsored_students": True,
        "sponsored_student_count": 1,
        "circle_zenq_display": {
            "zenq_source": "legacy_zqa_avg",
            "circle_ziq": None,
            "legacy_zqa_avg": 75,
            "zenq_available": True,
            "caution": (
                "Circle Impact engine score is not materialised yet. "
                "legacy_zqa_avg is student ZQA average only — "
                "do NOT call it ZenQ, ZIQ, or Circle Impact."
            ),
        },
        "sponsored_students": [],
    }
    block = _build_context_block(ctx, "CIRCLE_CHAT")
    _assert("CAUTION:" in block, "legacy caution must appear")
    _assert("do NOT call it ZenQ" in block, "must forbid calling avg ZQA ZenQ")


def test_history_excludes_trailing_user() -> None:
    rows = [
        _Msg("user", "what is my zenq score"),
        _Msg("kia", "ZenQ is an umbrella…"),
        _Msg("user", "what is my ziq"),
    ]
    hist = role_text_rows_to_history(
        rows, exclude_trailing_user_text="what is my ziq"
    )
    _assert(len(hist) == 2, f"expected 2 history msgs, got {len(hist)}")
    _assert(hist[0]["role"] == "user", "first is prior user")
    _assert(hist[1]["role"] == "assistant", "kia maps to assistant")
    _assert("ziq" not in hist[-1]["content"].lower() or hist[-1]["role"] == "assistant", "ok")


def test_research_deflection_detector() -> None:
    bad = (
        "I'm not able to provide a detailed breakdown of student school costs "
        "for Standard 10 in Jharkhand. However, our circle supports a Grade 8 "
        "student with a ZenQ score of 75."
    )
    good = (
        "Here is an estimate for Std 10 in Jharkhand: tuition bands… "
        "These are estimates — verify locally."
    )
    _assert(_looks_like_research_deflection(bad), "must flag refusal+score pivot")
    _assert(not _looks_like_research_deflection(good), "must allow real research answer")


def test_circle_chat_token_budget() -> None:
    _assert(
        CHANNEL_CONFIG["CIRCLE_CHAT"]["max_tokens"] >= 700,
        "CIRCLE_CHAT max_tokens should be raised for quality replies",
    )


def main() -> None:
    test_intent_scores_and_research()
    test_context_labels_ziq_not_zqa_as_zenq()
    test_legacy_caution_in_context()
    test_history_excludes_trailing_user()
    test_research_deflection_detector()
    test_circle_chat_token_budget()
    print("All Kia golden checks passed.")


if __name__ == "__main__":
    main()
