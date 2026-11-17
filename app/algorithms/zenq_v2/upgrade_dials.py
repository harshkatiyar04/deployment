"""Historical upgrade dial track — now live in product (2.1.0-design)."""

from __future__ import annotations

UPGRADE_DIALS: list[dict[str, str]] = [
    {
        "id": "chat_subst_share",
        "when": "Classifier agrees with hand labels on ≥85% of 200 labelled messages",
        "change": "flags.score_chat_subst=true; flags.score_chat_share=true; score_chat_react=true",
        "status": "live",
    },
    {
        "id": "kia_effective",
        "when": "Kia computes effective-week reliably for a full quarter",
        "change": "flags.score_kia_effective=true",
        "status": "live",
    },
    {
        "id": "growth_slope",
        "when": "Every child has two assessments beyond baseline",
        "change": "growth.slope=0.6; flags.growth_evidence_weight=true",
        "status": "live",
    },
    {
        "id": "agent_apply",
        "when": "Six monthly agent runs reviewed by the panel look sensible",
        "change": "agent.apply=true",
        "status": "live",
    },
    {
        "id": "sponsor_csr",
        "when": "Comparison group has two assessment cycles",
        "change": "flags.sponsor_yield=true; flags.csr_tool=true",
        "status": "live",
    },
]
