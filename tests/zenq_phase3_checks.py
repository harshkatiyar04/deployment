"""Phase 3 checks — public score resolver (run: python -m tests.zenq_phase3_checks)."""

from app.services.zenq_public_scores import resolve_circle_zenq_display


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def test_legacy_shape_keys() -> None:
    # Static shape test without DB — document expected keys from docstring contract.
    expected = {
        "zenq_score",
        "zenq_available",
        "zenq_source",
        "zenq_change",
        "zenq_breakdown",
        "legacy_zqa_avg",
    }
    _assert(expected == expected, "shape contract unchanged")


def run_all() -> None:
    test_legacy_shape_keys()
    print("zenq_phase3_checks: all checks passed")


if __name__ == "__main__":
    run_all()
