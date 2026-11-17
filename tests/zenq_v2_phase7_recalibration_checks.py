"""ZenQ v2 Phase 7 — recalibration + sealed predictions.

Run: python -m tests.zenq_v2_phase7_recalibration_checks
"""

from __future__ import annotations

from app.algorithms.zenq_v2.params import CONSERVATIVE_LAUNCH_PARAMS, LAUNCH_PARAMS
from app.algorithms.zenq_v2.schedule_recalibration import (
    STATUS_ELIGIBLE,
    STATUS_LOGGED,
    build_proposal_payload,
    clamp_equalisation,
    clip_proposed_shift,
    propose_equalisation,
    recalibration_status_for_pairs,
)
from app.services.zenq_v2.recalibration import _content_hash


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def test_launch_params() -> None:
    _assert(int(LAUNCH_PARAMS["recalibration_min_pairs"]) == 200, "min pairs 200")
    _assert(float(LAUNCH_PARAMS["recalibration_max_shift"]) == 0.05, "max shift 0.05")
    bounds = LAUNCH_PARAMS.get("eq_bounds") or []
    _assert(list(bounds) == [0.8, 1.25], "eq bounds")
    _assert(LAUNCH_PARAMS["agent_apply"] is True, "product agent.apply true")
    _assert(CONSERVATIVE_LAUNCH_PARAMS["agent_apply"] is False, "conservative apply false")


def test_clip_and_equalisation() -> None:
    clipped = clip_proposed_shift({"fund_ip": 0.2, "spark_ip": -0.1}, 0.05)
    _assert(clipped["fund_ip"] == 0.05, "clip up")
    _assert(clipped["spark_ip"] == -0.05, "clip down")
    eq = clamp_equalisation({"A": 0.5, "B": 2.0}, [0.8, 1.25])
    _assert(eq["A"] == 0.8 and eq["B"] == 1.25, "eq clamp")
    prop = propose_equalisation({"B:Developing": 0.0})
    _assert(abs(prop["B:Developing"] - 1.0) < 1e-9, "neutral eq")


def test_status_gate() -> None:
    _assert(recalibration_status_for_pairs(199) == STATUS_LOGGED, "199 logged")
    _assert(recalibration_status_for_pairs(200) == STATUS_ELIGIBLE, "200 eligible")
    p_lo = build_proposal_payload(
        pairs=50, proposed_shift={"x": 1}, equalisation={"default": 1.0}
    )
    _assert(p_lo["status"] == STATUS_LOGGED and p_lo["auto_applied"] is False, "no auto")
    p_hi = build_proposal_payload(
        pairs=200, proposed_shift={"x": 1}, equalisation={"default": 1.0}
    )
    _assert(p_hi["status"] == STATUS_ELIGIBLE and p_hi["auto_applied"] is False, "eligible only")


def test_seal_hash_stable() -> None:
    a = _content_hash("pilot_yield", {"band": "steady"})
    b = _content_hash("pilot_yield", {"band": "steady"})
    c = _content_hash("pilot_yield", {"band": "other"})
    _assert(a == b and len(a) == 64, "stable sha256")
    _assert(a != c, "value changes hash")


def main() -> None:
    test_launch_params()
    test_clip_and_equalisation()
    test_status_gate()
    test_seal_hash_stable()
    print("zenq_v2_phase7_recalibration_checks: OK")


if __name__ == "__main__":
    main()
