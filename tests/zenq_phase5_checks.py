"""Phase 5 checks — weight recalibration (run: python -m tests.zenq_phase5_checks)."""

from app.algorithms.zenq.constants import DEFAULT_WEIGHTS
from app.algorithms.zenq.recalibration import compute_component_correlations, recalibrate_weights


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def test_recalibrate_normalizes_and_bounded() -> None:
    n = 40
    history = {
        "T": [0.5 + (i % 5) * 0.02 for i in range(n)],
        "A": [0.4 + (i % 7) * 0.01 for i in range(n)],
        "S": [0.6 for _ in range(n)],
        "Cm": [0.3 for _ in range(n)],
        "In": [0.2 for _ in range(n)],
        "E": [0.1 for _ in range(n)],
        "C": [0.05 for _ in range(n)],
    }
    spd = [0.9 + (i % 3) * 0.05 for i in range(n)]
    next_weights = recalibrate_weights(history, spd, DEFAULT_WEIGHTS)
    total = sum(next_weights.values())
    _assert(abs(total - 1.0) < 0.001, f"weights should sum to 1, got {total}")
    for key, val in next_weights.items():
        _assert(0.0 < val < 1.0, f"{key} weight out of range: {val}")


def test_correlations_need_min_samples() -> None:
    short = compute_component_correlations({"T": [0.1, 0.2]}, [1.0, 1.1], min_samples=30)
    _assert(short["T"] == 0.0, "short series should yield zero correlation")


def test_insufficient_history_keeps_weights() -> None:
  current = dict(DEFAULT_WEIGHTS)
  history = {k: [0.5] * 5 for k in current}
  spd = [1.0] * 5
  next_weights = recalibrate_weights(history, spd, current)
  _assert(sum(abs(next_weights[k] - current[k]) for k in current) < 0.2, "small sample should shift little")


def run_all() -> None:
    test_recalibrate_normalizes_and_bounded()
    test_correlations_need_min_samples()
    test_insufficient_history_keeps_weights()
    print("zenq_phase5_checks: all checks passed")


if __name__ == "__main__":
    run_all()
