"""Aggregate raw platform signals into ZenQ metric snapshots."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from app.algorithms.zenq.commitment import compute_commitment_factor
from app.algorithms.zenq.core import classify_zqa_band
from app.algorithms.zenq.orchestrator import SponsorMetricsSnapshot, StudentContextSnapshot, student_spd_from_zqa

SUBSTANTIVE_MIN_CHARS = 40


def need_band_from_risk(risk_level: str) -> str:
    if risk_level == "High":
        return "critical"
    if risk_level == "Medium":
        return "high"
    return "developing"


def target_status_from_activity(
    message_count: int,
    orders_count: int,
    reviews_count: int,
) -> str:
    score = message_count + orders_count * 3 + reviews_count * 2
    if score >= 25:
        return "full"
    if score >= 8:
        return "partial"
    if score > 0:
        return "partial"
    return "none"


def is_substantive_message(text: Optional[str]) -> bool:
    if not text:
        return False
    cleaned = text.strip()
    if len(cleaned) >= SUBSTANTIVE_MIN_CHARS:
        return True
    if "?" in cleaned and len(cleaned) >= 15:
        return True
    lowered = cleaned.lower()
    keywords = ("because", "help", "plan", "goal", "student", "progress", "thank", "support")
    return any(k in lowered for k in keywords) and len(cleaned) >= 20


def estimate_substantive_count(message_count: int, *, ratio: float = 0.55) -> int:
    if message_count <= 0:
        return 0
    return max(0, min(message_count, int(round(message_count * ratio))))


def activity_to_session_mins(hours: float) -> float:
    return round(max(0.0, hours) * 60.0, 1)


def build_sponsor_metrics(
    *,
    user_id: str,
    activity: dict[str, Any],
    joined_at: Optional[datetime],
    now: Optional[datetime] = None,
    target_status_override: Optional[str] = None,
    months_active: float = 0.0,
    spend_inr: float = 0.0,
    mentor_session_mins: float = 0.0,
    mentor_inspire_count: int = 0,
) -> SponsorMetricsSnapshot:
    now = now or datetime.now(timezone.utc)
    msgs = int(activity.get("messages_count") or 0)
    orders = int(activity.get("orders_count") or 0)
    reviews = int(activity.get("enrollment_reviews_count") or 0)
    hours = float(activity.get("hours") or 0.0)
    streak = int(activity.get("active_days") or 0)
    substantive = int(activity.get("substantive_message_count") or estimate_substantive_count(msgs))
    avg_ras = float(activity.get("avg_ras") or 1.0)

    joined = joined_at
    if joined and joined.tzinfo is None:
        joined = joined.replace(tzinfo=timezone.utc)
    new_user = bool(joined and (now - joined).days <= 7)

    effort = hours + (msgs * 0.15) + (orders * 1.5) + (reviews * 0.75)
    session_mins = activity_to_session_mins(hours) + max(0.0, float(mentor_session_mins))

    target_status = target_status_from_activity(msgs, orders, reviews)
    if target_status_override in {"none", "partial", "full", "stretch"}:
        target_status = target_status_override

    commitment = compute_commitment_factor(
        spend_inr=spend_inr,
        months_active=months_active,
    )

    inspire_active = min(orders, 10) + min(int(mentor_inspire_count), 5)

    return SponsorMetricsSnapshot(
        user_id=user_id,
        session_mins=round(session_mins, 1),
        message_count=msgs,
        substantive_message_count=substantive,
        active_inspire=inspire_active,
        passive_inspire=min(reviews, 8),
        avg_ras=round(_clamp_ras(avg_ras), 3),
        streak_days=streak,
        new_user=new_user,
        spark_active=False,
        target_status=target_status,
        effort_weight=round(effort + mentor_session_mins * 0.02, 3),
        commitment_factor=commitment,
    )


def build_student_context(
    *,
    student_id: str,
    zqa_composite: float,
    baseline_zqa: Optional[float],
    attendance_pct: float,
    risk_level: str,
    spd_override: Optional[float] = None,
) -> StudentContextSnapshot:
    spd = (
        round(float(spd_override), 4)
        if spd_override is not None
        else student_spd_from_zqa(baseline_zqa, zqa_composite)
    )
    return StudentContextSnapshot(
        student_id=student_id,
        zqa_composite=round(float(zqa_composite or 0.0), 2),
        zqa_band=classify_zqa_band(float(zqa_composite or 0.0)),
        baseline_zqa=baseline_zqa,
        spd=spd,
        need_band=need_band_from_risk(risk_level or "Low"),
        attendance_30d=round(float(attendance_pct or 0.0), 1),
    )


def rolling_window_start(days: int = 30, now: Optional[datetime] = None) -> datetime:
    now = now or datetime.now(timezone.utc)
    return now - timedelta(days=days)


def _clamp_ras(value: float) -> float:
    return max(0.0, min(1.0, float(value)))
