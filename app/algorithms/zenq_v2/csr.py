"""CSR allocation shares — board O / Standalone funder tool (flagged off at launch)."""

from __future__ import annotations

from typing import Any, Optional, Sequence


DEFAULT_CSR_WEIGHTS: tuple[float, float, float] = (0.5, 0.3, 0.2)
DEFAULT_CSR_FLOOR = 0.03
DEFAULT_CSR_CEIL = 0.25


def csr_allocation(
    circles: Sequence[dict[str, Any]],
    budget: float,
    weights: Optional[Sequence[float]] = None,
    floor: float = DEFAULT_CSR_FLOOR,
    ceil: float = DEFAULT_CSR_CEIL,
) -> list[float]:
    """Return INR allocation per circle.

    Each circle dict needs: yield, avg_return, K, eligible (truthy → included).
    Shares are floored/ceiled then renormalized to sum to ``budget``.
    """
    if not circles or budget <= 0:
        return [0.0] * len(circles)
    w = tuple(weights) if weights is not None else DEFAULT_CSR_WEIGHTS
    if len(w) != 3:
        raise ValueError("csr weights must be length 3 (yield, return, K)")
    ymax = max(float(c.get("yield") or 0) for c in circles) or 1.0
    kmax = max(float(c.get("K") or 0) for c in circles) or 1.0
    rs = [float(c.get("avg_return") or 0) for c in circles]
    rmin, rmax = min(rs), max(rs)

    def rnorm(c: dict[str, Any]) -> float:
        if rmax <= rmin:
            return 0.0
        return (float(c.get("avg_return") or 0) - rmin) / (rmax - rmin)

    scores: list[float] = []
    for c in circles:
        eligible = 1.0 if c.get("eligible") else 0.0
        s = eligible * (
            float(w[0]) * float(c.get("yield") or 0) / ymax
            + float(w[1]) * rnorm(c)
            + float(w[2]) * float(c.get("K") or 0) / kmax
        )
        scores.append(s)
    tot = sum(scores) or 1.0
    shares: list[float] = []
    for c, s in zip(circles, scores):
        if not c.get("eligible"):
            shares.append(0.0)
        else:
            shares.append(min(ceil, max(floor, s / tot)))
    stot = sum(shares) or 1.0
    return [float(budget) * sh / stot for sh in shares]


def equal_split_allocations(n: int, budget: float) -> list[float]:
    if n <= 0 or budget <= 0:
        return [0.0] * max(n, 0)
    each = float(budget) / n
    return [each] * n


def impact_proxy(allocations: Sequence[float], yields: Sequence[float]) -> float:
    """Simple expected-impact proxy: Σ (allocation × yield). Not a causal claim."""
    return float(sum(float(a) * float(y) for a, y in zip(allocations, yields)))
