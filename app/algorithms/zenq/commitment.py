"""Commitment multiplier (C) for ZEQ — pledge proxy + tenure."""

from __future__ import annotations


def compute_commitment_factor(
    *,
    spend_inr: float = 0.0,
    months_active: float = 0.0,
    annual_pledge_inr: float = 0.0,
) -> float:
    """
    PDF commitment: financial pledge + months active.
    Uses marketplace spend as pledge proxy until per-member contribution tracking ships.
    """
    pledge_basis = max(float(spend_inr or 0.0), float(annual_pledge_inr or 0.0))
    pledge_boost = min(0.12, pledge_basis / 500_000.0)
    tenure_boost = min(0.08, max(0.0, float(months_active or 0.0)) / 24.0 * 0.08)
    return round(1.0 + pledge_boost + tenure_boost, 3)
