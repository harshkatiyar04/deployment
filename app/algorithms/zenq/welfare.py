"""Welfare escalation levels from engagement and safety signals (Phase 4)."""

from __future__ import annotations

from typing import Any


def evaluate_welfare_level(signals: dict[str, Any]) -> tuple[int, list[str]]:
    """
    Returns (level, issues). Level 0 = clear, 1 = watch, 2 = escalate, 3 = urgent.
    Not score-based — engagement and safety signals only.
    """
    issues: list[str] = []

    if signals.get("sos_open"):
        issues.append("sos_report_open")
        return 3, issues

    silent = int(signals.get("max_sponsor_silence_days") or 0)
    critical_need = bool(signals.get("critical_need"))

    if silent >= 28:
        issues.append("sponsor_silence_28d")
        return 3 if critical_need else 2, issues

    if bool(signals.get("attendance_below_80")):
        issues.append("attendance_below_80")
        return 2, issues

    if silent >= 14:
        issues.append("sponsor_silence_14d")
        return 1, issues

    if bool(signals.get("no_student_zqa_2q")):
        issues.append("missing_zqa_two_quarters")
        return 1, issues

    return 0, issues


def welfare_level_label(level: int) -> str:
    return {
        0: "clear",
        1: "watch",
        2: "escalate",
        3: "urgent",
    }.get(int(level), "unknown")
