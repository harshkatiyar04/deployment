from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class PrioritySignal:
    student_name: str
    score: int
    urgency: str
    action: str
    reasons: list[str]
    detail: str
    action_required: bool
    type: str = "student_priority"


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def urgency_for_score(score: int) -> str:
    if score >= 80:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 40:
        return "moderate"
    return "watch"


def _action_for_urgency(urgency: str) -> str:
    if urgency == "critical":
        return "Escalate to parent + Sponsor Leader today"
    if urgency == "high":
        return "Schedule parent meeting within 48 hours"
    if urgency == "moderate":
        return "Assign mentor follow-up this week"
    return "Monitor and continue classroom support"


def compute_student_priority(
    *,
    student_name: str,
    attendance_pct: float,
    zqa_score: float,
    zqa_baseline_delta: Optional[float],
    q_report_status: str,
    risk_level: str,
    tutor_recommendation_pending: bool,
) -> PrioritySignal:
    score = 0.0
    reasons: list[str] = []

    if attendance_pct > 0:
        if attendance_pct < 75:
            score += 35
            reasons.append(f"Attendance is low at {attendance_pct:.0f}%")
        elif attendance_pct < 85:
            score += 20
            reasons.append(f"Attendance is below target at {attendance_pct:.0f}%")
        elif attendance_pct < 92:
            score += 10
            reasons.append("Attendance is below the 92% integrity floor")

    if zqa_score <= 0:
        score += 20
        reasons.append("ZQA is not yet published")
    elif zqa_score < 45:
        score += 25
        reasons.append(f"ZQA is low at {zqa_score:.0f}%")
    elif zqa_score < 60:
        score += 15
        reasons.append(f"ZQA needs reinforcement at {zqa_score:.0f}%")

    if zqa_baseline_delta is not None and zqa_baseline_delta < -5:
        score += 15
        reasons.append(f"ZQA dropped by {abs(zqa_baseline_delta):.1f} points vs baseline")

    if q_report_status.lower() != "finalized":
        score += 15
        reasons.append("Quarterly report is not finalized")

    if risk_level == "High":
        score += 25
        reasons.append("Student is marked high risk")
    elif risk_level == "Medium":
        score += 10
        reasons.append("Student is marked medium risk")

    if tutor_recommendation_pending:
        score += 10
        reasons.append("Tutor recommendation is pending action")

    final_score = int(round(_clamp(score, 0.0, 100.0)))
    urgency = urgency_for_score(final_score)
    action = _action_for_urgency(urgency)
    detail = "Kia recommends: " + "; ".join(reasons[:3]) if reasons else "Stable profile."
    return PrioritySignal(
        student_name=student_name,
        score=final_score,
        urgency=urgency,
        action=action,
        reasons=reasons,
        detail=detail,
        action_required=urgency in {"critical", "high", "moderate"},
    )
