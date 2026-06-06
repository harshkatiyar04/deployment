from __future__ import annotations

import math
from typing import Iterable

from .constants import MAX_SHIFT_PER_CYCLE, WEIGHT_BOUNDS


def _clip(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _pearsonr_safe(x: list[float], y: list[float]) -> float:
    n = len(x)
    if n < 2 or n != len(y):
        return 0.0
    mx = sum(x) / n
    my = sum(y) / n
    cov = sum((a - mx) * (b - my) for a, b in zip(x, y))
    vx = sum((a - mx) ** 2 for a in x)
    vy = sum((b - my) ** 2 for b in y)
    den = math.sqrt(vx * vy)
    if den == 0.0:
        return 0.0
    return cov / den


def recalibrate_weights(
    component_history: dict[str, Iterable[float]],
    spd_outcomes: list[float],
    current_weights: dict[str, float],
) -> dict[str, float]:
    correlations: dict[str, float] = {}
    for component, values in component_history.items():
        series = list(values)
        if len(series) >= 30 and len(series) == len(spd_outcomes):
            corr = _pearsonr_safe(series, spd_outcomes)
            correlations[component] = max(corr, 0.0)
        else:
            correlations[component] = current_weights.get(component, 0.0)

    total = sum(correlations.values()) or 1.0
    next_weights: dict[str, float] = {}
    for component, old_weight in current_weights.items():
        target = correlations.get(component, old_weight) / total
        shift = _clip(target - old_weight, -MAX_SHIFT_PER_CYCLE, MAX_SHIFT_PER_CYCLE)
        low, high = WEIGHT_BOUNDS.get(component, (0.0, 1.0))
        next_weights[component] = _clip(old_weight + shift, low, high)

    norm = sum(next_weights.values()) or 1.0
    return {k: v / norm for k, v in next_weights.items()}
