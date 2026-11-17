"""Product vs conservative parameter blobs (Tech Guide §3).

Product = full design dials (post cutover). Conservative launch kept for rollback tests.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

ALGORITHM_VERSION = "2.1.0-design"

BRACKET: dict[str, dict[str, float]] = {
    "A": {"norm": 20, "exp_q": 6, "w_pres": 1.2, "w_learn": 0.9, "w_chat": 1.2, "w_kia": 0.9},
    "B": {"norm": 30, "exp_q": 5, "w_pres": 1.0, "w_learn": 1.0, "w_chat": 1.0, "w_kia": 1.0},
    "C": {"norm": 40, "exp_q": 4, "w_pres": 0.9, "w_learn": 1.2, "w_chat": 0.9, "w_kia": 1.1},
}

K_NEED = {"Standard": 0.90, "Developing": 1.00, "High": 1.15, "Critical": 1.30}

W_BASE = {
    "presence": 30,
    "learning": 25,
    "chat": 10,
    "kia": 10,
    "funding": 10,
    "growth": 10,
    "student": 5,
}

W_BOUNDS = {
    "presence": (15, 45),
    "learning": (10, 40),
    "chat": (3, 20),
    "kia": (3, 20),
    "funding": (3, 20),
    "growth": (3, 30),
    "student": (3, 10),
}

MILESTONES_IP = [0, 5000, 25000, 75000, 150000, 300000]
MILESTONE_NAMES = ["Seed", "Sprout", "Grove", "Canopy", "Forest", "Old Growth"]

_BASE_SCHEDULE: dict[str, Any] = {
    "session_ip": 10,
    "session_bonus": 2,
    "target_ip": {"none": 0, "partial": 5, "full": 10, "stretch": 13},
    "chat_ip": {"SUBST": 1.5, "ENCOUR": 2.5, "SHARE": 2.0, "REACT": 0.25},
    "chat_cap_day": 8,
    "kia_ip": {"PRACTICE": 4, "PREP": 2, "EFFECTIVE": 6},
    "kia_cap_month": 60,
    "fund_ip": 15,
    "fund_ref_inr": 2000,
    "fund_cap_x": 2,
    "referral_ip": 150,
    "anniversary_ip": 50,
    "spark_ip": 60,
    "streak_step": 0.05,
    "streak_max_wk": 10,
    "streak_reset_inactive_weeks": 3,
    "own_x": 1.5,
    "ext_x": 0.5,
    "ext_cap": 0.20,
    "g_slope": 0.6,
    "g_cap": 2.0,
    "g_floor": 1.0,
    "stretch_gr_below": 0.5,
    "stretch_min_assessments": 3,
    "stretch_bonus": 0.15,
    "fade_after": 3,
    "fade_rate": 0.03,
    "listing_months": 4,
    "ret_base_months": 3,
    "ladder_min_circles": 1,
    "awards_min_circles": 1,
    # Pilot: never write closed_at / never freeze months. Re-enable for production seal.
    "pilot_no_seal": True,
    "display_divisor": 1,
    "baseline_method": "MEAN_FIRST_TWO",
    "agent_step": 5,
    "agent_max_shift": 10,
    "agent_cooldown_months": 3,
    "agent_apply": True,
    "agent_thresholds": {
        "chat_share_hi": 0.18,
        "gr_fall": 0.02,
        "ref_window": 3,
        "pres_share_hi": 0.30,
        "fund_share_hi": 0.12,
        "regress_share": 0.25,
        "kia_share_lo": 0.06,
    },
    "recalibration_min_pairs": 200,
    "recalibration_max_shift": 0.05,
    "eq_bounds": [0.8, 1.25],
    "flags": {
        "score_chat_subst": True,
        "score_chat_share": True,
        "score_chat_react": True,
        "score_kia_effective": True,
        "sponsor_yield": True,
        "csr_tool": True,
        "growth_evidence_weight": True,
    },
}


def _params(*, conservative: bool) -> dict[str, Any]:
    p = deepcopy(_BASE_SCHEDULE)
    p["bracket"] = deepcopy(BRACKET)
    p["k_need"] = dict(K_NEED)
    p["w_base"] = dict(W_BASE)
    p["w_bounds"] = {k: list(v) for k, v in W_BOUNDS.items()}
    p["milestones_ip"] = list(MILESTONES_IP)
    if conservative:
        p["g_slope"] = 0.0
        p["agent_apply"] = False
        p["flags"] = {
            "score_chat_subst": False,
            "score_chat_share": False,
            "score_chat_react": False,
            "score_kia_effective": False,
            "sponsor_yield": False,
            "csr_tool": False,
            "growth_evidence_weight": False,
        }
    return p


# Product defaults = full design dials (fully live).
LAUNCH_PARAMS: dict[str, Any] = _params(conservative=False)
DESIGN_PARAMS: dict[str, Any] = LAUNCH_PARAMS
# Rollback / historical launch gates (tests that document pre-cutover behaviour).
CONSERVATIVE_LAUNCH_PARAMS: dict[str, Any] = _params(conservative=True)
