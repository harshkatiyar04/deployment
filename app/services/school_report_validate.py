"""Validate quarterly report payloads before save (reject out-of-range values)."""

from __future__ import annotations

from typing import Any


def _check_pct(value: float, field: str) -> None:
    if value < 0 or value > 100:
        raise ValueError(f"{field} must be between 0 and 100.")


def _check_bloom_sel(value: float, field: str) -> None:
    if value < 0 or value > 5:
        raise ValueError(f"{field} must be between 0 and 5.")


def validate_quarterly_payload(payload: dict[str, Any], *, partial: bool = False) -> dict[str, Any]:
    """
    Validate report payload before save.

    partial=True for marks-only PDF imports: attendance/Bloom's/SEL optional;
    at least one subject score and narrative required.
    """
    quarter = (payload.get("quarter") or "").upper()
    if quarter not in ("Q1", "Q2", "Q3", "Q4"):
        raise ValueError("Quarter must be Q1, Q2, Q3, or Q4.")

    risk = payload.get("risk_level") or "Low"
    if risk not in ("Low", "Medium", "High"):
        raise ValueError("Risk level must be Low, Medium, or High.")

    subj = payload.get("subject_scores") or {}
    present_subjects = []
    for key in ("maths", "science", "english", "social", "hindi"):
        val = subj.get(key)
        if val is None or val == "":
            if not partial:
                raise ValueError(f"subject_scores.{key} is required")
            continue
        _check_pct(float(val), key)
        present_subjects.append(key)

    sk = subj.get("sanskrit")
    if sk is not None and sk != "":
        _check_pct(float(sk), "sanskrit")
        present_subjects.append("sanskrit")

    if partial and not present_subjects:
        raise ValueError("At least one subject score is required from the PDF.")

    if not partial:
        if payload.get("attendance_pct") is None:
            raise ValueError("attendance_pct is required")
        _check_pct(float(payload["attendance_pct"]), "attendance_pct")
        if payload.get("avg_score") is None:
            raise ValueError("avg_score is required")
        _check_pct(float(payload["avg_score"]), "avg_score")
    else:
        ap = payload.get("attendance_pct")
        if ap is not None and ap != "":
            _check_pct(float(ap), "attendance_pct")
        av = payload.get("avg_score")
        if av is not None and av != "":
            _check_pct(float(av), "avg_score")

    blooms = payload.get("blooms")
    if blooms is not None and isinstance(blooms, dict) and blooms:
        for key in ("remember", "understand", "apply", "analyse", "evaluate", "create"):
            if key in blooms and blooms[key] is not None:
                _check_bloom_sel(float(blooms[key]), f"blooms.{key}")
    elif not partial:
        raise ValueError("blooms assessment is required")

    sel = payload.get("sel")
    if sel is not None and isinstance(sel, dict) and sel:
        for key in (
            "self_awareness",
            "self_management",
            "social_awareness",
            "relationship_skills",
            "responsible_decisions",
        ):
            if key in sel and sel[key] is not None:
                _check_bloom_sel(float(sel[key]), f"sel.{key}")
    elif not partial:
        raise ValueError("sel assessment is required")

    narrative = (payload.get("narrative") or "").strip()
    if not narrative:
        raise ValueError("narrative is required")

    return payload
