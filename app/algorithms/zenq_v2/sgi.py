"""Student Growth Index — Standalone bands (shown when G slope is 0 at launch)."""

from __future__ import annotations

from typing import Optional

from app.algorithms.zenq_v2.params import BRACKET


def compute_sgi(
    *,
    baseline: Optional[float],
    latest: Optional[float],
    n_assessments: int,
    bracket: str = "B",
    attendance_rate: Optional[float] = None,
    sparks_given: float = 0.0,
) -> tuple[Optional[float], str]:
    """Return (sgi_value, band).

    Standalone: SGI = (latest−baseline)×(10/exp_q) + attendance term + 5×sparks.
    Attendance/sparks default off until data exists (Phase 2).
    Bands: Baseline set | Needs support | Steady | Growing | Thriving
    """
    if n_assessments < 3 or baseline is None or latest is None:
        return None, "Baseline set"

    exp_q = float(BRACKET.get(bracket, BRACKET["B"])["exp_q"])
    sgi = (float(latest) - float(baseline)) * (10.0 / exp_q)
    if attendance_rate is not None:
        sgi += 40.0 * (float(attendance_rate) - 0.75)
    sgi += 5.0 * float(sparks_given)

    if sgi < 0:
        band = "Needs support"
    elif sgi < 15:
        band = "Steady"
    elif sgi < 35:
        band = "Growing"
    else:
        band = "Thriving"
    return float(sgi), band


def sgi_from_growth_ratio(gr: Optional[float]) -> tuple[Optional[float], str]:
    """Backward-compatible helper used by older callers."""
    if gr is None:
        return None, "Baseline set"
    # Map GR roughly into Standalone-style bands for display-only fallbacks.
    if gr < 0:
        return float(gr), "Needs support"
    if gr < 0.5:
        return float(gr), "Steady"
    if gr < 1.0:
        return float(gr), "Growing"
    return float(gr), "Thriving"
