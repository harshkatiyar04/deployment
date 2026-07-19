"""Kia ZIQ reply quality checks. Run: python -m tests.kia_ziq_reply_checks"""

from app.services.kia_algorithm_guide import format_algorithm_reply, score_question_focus
from app.services.kia_zenq_snapshot import enrich_zenq_display_for_kia


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def test_focus_ziq() -> None:
    _assert(score_question_focus("what is my ziq and how should i increase it") == "ziq", "focus")


def test_strip_raw_decimals_and_orphan_bullets() -> None:
    raw = """**ZIQ — Circle Impact**
Your circle's current ZIQ score is 29.

**Breaking down ZIQ**
•
ZEQ (effort): 0.6025 (average)
•
ZCQ (context): 0.4799 (average)

**Increasing ZIQ**
Increasing
ZEQ (effort) by engaging more
"""
    out = format_algorithm_reply(raw)
    _assert("0.6025" not in out, f"raw decimal leaked: {out}")
    _assert("0.4799" not in out, f"raw decimal leaked: {out}")
    _assert("Increasing ZEQ" in out or "Increasing\nZEQ" not in out, out)


def test_enrich_uses_bands_not_raw() -> None:
    display = {
        "zenq_score": 29,
        "zenq_available": True,
        "zenq_source": "engine",
        "zenq_breakdown": {
            "ziq": 28.9,
            "zeq_avg": 0.6025,
            "zcq": 0.4799,
            "spd_avg": 1.0,
        },
        "legacy_zqa_avg": 75,
    }
    snap = enrich_zenq_display_for_kia(display)
    _assert(snap["circle_ziq"] == 29, snap)
    _assert(snap.get("ziq_band") == "Emerging", snap)
    _assert("zeq_avg" not in snap, "should not expose raw zeq_avg key for chat")
    _assert(snap.get("zeq_band"), "zeq band expected")
    _assert(len(snap.get("how_to_raise_ziq") or []) >= 3, "tips expected")


def main() -> None:
    test_focus_ziq()
    test_strip_raw_decimals_and_orphan_bullets()
    test_enrich_uses_bands_not_raw()
    print("All Kia ZIQ reply checks passed.")


if __name__ == "__main__":
    main()
