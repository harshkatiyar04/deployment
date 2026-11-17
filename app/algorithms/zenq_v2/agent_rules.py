"""Weighting agent R1–R5 — log-only at launch (agent.apply=false)."""

from __future__ import annotations

from typing import Any, Optional, Set

from app.algorithms.zenq_v2.params import LAUNCH_PARAMS, W_BASE, W_BOUNDS


def propose_weight_deltas(
    signals: dict[str, Any],
    params: Optional[dict[str, Any]] = None,
    *,
    blocked_rules: Optional[Set[str]] = None,
) -> tuple[dict[str, float], list[str], str]:
    """Return (deltas by factor, rules_fired, reasoning_text)."""
    p = params or LAUNCH_PARAMS
    thr = p["agent_thresholds"]
    step = float(p["agent_step"])
    max_shift = float(p["agent_max_shift"])
    blocked = blocked_rules or set()
    deltas = {k: 0.0 for k in W_BASE}
    fired: list[str] = []

    chat_share = float(signals.get("chat_share") or 0)
    pres_share = float(signals.get("presence_share") or 0)
    fund_share = float(signals.get("funding_share") or 0)
    kia_share = float(signals.get("kia_share") or 0)
    mean_gr = signals.get("mean_growth_ratio")
    mean_gr_3m = signals.get("mean_growth_ratio_3m")
    regress_share = float(signals.get("regress_share") or 0)
    refs = int(signals.get("referral_activations") or signals.get("refs") or 0)
    # Legacy signal: treat as zero referrals when window has no new circles
    if "referral_activations" not in signals and "refs" not in signals:
        refs = int(signals.get("new_circles_in_window") or 0)

    # R1
    if "R1" not in blocked and (
        chat_share > thr["chat_share_hi"]
        and mean_gr is not None
        and mean_gr_3m is not None
        and float(mean_gr) < float(mean_gr_3m) - thr["gr_fall"]
    ):
        deltas["chat"] -= step
        deltas["learning"] += step / 2
        deltas["presence"] += step / 2
        fired.append("R1")

    # R2 — Tech Guide: presence share high AND no referrals in window
    if "R2" not in blocked and pres_share > thr["pres_share_hi"] and refs == 0:
        deltas["presence"] -= step
        deltas["growth"] += step
        fired.append("R2")

    # R3
    if "R3" not in blocked and fund_share > thr["fund_share_hi"]:
        deltas["funding"] -= step
        deltas["presence"] += step / 2
        deltas["learning"] += step / 2
        fired.append("R3")

    # R4
    if "R4" not in blocked and regress_share >= thr["regress_share"]:
        deltas["chat"] -= step / 2
        deltas["funding"] -= step / 2
        deltas["learning"] += step / 2
        deltas["presence"] += step / 2
        fired.append("R4")

    # R5
    if "R5" not in blocked and kia_share < thr["kia_share_lo"]:
        deltas["presence"] -= step
        deltas["kia"] += step
        fired.append("R5")

    for k in deltas:
        deltas[k] = max(-max_shift, min(max_shift, deltas[k]))

    reasons = []
    if "R1" in fired:
        reasons.append(
            f"R1: chat share {chat_share:.0%} and mean GrowthRatio fell — shift weight from Chat to Learning and Presence"
        )
    if "R2" in fired:
        reasons.append(
            f"R2: presence share {pres_share:.0%} and no referrals in window — shift weight from Presence to Growth"
        )
    if "R3" in fired:
        reasons.append("R3: funding share high — shift weight from Funding to Presence and Learning")
    if "R4" in fired:
        reasons.append("R4: regression spreading — shift toward Learning and Presence")
    if "R5" in fired:
        reasons.append("R5: Kia under-used — shift weight from Presence to Kia")
    if not reasons:
        reasons.append("No change proposed: no rule triggered on last month's data.")

    return deltas, fired, " ".join(reasons)


def apply_deltas(current: dict[str, float], deltas: dict[str, float]) -> dict[str, float]:
    out = {}
    for k, base in W_BASE.items():
        lo, hi = W_BOUNDS[k]
        out[k] = min(hi, max(lo, float(current.get(k, base)) + float(deltas.get(k, 0))))
    total = sum(out.values()) or 1.0
    return {k: v / total * 100.0 for k, v in out.items()}
