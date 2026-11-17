"""Growth multiplier G, GrowthRatio, stretch — Tech Guide close_circles."""

from __future__ import annotations

from typing import Any, Optional

from app.algorithms.zenq_v2.params import BRACKET, LAUNCH_PARAMS, W_BASE


def growth_ratio(
    baseline: Optional[float],
    latest: Optional[float],
    n_assessments: int,
    bracket: str,
) -> Optional[float]:
    """None while Effort phase (fewer than 3 assessments after MEAN_FIRST_TWO baseline).

    Tech Guide: baseline = mean(a1, a2); gr when n >= 3; quarters = n - 2.
    """
    if n_assessments < 3 or baseline is None or latest is None:
        return None
    exp_q = float(BRACKET[bracket]["exp_q"])
    quarters = max(n_assessments - 2, 1)
    return (float(latest) - float(baseline)) / (exp_q * quarters)


def wmult(weights: dict[str, float], key: str) -> float:
    base = float(W_BASE[key])
    return float(weights.get(key, base)) / base


def G(
    gr: Optional[float],
    weights: Optional[dict[str, float]] = None,
    params: Optional[dict[str, Any]] = None,
) -> float:
    p = params or LAUNCH_PARAMS
    floor = float(p["g_floor"])
    slope = float(p["g_slope"])
    if gr is None or slope == 0.0:
        return floor
    w = weights or dict(W_BASE)
    cap = float(p["g_cap"])
    return max(floor, 1.0 + slope * wmult(w, "student") * min(float(gr), cap))


def in_stretch(prev_gr: Optional[float], prev_n: int, params: Optional[dict[str, Any]] = None) -> bool:
    p = params or LAUNCH_PARAMS
    return (
        prev_n >= int(p["stretch_min_assessments"])
        and prev_gr is not None
        and float(prev_gr) < float(p["stretch_gr_below"])
    )
