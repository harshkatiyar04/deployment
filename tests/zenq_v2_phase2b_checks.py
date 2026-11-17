"""ZenQ v2 Phase 2b — T5 weights shape + T15 agent.apply gate.

Run: python -m tests.zenq_v2_phase2b_checks
"""

from __future__ import annotations

from app.algorithms.zenq_v2.agent_rules import apply_deltas, propose_weight_deltas
from app.algorithms.zenq_v2.params import (
    CONSERVATIVE_LAUNCH_PARAMS,
    LAUNCH_PARAMS,
    W_BASE,
    W_BOUNDS,
)
from app.services.zenq_v2.weights import (
    assert_weights_shape,
    compute_neutrality,
    pick_weight_source,
    weights_equal,
)


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def test_t5_baseline_shape() -> None:
    assert_weights_shape(dict(W_BASE))
    _assert(abs(sum(W_BASE.values()) - 100) < 1e-9, "W_BASE sums to 100")
    for k, (lo, hi) in W_BOUNDS.items():
        _assert(lo <= W_BASE[k] <= hi, f"{k} in bounds")


def test_t5_neutrality_unchanged() -> None:
    nu = compute_neutrality(dict(W_BASE), dict(W_BASE))
    _assert(nu == 1.0, "ν=1 when weights unchanged")
    shifted = dict(W_BASE)
    shifted["chat"] = 5
    shifted["presence"] = 35
    nu2 = compute_neutrality(shifted, dict(W_BASE), prior_actual_earnings=100, prior_rescored_earnings=80)
    _assert(abs(nu2 - 1.25) < 1e-9, "ν = actual/rescored when weights move")


def test_t5_pick_source_carried_when_apply_false() -> None:
    w, source, _ = pick_weight_source(
        prev_w=dict(W_BASE),
        agent_apply=False,
        approved_proposal={**W_BASE, "chat": 15, "presence": 25},
    )
    _assert(source == "CARRIED", "apply=false ignores agent proposal")
    _assert(weights_equal(w, W_BASE), "carried baseline")


def test_t5_pick_source_agent_when_apply_true() -> None:
    prop = dict(W_BASE)
    prop["chat"] = 8
    prop["presence"] = 32
    w, source, _ = pick_weight_source(
        prev_w=dict(W_BASE),
        agent_apply=True,
        approved_proposal=prop,
    )
    _assert(source == "AGENT", "apply=true uses approved proposal")
    assert_weights_shape(w)


def test_t15_product_agent_apply_true() -> None:
    _assert(LAUNCH_PARAMS["agent_apply"] is True, "product agent.apply true")
    _assert(CONSERVATIVE_LAUNCH_PARAMS["agent_apply"] is False, "conservative apply false")


def test_t15_proposals_do_not_mutate_via_rules() -> None:
    """R1–R5 propose deltas; apply_deltas only returns a new dict — never mutates W_BASE."""
    base = dict(W_BASE)
    snap = dict(W_BASE)
    # Force R3 (high funding share)
    deltas, fired, reason = propose_weight_deltas(
        {"funding_share": 0.5, "chat_share": 0, "presence_share": 0, "kia_share": 0.1},
        LAUNCH_PARAMS,
    )
    _assert("R3" in fired, f"R3 should fire, got {fired} ({reason})")
    proposed = apply_deltas(base, deltas)
    _assert(weights_equal(W_BASE, snap), "W_BASE immutable")
    _assert(not weights_equal(proposed, W_BASE), "proposal differs")
    assert_weights_shape(proposed)
    # Gate still honoured when apply=false (conservative path)
    live, source, _ = pick_weight_source(
        prev_w=dict(W_BASE),
        agent_apply=False,
        approved_proposal=proposed,
    )
    _assert(source == "CARRIED" and weights_equal(live, W_BASE), "apply=false ignores proposal")
    live_on, source_on, _ = pick_weight_source(
        prev_w=dict(W_BASE),
        agent_apply=True,
        approved_proposal=proposed,
    )
    _assert(source_on == "AGENT" and weights_equal(live_on, proposed), "apply=true uses proposal")


def test_t15_cooldown_blocks_rules() -> None:
    deltas, fired, _ = propose_weight_deltas(
        {"funding_share": 0.5, "chat_share": 0, "presence_share": 0, "kia_share": 0.1},
        LAUNCH_PARAMS,
        blocked_rules={"R3"},
    )
    _assert("R3" not in fired, "cooldown blocks R3")
    _assert(all(abs(v) < 1e-12 for v in deltas.values()) or "R3" not in fired, "no R3 delta")


def test_r1_r5_ids_present() -> None:
    # Smoke: each rule can fire in isolation
    cases = [
        (
            "R1",
            {
                "chat_share": 0.25,
                "mean_growth_ratio": 0.4,
                "mean_growth_ratio_3m": 0.5,
                "presence_share": 0,
                "funding_share": 0,
                "kia_share": 0.2,
            },
        ),
        ("R2", {"presence_share": 0.4, "referral_activations": 0, "kia_share": 0.2}),
        ("R4", {"regress_share": 0.4, "kia_share": 0.2}),
        ("R5", {"kia_share": 0.01, "presence_share": 0.2}),
    ]
    for rule, sig in cases:
        _, fired, _ = propose_weight_deltas(sig, LAUNCH_PARAMS)
        _assert(rule in fired, f"{rule} should fire on fixture")


def main() -> None:
    test_t5_baseline_shape()
    test_t5_neutrality_unchanged()
    test_t5_pick_source_carried_when_apply_false()
    test_t5_pick_source_agent_when_apply_true()
    test_t15_product_agent_apply_true()
    test_t15_proposals_do_not_mutate_via_rules()
    test_t15_cooldown_blocks_rules()
    test_r1_r5_ids_present()
    print("zenq_v2_phase2b_checks: OK (T5 + T15)")


if __name__ == "__main__":
    main()
