from __future__ import annotations

import math
import statistics
from typing import Optional

from .constants import BASE_IMPACT, DECAY_RATE, DEFAULT_WEIGHTS, SPARK_MULTIPLIER


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(value)))


def apply_ras(component_value: float, ras: float) -> float:
    if ras > 0.80:
        return component_value * 1.00
    if ras > 0.60:
        return component_value * 0.80
    if ras > 0.40:
        return component_value * 0.60
    return component_value * 0.30


def compute_t(session_mins: float, ras: float = 1.0) -> float:
    mins = max(0.0, float(session_mins))
    if mins <= 10:
        raw = mins / 10.0
    elif mins <= 30:
        raw = 1.0 + 0.5 * ((mins - 10.0) / 20.0)
    else:
        raw = 1.5
    return apply_ras(raw / 1.5, ras)


def compute_a(status: str) -> float:
    return {"none": 0.0, "partial": 0.5, "full": 1.0, "stretch": 1.2}.get(status, 0.0)


def compute_s(days: int, *, new_user: bool = False, spark_active: bool = False) -> float:
    if new_user and days <= 7:
        base = 0.50
    elif days <= 0:
        base = 0.00
    elif days <= 7:
        base = 0.20 + 0.10 * days
    elif days <= 30:
        base = 0.90 + 0.10 * ((days - 7) / 23.0)
    else:
        base = 1.00
    if spark_active:
        return min(base * SPARK_MULTIPLIER, 1.0)
    return base


def compute_comm_index(message_count: int, substantive_message_count: int, avg_ras: float = 1.0) -> float:
    passive = min(0.05 * max(0, message_count - substantive_message_count), 0.30)
    substantive = min(0.15 * max(0, substantive_message_count), 0.70)
    return apply_ras(min(passive + substantive, 1.0), avg_ras)


def compute_inspire_index(active: int, passive: int) -> float:
    return min(0.20 * max(0, active) + 0.05 * max(0, passive), 1.0)


def compute_equity(effort_shares: list[float]) -> float:
    if len(effort_shares) < 2:
        return 1.0
    std = statistics.stdev(effort_shares)
    return 0.90 + 0.20 * max(0.0, 1.0 - (std / 0.5))


def compute_zeq(
    t: float,
    a: float,
    s: float,
    comm_index: float,
    inspire_index: float,
    equity: float,
    commitment_factor: float,
    weights: Optional[dict[str, float]] = None,
) -> float:
    w = weights or DEFAULT_WEIGHTS
    raw = (
        w["T"] * t
        + w["A"] * a
        + w["S"] * s
        + w["Cm"] * comm_index
        + w["In"] * inspire_index
        + w["E"] * (equity - 1.0)
        + w["C"] * (commitment_factor - 1.0)
    )
    return _clamp(raw, 0.0, 1.30)


def get_k(need_band: str) -> float:
    return {
        "standard": 0.85,
        "developing": 1.00,
        "high": 1.15,
        "critical": 1.30,
    }.get((need_band or "").lower(), 1.00)


def get_k_att(attendance_30d_ratio: float, absent_today: bool) -> float:
    base = 0.80 + 0.40 * _clamp(attendance_30d_ratio, 0.0, 1.0)
    return base * (0.70 if absent_today else 1.0)


def get_n_eff(group_size: int) -> float:
    return math.sqrt(max(int(group_size), 1))


def compute_zcq(k: float, k_att: float, n_eff: float) -> float:
    return max(0.20, k * k_att * (1.0 / n_eff))


def compute_zqa_composite(language: Optional[float], maths: Optional[float], history: Optional[float]) -> float:
    # If one subject is missing, re-normalize remaining declared weights.
    weighted = [("language", language, 0.40), ("maths", maths, 0.35), ("history", history, 0.25)]
    present = [(score, weight) for _, score, weight in weighted if score is not None]
    if not present:
        return 0.0
    total_weight = sum(weight for _, weight in present)
    return sum(_clamp(score, 0, 100) * weight for score, weight in present) / total_weight


def classify_zqa_band(score: float) -> str:
    if score >= 85:
        return "4 - Insightful"
    if score >= 65:
        return "3 - Developing"
    if score >= 40:
        return "2 - Emerging"
    return "1 - Beginning"


def compute_spd(baseline: Optional[float], current: float) -> float:
    if baseline is None:
        return 1.00
    return _clamp(1.0 + ((current - baseline) / 100.0) * 2.0, 0.60, 1.40)


def apply_decay(value: float, months_since_contribution: int, decay_rate: float = DECAY_RATE) -> float:
    if months_since_contribution <= 2:
        return value
    months_beyond = months_since_contribution - 2
    return value * ((1.0 - decay_rate) ** months_beyond)


def compute_ziq(zeq: float, zcq: float, spd: float, base_impact: float = BASE_IMPACT) -> float:
    return base_impact * zeq * zcq * spd


def compute_ziq_per_member(ziq: float, n_eff: float) -> float:
    return ziq / n_eff if n_eff > 0 else ziq
