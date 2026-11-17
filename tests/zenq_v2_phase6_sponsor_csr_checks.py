"""ZenQ v2 Phase 6 — Sponsor / CSR (design flags on).

Run: python -m tests.zenq_v2_phase6_sponsor_csr_checks
"""

from __future__ import annotations

from app.algorithms.zenq_v2.csr import csr_allocation, equal_split_allocations, impact_proxy
from app.algorithms.zenq_v2.language import (
    FUNDER_CLAIM_LANGUAGE,
    assert_copy_clean,
    funder_claim_language,
)
from app.algorithms.zenq_v2.params import CONSERVATIVE_LAUNCH_PARAMS, LAUNCH_PARAMS


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def test_product_flags_on() -> None:
    flags = LAUNCH_PARAMS.get("flags") or {}
    _assert(flags.get("sponsor_yield") is True, "sponsor_yield on")
    _assert(flags.get("csr_tool") is True, "csr_tool on")
    cflags = CONSERVATIVE_LAUNCH_PARAMS.get("flags") or {}
    _assert(cflags.get("sponsor_yield") is False, "conservative yield off")
    _assert(cflags.get("csr_tool") is False, "conservative csr off")


def test_funder_claim_copy() -> None:
    claim = funder_claim_language()
    _assert(claim == FUNDER_CLAIM_LANGUAGE, "claim constant")
    assert_copy_clean(claim)
    _assert("impact claims" in claim.lower(), "pilot framing")


def test_csr_allocation_math() -> None:
    circles = [
        {"yield": 10.0, "avg_return": 0.1, "K": 1.0, "eligible": True},
        {"yield": 5.0, "avg_return": 0.0, "K": 1.3, "eligible": True},
        {"yield": 20.0, "avg_return": 0.2, "K": 0.9, "eligible": False},
    ]
    budget = 100_000.0
    shares = csr_allocation(circles, budget)
    _assert(len(shares) == 3, "3 shares")
    _assert(abs(sum(shares) - budget) < 0.01, "sums to budget")
    _assert(shares[2] == 0.0, "ineligible gets 0")
    _assert(shares[0] > 0 and shares[1] > 0, "eligible positive")
    equal = equal_split_allocations(2, budget)
    _assert(abs(equal[0] - 50_000) < 0.01, "equal split")
    proxy = impact_proxy(shares[:2], [10.0, 5.0])
    _assert(proxy > 0, "impact proxy")


def test_payload_no_student_keys() -> None:
    from app.services.zenq_v2.sponsor_csr import _strip_student_keys

    dirty = {
        "circle_id": "c1",
        "circle_name": "Alpha",
        "student_id": "should-go",
        "child_ids": ["x"],
        "k": 1.0,
    }
    clean = _strip_student_keys(dirty)
    _assert("student_id" not in clean and "child_ids" not in clean, "no child keys")
    _assert(clean["circle_name"] == "Alpha", "name kept")


def main() -> None:
    test_product_flags_on()
    test_funder_claim_copy()
    test_csr_allocation_math()
    test_payload_no_student_keys()
    print("zenq_v2_phase6_sponsor_csr_checks: OK")


if __name__ == "__main__":
    main()
