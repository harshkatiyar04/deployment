"""Monthly circle earnings E — Tech Guide close_circles / board O.3."""

from __future__ import annotations

from typing import Any, Optional

from app.algorithms.zenq_v2.growth import G, wmult
from app.algorithms.zenq_v2.params import K_NEED, LAUNCH_PARAMS, W_BASE


def circle_month_earnings(
    pts: dict[str, float],
    partner_ip_raw: float,
    growth_raw: float,
    spark_ip: float,
    need: str,
    gr: Optional[float],
    weights: Optional[dict[str, float]] = None,
    nu: float = 1.0,
    stretch: bool = False,
    params: Optional[dict[str, Any]] = None,
) -> float:
    """pts: unweighted class points {presence, learning, chat, kia, funding}."""
    p = params or LAUNCH_PARAMS
    w = weights or dict(W_BASE)
    prem = 1.0 + (float(p["stretch_bonus"]) if stretch else 0.0)
    member_ip = (float(pts.get("presence", 0)) * wmult(w, "presence") + float(pts.get("learning", 0)) * wmult(w, "learning")) * prem
    member_ip += float(pts.get("chat", 0)) * wmult(w, "chat")
    member_ip += float(pts.get("kia", 0)) * wmult(w, "kia")
    member_ip += float(pts.get("funding", 0)) * wmult(w, "funding")
    partner_ip = min(float(partner_ip_raw), float(p["ext_cap"]) * member_ip)
    raw = member_ip + partner_ip + float(growth_raw) * wmult(w, "growth") + float(spark_ip)
    k = float(K_NEED.get(need, 1.0))
    return max(0.0, raw * k * G(gr, w, p)) * float(nu)


def impact_return(earnings_hist: list[float], tenure_months: int, params: Optional[dict[str, Any]] = None) -> Optional[float]:
    p = params or LAUNCH_PARAMS
    listing = int(p["listing_months"])
    base_n = int(p["ret_base_months"])
    if tenure_months < listing or len(earnings_hist) < base_n + 1:
        return None
    base = sum(earnings_hist[-(base_n + 1) : -1]) / base_n
    if base == 0:
        return None
    return earnings_hist[-1] / base - 1.0


def yield_per_lakh(lifetime_ip: float, contribution_inr: float, params: Optional[dict[str, Any]] = None) -> float:
    p = params or LAUNCH_PARAMS
    div = float(p["display_divisor"])
    if contribution_inr <= 0:
        return 0.0
    return (lifetime_ip / div) / (contribution_inr / 1e5)


def milestone_name(lifetime_ip: float, params: Optional[dict[str, Any]] = None) -> str:
    from app.algorithms.zenq_v2.params import MILESTONE_NAMES, MILESTONES_IP

    name = MILESTONE_NAMES[0]
    for thr, nm in zip(MILESTONES_IP, MILESTONE_NAMES):
        if lifetime_ip >= thr:
            name = nm
    return name
