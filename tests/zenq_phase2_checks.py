"""Phase 2 checks — commitment + target override (run: python -m tests.zenq_phase2_checks)."""

from app.algorithms.zenq.aggregators import build_sponsor_metrics
from app.algorithms.zenq.commitment import compute_commitment_factor


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def test_commitment_increases_with_spend_and_tenure() -> None:
    low = compute_commitment_factor(spend_inr=0, months_active=0)
    high = compute_commitment_factor(spend_inr=250_000, months_active=12)
    _assert(low == 1.0, "baseline commitment should be 1.0")
    _assert(high > low, "commitment should rise with spend and tenure")
    _assert(high <= 1.21, f"commitment should stay bounded: {high}")


def test_leader_target_overrides_activity() -> None:
    metrics = build_sponsor_metrics(
        user_id="u1",
        activity={"messages_count": 0, "orders_count": 0, "hours": 0},
        joined_at=None,
        target_status_override="stretch",
        spend_inr=100_000,
        months_active=6,
    )
    _assert(metrics.target_status == "stretch", "leader target should override")
    _assert(metrics.commitment_factor > 1.0, "commitment should reflect spend")


def run_all() -> None:
    test_commitment_increases_with_spend_and_tenure()
    test_leader_target_overrides_activity()
    print("zenq_phase2_checks: all checks passed")


if __name__ == "__main__":
    run_all()
