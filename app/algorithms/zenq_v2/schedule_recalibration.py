"""IP-schedule recalibration helpers — log from day one; apply gate ≥200 pairs."""

from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

STATUS_LOGGED = "LOGGED"
STATUS_ELIGIBLE = "ELIGIBLE"
STATUS_APPROVED = "APPROVED"
STATUS_REJECTED = "REJECTED"

DEFAULT_MAX_SHIFT = 0.05
DEFAULT_EQ_BOUNDS = (0.8, 1.25)
DEFAULT_MIN_PAIRS = 200


def clip_proposed_shift(
    shift: Mapping[str, float],
    max_shift: float = DEFAULT_MAX_SHIFT,
) -> dict[str, float]:
    cap = abs(float(max_shift))
    return {str(k): max(-cap, min(cap, float(v))) for k, v in shift.items()}


def clamp_equalisation(
    factors: Mapping[str, float],
    bounds: Sequence[float] = DEFAULT_EQ_BOUNDS,
) -> dict[str, float]:
    lo = float(bounds[0]) if bounds else 0.8
    hi = float(bounds[1]) if len(bounds) > 1 else 1.25
    if lo > hi:
        lo, hi = hi, lo
    return {str(k): max(lo, min(hi, float(v))) for k, v in factors.items()}


def propose_equalisation(
    by_bracket_need: Optional[Mapping[str, float]] = None,
    *,
    bounds: Sequence[float] = DEFAULT_EQ_BOUNDS,
) -> dict[str, float]:
    """Deterministic equalisation factors from share deltas (1.0 = neutral).

    ``by_bracket_need`` maps keys like ``B:Developing`` → observed share delta
    (−0.2..+0.2 typical). Factor = 1 / (1 + delta), then clamped.
    """
    raw: dict[str, float] = {}
    src = by_bracket_need or {}
    if not src:
        return clamp_equalisation({"default": 1.0}, bounds)
    for key, delta in src.items():
        d = float(delta)
        denom = 1.0 + d
        raw[str(key)] = 1.0 if abs(denom) < 1e-9 else 1.0 / denom
    return clamp_equalisation(raw, bounds)


def recalibration_status_for_pairs(
    pairs: int,
    min_pairs: int = DEFAULT_MIN_PAIRS,
) -> str:
    return STATUS_ELIGIBLE if int(pairs) >= int(min_pairs) else STATUS_LOGGED


def build_proposal_payload(
    *,
    pairs: int,
    proposed_shift: Mapping[str, float],
    equalisation: Mapping[str, float],
    min_pairs: int = DEFAULT_MIN_PAIRS,
    max_shift: float = DEFAULT_MAX_SHIFT,
    eq_bounds: Sequence[float] = DEFAULT_EQ_BOUNDS,
    evidence: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    clipped = clip_proposed_shift(proposed_shift, max_shift)
    eq = clamp_equalisation(equalisation, eq_bounds)
    status = recalibration_status_for_pairs(pairs, min_pairs)
    return {
        "pairs": int(pairs),
        "min_pairs": int(min_pairs),
        "proposed_shift": clipped,
        "equalisation": eq,
        "status": status,
        "eligible_to_apply": status == STATUS_ELIGIBLE,
        "auto_applied": False,
        "evidence": evidence or {},
    }
