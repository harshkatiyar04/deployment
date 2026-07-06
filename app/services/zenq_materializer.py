"""Persist ZenQ scores from live platform data (Phase 0 — admin-only materializer)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from dataclasses import asdict
from typing import Optional

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.algorithms.zenq.aggregators import build_sponsor_metrics, build_student_context, rolling_window_start
from app.algorithms.zenq.constants import ALGORITHM_VERSION, DEFAULT_WEIGHTS
from app.algorithms.zenq.core import classify_zqa_band, compute_ziq, compute_ziq_per_member, get_n_eff
from app.algorithms.zenq.decay import apply_zeq_decay, months_since
from app.algorithms.zenq.orchestrator import (
    CircleZenqComputation,
    SponsorMetricsSnapshot,
    computation_to_dict,
    compute_circle_zenq,
)
from app.chat.models import ChatChannel, ChatMessage, CircleMember, GamifiedPersona, SponsorCircle
from app.models.school import SchoolStudent, SchoolZqaSnapshot
from app.models.zenq import (
    ZenqCircleScore,
    ZenqComputationSnapshot,
    ZenqSponsorMetrics,
    ZenqSponsorScore,
    ZenqStudentContext,
    ZenqWeightConfig,
)
from app.services.sponsor_circle_time_impact import batch_member_activity_for_circle
from app.services.zenq_sponsor_enrichment import (
    batch_mentor_session_stats,
    batch_order_spend,
    batch_tenure_months,
    latest_target_status_by_sponsor,
)
from app.services.zenq_spark import active_spark_student_ids

logger = logging.getLogger(__name__)

# Circle roles that earn personal ZEQ and trigger live recompute on chat.
ZENQ_SCORING_ROLES = frozenset(
    {"sponsor", "sponsor_member", "lead", "sponsor_leader", "mentor"}
)
SPONSOR_ROLES = ZENQ_SCORING_ROLES


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def _load_active_weights(db: AsyncSession) -> dict[str, float]:
    res = await db.execute(
        select(ZenqWeightConfig)
        .where(ZenqWeightConfig.status == "active")
        .order_by(ZenqWeightConfig.created_at.desc())
        .limit(1)
    )
    row = res.scalar_one_or_none()
    if row and row.weights_json:
        return {str(k): float(v) for k, v in row.weights_json.items()}
    return dict(DEFAULT_WEIGHTS)


async def _batch_active_days(
    db: AsyncSession,
    circle_id: str,
    user_ids: list[str],
    since: datetime,
) -> dict[str, int]:
    if not user_ids:
        return {}
    since_naive = since.replace(tzinfo=None) if since.tzinfo else since
    res = await db.execute(
        select(
            GamifiedPersona.user_id,
            func.count(func.distinct(func.date(ChatMessage.created_at))),
        )
        .select_from(ChatMessage)
        .join(ChatChannel, ChatChannel.id == ChatMessage.channel_id)
        .join(GamifiedPersona, GamifiedPersona.id == ChatMessage.gamified_persona_id)
        .where(
            ChatChannel.circle_id == circle_id,
            GamifiedPersona.user_id.in_(user_ids),
            ChatMessage.created_at >= since_naive,
            ChatMessage.hidden_at.is_(None),
            ChatMessage.deleted_at.is_(None),
        )
        .group_by(GamifiedPersona.user_id)
    )
    return {uid: int(cnt) for uid, cnt in res.all()}


async def _batch_message_quality_stats(
    db: AsyncSession,
    circle_id: str,
    user_ids: list[str],
    since: datetime,
) -> dict[str, dict[str, float | int]]:
    """Per-sponsor message counts, substantive counts, and avg RAS (30d window)."""
    if not user_ids:
        return {}

    since_naive = since.replace(tzinfo=None) if since.tzinfo else since
    res = await db.execute(
        select(
            GamifiedPersona.user_id,
            func.count(ChatMessage.id),
            func.coalesce(
                func.sum(case((ChatMessage.zenq_substantive.is_(True), 1), else_=0)),
                0,
            ),
            func.avg(ChatMessage.ras_score),
        )
        .select_from(ChatMessage)
        .join(ChatChannel, ChatChannel.id == ChatMessage.channel_id)
        .join(GamifiedPersona, GamifiedPersona.id == ChatMessage.gamified_persona_id)
        .where(
            ChatChannel.circle_id == circle_id,
            GamifiedPersona.user_id.in_(user_ids),
            ChatMessage.created_at >= since_naive,
            ChatMessage.hidden_at.is_(None),
            ChatMessage.deleted_at.is_(None),
            ChatMessage.content_text.isnot(None),
            func.length(func.trim(ChatMessage.content_text)) > 0,
        )
        .group_by(GamifiedPersona.user_id)
    )
    out: dict[str, dict[str, float | int]] = {}
    for uid, msg_count, sub_count, avg_ras in res.all():
        out[uid] = {
            "message_count": int(msg_count or 0),
            "substantive_message_count": int(sub_count or 0),
            "avg_ras": round(float(avg_ras), 3) if avg_ras is not None else 1.0,
        }
    return out


async def _latest_zqa_by_student(
    db: AsyncSession,
    student_ids: list[str],
) -> dict[str, SchoolZqaSnapshot]:
    if not student_ids:
        return {}
    res = await db.execute(
        select(SchoolZqaSnapshot)
        .where(SchoolZqaSnapshot.student_id.in_(student_ids))
        .order_by(SchoolZqaSnapshot.computed_at.desc())
    )
    out: dict[str, SchoolZqaSnapshot] = {}
    for snap in res.scalars().all():
        if snap.student_id not in out:
            out[snap.student_id] = snap
    return out


async def _circle_last_activity_at(
    db: AsyncSession,
    circle_id: str,
) -> Optional[datetime]:
    since = rolling_window_start(90)
    since_naive = since.replace(tzinfo=None) if since.tzinfo else since
    msg_res = await db.execute(
        select(func.max(ChatMessage.created_at))
        .select_from(ChatMessage)
        .join(ChatChannel, ChatChannel.id == ChatMessage.channel_id)
        .where(
            ChatChannel.circle_id == circle_id,
            ChatMessage.created_at >= since_naive,
            ChatMessage.hidden_at.is_(None),
            ChatMessage.deleted_at.is_(None),
        )
    )
    last_msg = msg_res.scalar_one_or_none()
    if last_msg:
        if last_msg.tzinfo is None:
            return last_msg.replace(tzinfo=timezone.utc)
        return last_msg

    metrics_res = await db.execute(
        select(func.max(ZenqSponsorMetrics.updated_at)).where(
            ZenqSponsorMetrics.circle_id == circle_id,
            ZenqSponsorMetrics.message_count > 0,
        )
    )
    last_metrics = metrics_res.scalar_one_or_none()
    if last_metrics:
        if last_metrics.tzinfo is None:
            return last_metrics.replace(tzinfo=timezone.utc)
        return last_metrics
    return None


def _apply_circle_decay(computation: CircleZenqComputation, months_inactive: int) -> tuple[float, float]:
    """Apply inactivity decay to ZEQ/ZIQ; return (ziq_raw, decay_factor)."""
    ziq_raw = computation.ziq
    if months_inactive <= 2:
        return ziq_raw, 1.0

    decayed_zeq, decay_factor = apply_zeq_decay(computation.zeq_avg, months_inactive)
    computation.zeq_avg = decayed_zeq
    computation.ziq = round(
        compute_ziq(zeq=decayed_zeq, zcq=computation.zcq, spd=computation.spd_avg),
        2,
    )
    n_eff = get_n_eff(computation.group_size)
    computation.ziq_per_member = round(
        compute_ziq_per_member(ziq=computation.ziq, n_eff=n_eff),
        2,
    )
    for breakdown in computation.sponsor_breakdowns:
        breakdown.zeq, _ = apply_zeq_decay(breakdown.zeq, months_inactive)
    computation.summary = {
        **(computation.summary or {}),
        "decay_months_inactive": months_inactive,
        "decay_factor": decay_factor,
        "ziq_raw": ziq_raw,
    }
    return ziq_raw, decay_factor


async def _gather_circle_inputs(
    db: AsyncSession,
    circle: SponsorCircle,
) -> tuple[list, list]:
    member_res = await db.execute(
        select(CircleMember).where(CircleMember.circle_id == circle.id)
    )
    members = member_res.scalars().all()
    sponsors = [m for m in members if (m.role or "").lower() in SPONSOR_ROLES or m.role == "lead"]
    sponsor_ids = [m.user_id for m in sponsors]
    joined_by_user = {m.user_id: m.joined_at for m in sponsors}

    since = rolling_window_start(30)
    activity_by_user = await batch_member_activity_for_circle(db, circle, sponsor_ids, since)
    active_days = await _batch_active_days(db, circle.id, sponsor_ids, since)
    quality_by_user = await _batch_message_quality_stats(db, circle.id, sponsor_ids, since)
    mentor_stats = await batch_mentor_session_stats(db, sponsor_ids, since)
    spend_by_user = await batch_order_spend(db, circle, sponsor_ids, since)
    tenure_by_user = batch_tenure_months(joined_by_user)
    targets_by_user = await latest_target_status_by_sponsor(db, circle.id, sponsor_ids)
    spark_students = await active_spark_student_ids(db, circle.id)
    circle_spark = bool(spark_students)

    sponsor_metrics = []
    for uid in sponsor_ids:
        activity = dict(activity_by_user.get(uid) or {})
        activity["active_days"] = active_days.get(uid, 0)
        q = quality_by_user.get(uid) or {}
        if q:
            activity["messages_count"] = q.get("message_count", activity.get("messages_count", 0))
            activity["substantive_message_count"] = q.get(
                "substantive_message_count",
                activity.get("substantive_message_count", 0),
            )
            activity["avg_ras"] = q.get("avg_ras", 1.0)
        mentor = mentor_stats.get(uid) or {}
        target = targets_by_user.get(uid) or {}
        snap = build_sponsor_metrics(
            user_id=uid,
            activity=activity,
            joined_at=joined_by_user.get(uid),
            target_status_override=target.get("target_status"),
            months_active=tenure_by_user.get(uid, 0.0),
            spend_inr=spend_by_user.get(uid, 0.0),
            mentor_session_mins=float(mentor.get("mentor_session_mins") or 0.0),
            mentor_inspire_count=int(mentor.get("mentor_inspire_count") or 0),
        )
        snap.spark_active = circle_spark
        sponsor_metrics.append(snap)

    student_res = await db.execute(
        select(SchoolStudent).where(SchoolStudent.circle_id == circle.id)
    )
    students = student_res.scalars().all()
    snap_by_id = await _latest_zqa_by_student(db, [s.id for s in students])

    student_contexts = []
    for st in students:
        snap = snap_by_id.get(st.id)
        if snap:
            zqa = float(snap.zqa_composite or 0.0)
            baseline = snap.baseline_zqa
            spd_override = float(snap.spd) if snap.spd is not None else None
            zqa_band = snap.zqa_band or classify_zqa_band(zqa)
        else:
            zqa = float(st.zqa_score or 0.0)
            baseline = None
            spd_override = None
            zqa_band = None
            if st.zqa_baseline_delta is not None and zqa:
                baseline = max(0.0, zqa - float(st.zqa_baseline_delta or 0))
        ctx = build_student_context(
            student_id=st.id,
            zqa_composite=zqa,
            baseline_zqa=baseline,
            attendance_pct=float(st.attendance_pct or 0.0),
            risk_level=st.risk_level or "Low",
            spd_override=spd_override,
        )
        if zqa_band:
            ctx.zqa_band = zqa_band
        student_contexts.append(ctx)

    return sponsor_metrics, student_contexts, spark_students


async def _upsert_metrics_and_scores(
    db: AsyncSession,
    computation: CircleZenqComputation,
    sponsor_metrics: list[SponsorMetricsSnapshot],
    *,
    trigger_source: str,
    spark_students: Optional[set[str]] = None,
    ziq_raw: Optional[float] = None,
    decay_factor: float = 1.0,
) -> None:
    now = _utcnow()
    metrics_by_user = {m.user_id: m for m in sponsor_metrics}

    for breakdown in computation.sponsor_breakdowns:
        raw = metrics_by_user.get(breakdown.user_id)
        existing_res = await db.execute(
            select(ZenqSponsorMetrics).where(
                ZenqSponsorMetrics.circle_id == computation.circle_id,
                ZenqSponsorMetrics.user_id == breakdown.user_id,
                ZenqSponsorMetrics.window_key == "30d",
            )
        )
        metrics_row = existing_res.scalar_one_or_none()
        if metrics_row is None:
            metrics_row = ZenqSponsorMetrics(
                circle_id=computation.circle_id,
                user_id=breakdown.user_id,
                window_key="30d",
            )
            db.add(metrics_row)
        if raw:
            metrics_row.session_mins = raw.session_mins
            metrics_row.message_count = raw.message_count
            metrics_row.substantive_message_count = raw.substantive_message_count
            metrics_row.streak_days = raw.streak_days
            metrics_row.target_status = raw.target_status
            metrics_row.effort_weight = raw.effort_weight
            metrics_row.avg_ras = raw.avg_ras
            metrics_row.commitment_factor = raw.commitment_factor
            metrics_row.spark_active = raw.spark_active
        metrics_row.updated_at = now

        score_res = await db.execute(
            select(ZenqSponsorScore).where(
                ZenqSponsorScore.circle_id == computation.circle_id,
                ZenqSponsorScore.user_id == breakdown.user_id,
            )
        )
        score_row = score_res.scalar_one_or_none()
        if score_row is None:
            score_row = ZenqSponsorScore(
                circle_id=computation.circle_id,
                user_id=breakdown.user_id,
            )
            db.add(score_row)
        score_row.zeq = breakdown.zeq
        score_row.components_json = breakdown.components
        score_row.updated_at = now

    for st in computation.student_contexts:
        ctx_res = await db.execute(
            select(ZenqStudentContext).where(ZenqStudentContext.student_id == st.student_id)
        )
        ctx_row = ctx_res.scalar_one_or_none()
        if ctx_row is None:
            ctx_row = ZenqStudentContext(student_id=st.student_id)
            db.add(ctx_row)
        ctx_row.circle_id = computation.circle_id
        ctx_row.zqa_composite = st.zqa_composite
        ctx_row.zqa_band = st.zqa_band
        ctx_row.baseline_zqa = st.baseline_zqa
        ctx_row.spd = st.spd
        ctx_row.need_band = st.need_band
        ctx_row.attendance_30d = st.attendance_30d
        ctx_row.spark_active = bool(spark_students and st.student_id in spark_students)
        ctx_row.updated_at = now

    circle_res = await db.execute(
        select(ZenqCircleScore).where(ZenqCircleScore.circle_id == computation.circle_id)
    )
    circle_row = circle_res.scalar_one_or_none()
    if circle_row is None:
        circle_row = ZenqCircleScore(circle_id=computation.circle_id)
        db.add(circle_row)
    circle_row.circle_name = computation.circle_name
    circle_row.zeq_avg = computation.zeq_avg
    circle_row.zcq = computation.zcq
    circle_row.spd_avg = computation.spd_avg
    circle_row.ziq = computation.ziq
    circle_row.ziq_raw = ziq_raw if ziq_raw is not None else computation.ziq
    circle_row.decay_factor = decay_factor
    circle_row.ziq_per_member = computation.ziq_per_member
    circle_row.sponsor_count = computation.sponsor_count
    circle_row.student_count = computation.student_count
    circle_row.algorithm_version = computation.algorithm_version
    circle_row.summary_json = {
        "zcq_inputs": computation.zcq_inputs,
        "summary": computation.summary,
    }
    circle_row.updated_at = now

    snapshot = ZenqComputationSnapshot(
        scope_type="circle",
        scope_id=computation.circle_id,
        circle_id=computation.circle_id,
        algorithm_version=ALGORITHM_VERSION,
        trigger_source=trigger_source,
        inputs_json={
            "sponsors": [asdict(m) for m in sponsor_metrics],
            "students": [asdict(st) for st in computation.student_contexts],
            "zcq_inputs": computation.zcq_inputs,
        },
        outputs_json=computation_to_dict(computation),
    )
    db.add(snapshot)


async def materialize_circle(
    db: AsyncSession,
    circle: SponsorCircle,
    *,
    trigger_source: str = "materializer",
    commit: bool = True,
) -> CircleZenqComputation:
    weights = await _load_active_weights(db)
    sponsor_metrics, student_contexts, spark_students = await _gather_circle_inputs(db, circle)
    computation = compute_circle_zenq(
        circle_id=circle.id,
        circle_name=circle.name,
        sponsor_metrics=sponsor_metrics,
        students=student_contexts,
        weights=weights,
    )
    last_activity = await _circle_last_activity_at(db, circle.id)
    months_inactive = months_since(last_activity)
    ziq_raw, decay_factor = _apply_circle_decay(computation, months_inactive)
    await _upsert_metrics_and_scores(
        db,
        computation,
        sponsor_metrics,
        trigger_source=trigger_source,
        spark_students=spark_students,
        ziq_raw=ziq_raw,
        decay_factor=decay_factor,
    )
    if commit:
        await db.commit()
    return computation


async def materialize_circle_by_id(
    db: AsyncSession,
    circle_id: str,
    *,
    trigger_source: str = "materializer",
) -> Optional[CircleZenqComputation]:
    res = await db.execute(select(SponsorCircle).where(SponsorCircle.id == circle_id))
    circle = res.scalar_one_or_none()
    if not circle:
        return None
    return await materialize_circle(db, circle, trigger_source=trigger_source)
