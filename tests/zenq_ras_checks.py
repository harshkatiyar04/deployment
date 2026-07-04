"""RAS scorer checks (run: python -m tests.zenq_ras_checks)."""

from app.algorithms.zenq.aggregators import is_substantive_message
from app.algorithms.zenq.ras import message_quality_fields, score_message_ras
from app.services.zenq_ras_ai import blend_ras_scores


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def test_substantive_long_message() -> None:
    text = (
        "We should plan a session for the student because their maths progress "
        "needs more structured support this month."
    )
    _assert(is_substantive_message(text), "long reflective message should be substantive")


def test_ras_warn_lower_than_allow() -> None:
    text = "Thanks for sharing the update on attendance this week."
    allow = score_message_ras(text, "allow", substantive=True)
    warn = score_message_ras(text, "warn", substantive=True)
    _assert(warn < allow, "warn should reduce RAS vs allow")


def test_ras_low_effort_short() -> None:
    score = score_message_ras("ok", "allow")
    _assert(score <= 0.55, f"low-effort message should score low: {score}")


def test_ras_bounded() -> None:
    fields = message_quality_fields("Great plan — let's support her science goals next week.", "allow")
    _assert(0.0 <= fields["ras_score"] <= 1.0, "RAS must be 0-1")
    _assert(fields["zenq_substantive"] is True, "reflective message should be substantive")


def test_blend_prefers_ai_when_present() -> None:
    blended = blend_ras_scores(0.5, 0.9, shield_action="allow")
    _assert(blended > 0.5, "AI boost should raise blended RAS")


def test_blend_block_caps() -> None:
    blended = blend_ras_scores(0.8, 0.95, shield_action="block")
    _assert(blended <= 0.25, "blocked messages should score very low")


def run_all() -> None:
    test_substantive_long_message()
    test_ras_warn_lower_than_allow()
    test_ras_low_effort_short()
    test_ras_bounded()
    test_blend_prefers_ai_when_present()
    test_blend_block_caps()
    print("zenq_ras_checks: all checks passed")


if __name__ == "__main__":
    run_all()
