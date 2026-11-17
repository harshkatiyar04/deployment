"""Pipeline status for Admin Lab + health."""

from __future__ import annotations

from typing import Any

from app.algorithms.zenq_v2.params import ALGORITHM_VERSION, LAUNCH_PARAMS
from app.algorithms.zenq_v2.upgrade_dials import UPGRADE_DIALS
from app.core.settings import settings


def zenq_v2_pipeline_status() -> dict[str, Any]:
    flags = LAUNCH_PARAMS.get("flags") or {}
    on = settings.zenq_v2_ledger or settings.zenq_v2_close or settings.zenq_v2_product
    label = "on" if on else "off"
    chat_codes = []
    if flags.get("score_chat_subst"):
        chat_codes.append("SUBST")
    chat_codes.append("ENCOUR")
    if flags.get("score_chat_share"):
        chat_codes.append("SHARE")
    if flags.get("score_chat_react"):
        chat_codes.append("REACT")
    ladder_min = int(LAUNCH_PARAMS.get("ladder_min_circles") or 1)
    awards_min = int(LAUNCH_PARAMS.get("awards_min_circles") or 1)
    pilot_no_seal = bool(LAUNCH_PARAMS.get("pilot_no_seal", True))
    return {
        "v2_algorithm_version": ALGORITHM_VERSION,
        "v2_launch_pipeline": label,
        "v2_launch_pipeline_label": f"v2 design pipeline: {label}",
        "flags": {
            "ZENQ_V2_LEDGER": bool(settings.zenq_v2_ledger),
            "ZENQ_V2_CLOSE": bool(settings.zenq_v2_close),
            "ZENQ_V2_PRODUCT": bool(settings.zenq_v2_product),
        },
        "launch_dials": {
            "g_slope": LAUNCH_PARAMS["g_slope"],
            "agent_apply": LAUNCH_PARAMS["agent_apply"],
            "score_chat_encour_only": not (
                flags.get("score_chat_subst")
                or flags.get("score_chat_share")
                or flags.get("score_chat_react")
            ),
            "score_chat_codes": chat_codes,
            "score_chat_subst": bool(flags.get("score_chat_subst")),
            "score_chat_share": bool(flags.get("score_chat_share")),
            "score_chat_react": bool(flags.get("score_chat_react")),
            "score_kia_effective": bool(flags.get("score_kia_effective")),
            "sponsor_yield": bool(flags.get("sponsor_yield")),
            "csr_tool": bool(flags.get("csr_tool")),
            "growth_evidence_weight": bool(flags.get("growth_evidence_weight")),
            "pilot_no_seal": pilot_no_seal,
            "ladder_min_circles": ladder_min,
            "awards_min_circles": awards_min,
        },
        "recalibration": {
            "min_pairs": int(LAUNCH_PARAMS.get("recalibration_min_pairs") or 200),
            "max_shift": float(LAUNCH_PARAMS.get("recalibration_max_shift") or 0.05),
            "eq_bounds": LAUNCH_PARAMS.get("eq_bounds") or [0.8, 1.25],
            "auto_mutate_weights": False,
            "review_marks_apply_eligible": True,
        },
        "upgrade_dials": UPGRADE_DIALS,
        "pilot_scoring": {
            "walls_from_first_circle": True,
            "walls_from_first_member": True,
            "walls_realtime": True,
            "live_circle_month_snapshot": True,
            "live_pcs_rebuild": True,
            "pilot_no_seal": pilot_no_seal,
            "ladder_min_circles": ladder_min,
            "awards_min_circles": awards_min,
            "ladder_per_bracket": True,
            "surfaces": {
                "chat": "LIVE",
                "session": "LIVE",
                "target": "LIVE",
                "kia_practice_prep": "LIVE",
                "kia_effective": "LIVE",
                "funding": "LIVE",
                "referral": "LIVE",
                "anniversary": "LIVE",
                "spark": "LIVE",
                "partner_engaged": "LIVE",
                "csr": "LIVE",
                "sponsor_yield": "LIVE",
                "ladder": "LIVE",
                "walls": "LIVE",
                "statement": "LIVE",
                "pcs": "LIVE",
            },
            "ops": (
                "Join → chat/session/pledge/Kia → ledger → bump → live circle_month "
                "(closed_at NULL) + rebuild PCS → Lifetime/ranks/CSR. "
                "No Admin Close freeze. Ladder from first scored circle."
            ),
        },
        "realtime": {
            "walls_live": True,
            "admin_close_required_for_walls": False,
            "month_end_auto_seal": False if pilot_no_seal else True,
            "live_snapshot_on_emit": True,
            "chat_llm_on_send": True,
        },
        "note": (
            "Everything live, no base seal. Every emit upserts live circle_month and "
            "rebuilds PCS. Impact score = season ZenQ per member-month. "
            "Admin Close is a no-op under pilot_no_seal."
        ),
    }
