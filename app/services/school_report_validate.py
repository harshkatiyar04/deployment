"""Validate quarterly report payloads before save (reject out-of-range values)."""

from __future__ import annotations

from typing import Any


def _check_pct(value: float, field: str) -> None:
    if value < 0 or value > 100:
        raise ValueError(f"{field} must be between 0 and 100.")


def _check_bloom_sel(value: float, field: str) -> None:
    if value < 0 or value > 5:
        raise ValueError(f"{field} must be between 0 and 5.")


def validate_quarterly_payload(payload: dict[str, Any]) -> dict[str, Any]:
    quarter = (payload.get("quarter") or "").upper()
    if quarter not in ("Q1", "Q2", "Q3", "Q4"):
        raise ValueError("Quarter must be Q1, Q2, Q3, or Q4.")

    risk = payload.get("risk_level") or "Low"
    if risk not in ("Low", "Medium", "High"):
        raise ValueError("Risk level must be Low, Medium, or High.")

    _check_pct(float(payload["attendance_pct"]), "attendance_pct")
    _check_pct(float(payload["avg_score"]), "avg_score")

    subj = payload.get("subject_scores") or {}
    for key in ("maths", "science", "english", "social", "hindi"):
        if key not in subj:
            raise ValueError(f"subject_scores.{key} is required")
        _check_pct(float(subj[key]), key)

    if subj.get("sanskrit") is not None and subj.get("sanskrit") != "":
        _check_pct(float(subj["sanskrit"]), "sanskrit")

    blooms = payload.get("blooms") or {}
    for key in ("remember", "understand", "apply", "analyse", "evaluate", "create"):
        if key not in blooms:
            raise ValueError(f"blooms.{key} is required")
        _check_bloom_sel(float(blooms[key]), f"blooms.{key}")

    sel = payload.get("sel") or {}
    for key in (
        "self_awareness",
        "self_management",
        "social_awareness",
        "relationship_skills",
        "responsible_decisions",
    ):
        if key not in sel:
            raise ValueError(f"sel.{key} is required")
        _check_bloom_sel(float(sel[key]), f"sel.{key}")

    narrative = (payload.get("narrative") or "").strip()
    if not narrative:
        raise ValueError("narrative is required")

    return payload
