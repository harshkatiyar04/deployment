"""Admin ZenQ observatory queries (read-only + backfill trigger)."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import settings
from app.algorithms.zenq.constants import ALGORITHM_VERSION
from app.chat.models import SponsorCircle
from app.models.zenq import (
    ZenqCircleScore,
    ZenqComputationSnapshot,
    ZenqSponsorMetrics,
    ZenqSponsorScore,
    ZenqStudentContext,
    ZenqEvent,
    ZenqWelfareCase,
    ZenqWeightConfig,
)
from app.services.zenq_backfill import backfill_all_circles
from app.services.zenq_materializer import materialize_circle_by_id

_SPD_NEUTRAL = 1.0
_SPD_EPS = 0.0001


def _is_neutral_spd(value: Optional[float]) -> bool:
    return abs(float(value or _SPD_NEUTRAL) - _SPD_NEUTRAL) < _SPD_EPS


def build_spd_baseline_warning(
    students: list[dict[str, Any]],
    *,
    spd_avg: Optional[float] = None,
) -> Optional[dict[str, Any]]:
    """Warn when every student lacks a ZQA baseline so SPD stays at PDF default 1.00."""
    if not students:
        return None

    without_baseline = sum(1 for s in students if s.get("baseline_zqa") is None)
    neutral_spd = sum(1 for s in students if _is_neutral_spd(s.get("spd")))

    if without_baseline < len(students):
        return None

    avg_neutral = spd_avg is None or _is_neutral_spd(spd_avg)
    if not avg_neutral and neutral_spd < len(students):
        return None

    return {
        "level": "warn",
        "code": "spd_neutral_missing_baselines",
        "title": "SPD stuck at neutral (1.00)",
        "message": (
            f"All {len(students)} sponsored student(s) in this circle have no ZQA baseline on file. "
            "Student Progress (SPD) stays at 1.00 until the school publishes ZQA across two quarters "
            "(baseline + current), then you run a ZenQ backfill."
        ),
        "students_without_baseline": without_baseline,
        "students_neutral_spd": neutral_spd,
        "spd_avg": round(float(spd_avg), 4) if spd_avg is not None else _SPD_NEUTRAL,
        "remediation": (
            "School portal → publish ZQA with prior-quarter baseline for each student, "
            "then ZenQ Lab → Run full backfill."
        ),
    }


async def spd_baseline_platform_summary(db: AsyncSession) -> dict[str, Any]:
    from app.models.school import SchoolZqaSnapshot

    ctx_rows = (await db.execute(select(ZenqStudentContext))).scalars().all()
    by_circle: dict[str, list[ZenqStudentContext]] = {}
    for row in ctx_rows:
        by_circle.setdefault(row.circle_id, []).append(row)

    circles_all_missing_baseline = 0
    students_without_baseline = 0
    for rows in by_circle.values():
        if not rows:
            continue
        missing = sum(1 for r in rows if r.baseline_zqa is None)
        students_without_baseline += missing
        if missing == len(rows):
            circles_all_missing_baseline += 1

    snaps_with_baseline = int(
        (
            await db.execute(
                select(func.count())
                .select_from(SchoolZqaSnapshot)
                .where(SchoolZqaSnapshot.baseline_zqa.isnot(None))
            )
        ).scalar()
        or 0
    )
    circles_neutral_spd = int(
        (
            await db.execute(
                select(func.count())
                .select_from(ZenqCircleScore)
                .where(
                    ZenqCircleScore.student_count > 0,
                    func.abs(ZenqCircleScore.spd_avg - _SPD_NEUTRAL) < _SPD_EPS,
                )
            )
        ).scalar()
        or 0
    )

    platform_warning: Optional[dict[str, Any]] = None
    if circles_all_missing_baseline > 0:
        platform_warning = {
            "level": "warn",
            "code": "spd_neutral_missing_baselines",
            "title": "Student progress (SPD) mostly neutral",
            "message": (
                f"{circles_all_missing_baseline} circle(s) have SPD = 1.00 for every sponsored student "
                f"because no ZQA baselines are on file ({students_without_baseline} student rows affected). "
                "ZIQ is under-weighting real student progress until school ZQA is published with a prior quarter."
            ),
            "circles_affected": circles_all_missing_baseline,
            "students_without_baseline": students_without_baseline,
            "circles_neutral_spd_avg": circles_neutral_spd,
            "school_zqa_snapshots_with_baseline": snaps_with_baseline,
            "remediation": (
                "Publish school ZQA (2+ quarters per student) so baselines exist, then run full backfill."
            ),
        }

    return {
        "students_tracked": len(ctx_rows),
        "students_without_baseline": students_without_baseline,
        "circles_all_students_missing_baseline": circles_all_missing_baseline,
        "circles_neutral_spd_avg": circles_neutral_spd,
        "school_zqa_snapshots_with_baseline": snaps_with_baseline,
        "platform_warning": platform_warning,
    }


async def zenq_engine_status(db: AsyncSession) -> dict[str, Any]:
    circle_count = int(
        (await db.execute(select(func.count(ZenqCircleScore.circle_id)))).scalar() or 0
    )
    snapshot_count = int(
        (await db.execute(select(func.count(ZenqComputationSnapshot.id)))).scalar() or 0
    )
    student_ctx_count = int(
        (await db.execute(select(func.count(ZenqStudentContext.id)))).scalar() or 0
    )
    welfare_open = int(
        (
            await db.execute(
                select(func.count(ZenqWelfareCase.id)).where(ZenqWelfareCase.status == "open")
            )
        ).scalar()
        or 0
    )
    pending_weights = int(
        (
            await db.execute(
                select(func.count(ZenqWeightConfig.id)).where(ZenqWeightConfig.status == "proposed")
            )
        ).scalar()
        or 0
    )
    spd_summary = await spd_baseline_platform_summary(db)
    return {
        "algorithm_version": ALGORITHM_VERSION,
        "engine_enabled_for_product": settings.zenq_engine_enabled,
        "live_scoring_note": (
            "ZenQ is live on sponsor dashboards."
            if settings.zenq_engine_enabled
            else "Set ZENQ_ENGINE_ENABLED=true to show live ZIQ/ZEQ on sponsor dashboards."
        ),
        "live_events_enabled": settings.zenq_live_events,
        "admin_observatory": True,
        "circles_scored": circle_count,
        "snapshots_total": snapshot_count,
        "students_tracked": student_ctx_count,
        "welfare_cases_open": welfare_open,
        "weight_proposals_pending": pending_weights,
        "recalibration_enabled": settings.zenq_recalibration_enabled,
        "ai_ras_enabled": settings.zenq_ai_ras_enabled,
        "ai_ras_provider": "kia" if settings.groq_api_key else None,
        "note": (
            "Phase 5: approve weight proposals in ZenQ Lab before they affect ZEQ. "
            + (
                "Sponsor ZIQ is live (ZENQ_ENGINE_ENABLED=true)."
                if settings.zenq_engine_enabled
                else "Set ZENQ_ENGINE_ENABLED=true for sponsor ZIQ cutover."
            )
        ),
        "spd_diagnostics": spd_summary,
        "spd_baseline_warning": spd_summary.get("platform_warning"),
    }


async def list_zenq_circles(
    db: AsyncSession,
    *,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    total = int((await db.execute(select(func.count(ZenqCircleScore.circle_id)))).scalar() or 0)
    res = await db.execute(
        select(ZenqCircleScore)
        .order_by(ZenqCircleScore.updated_at.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = res.scalars().all()
    return {
        "total": total,
        "items": [_circle_row_to_dict(r) for r in rows],
    }


def _circle_row_to_dict(row: ZenqCircleScore) -> dict[str, Any]:
    return {
        "circle_id": row.circle_id,
        "circle_name": row.circle_name,
        "zeq_avg": row.zeq_avg,
        "zcq": row.zcq,
        "spd_avg": row.spd_avg,
        "ziq": row.ziq,
        "ziq_raw": row.ziq_raw,
        "decay_factor": row.decay_factor,
        "ziq_per_member": row.ziq_per_member,
        "sponsor_count": row.sponsor_count,
        "student_count": row.student_count,
        "algorithm_version": row.algorithm_version,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        "spd_baseline_missing": bool(
            row.student_count and row.student_count > 0 and _is_neutral_spd(row.spd_avg)
        ),
    }


async def get_zenq_circle_detail(db: AsyncSession, circle_id: str) -> Optional[dict[str, Any]]:
    circle_res = await db.execute(select(ZenqCircleScore).where(ZenqCircleScore.circle_id == circle_id))
    circle_row = circle_res.scalar_one_or_none()
    if not circle_row:
        sc = await db.execute(select(SponsorCircle).where(SponsorCircle.id == circle_id))
        if not sc.scalar_one_or_none():
            return None
        return {
            "circle_id": circle_id,
            "scored": False,
            "message": "Circle exists but has not been materialized yet. Run backfill.",
        }

    sponsor_res = await db.execute(
        select(ZenqSponsorScore)
        .where(ZenqSponsorScore.circle_id == circle_id)
        .order_by(ZenqSponsorScore.zeq.desc())
    )
    metrics_res = await db.execute(
        select(ZenqSponsorMetrics).where(
            ZenqSponsorMetrics.circle_id == circle_id,
            ZenqSponsorMetrics.window_key == "30d",
        )
    )
    metrics_by_user = {m.user_id: m for m in metrics_res.scalars().all()}

    sponsors = []
    ras_values: list[float] = []
    for s in sponsor_res.scalars().all():
        m = metrics_by_user.get(s.user_id)
        avg_ras = float(m.avg_ras) if m else None
        if avg_ras is not None:
            ras_values.append(avg_ras)
        sponsors.append(
            {
                "user_id": s.user_id,
                "zeq": s.zeq,
                "components": s.components_json or {},
                "avg_ras": avg_ras,
                "message_count": int(m.message_count) if m else 0,
                "substantive_message_count": int(m.substantive_message_count) if m else 0,
                "target_status": m.target_status if m else None,
                "commitment_factor": float(m.commitment_factor) if m else None,
                "spark_active": bool(m.spark_active) if m else False,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            }
        )

    student_res = await db.execute(
        select(ZenqStudentContext).where(ZenqStudentContext.circle_id == circle_id)
    )
    students = [
        {
            "student_id": st.student_id,
            "zqa_composite": st.zqa_composite,
            "zqa_band": st.zqa_band,
            "baseline_zqa": st.baseline_zqa,
            "spd": st.spd,
            "need_band": st.need_band,
            "attendance_30d": st.attendance_30d,
            "spark_active": st.spark_active,
        }
        for st in student_res.scalars().all()
    ]

    snap_res = await db.execute(
        select(ZenqComputationSnapshot)
        .where(ZenqComputationSnapshot.circle_id == circle_id)
        .order_by(ZenqComputationSnapshot.created_at.desc())
        .limit(5)
    )
    recent_snapshots = [
        {
            "id": snap.id,
            "trigger_source": snap.trigger_source,
            "algorithm_version": snap.algorithm_version,
            "created_at": snap.created_at.isoformat() if snap.created_at else None,
            "outputs": {
                "ziq": (snap.outputs_json or {}).get("ziq"),
                "zeq_avg": (snap.outputs_json or {}).get("zeq_avg"),
                "zcq": (snap.outputs_json or {}).get("zcq"),
                "spd_avg": (snap.outputs_json or {}).get("spd_avg"),
            },
        }
        for snap in snap_res.scalars().all()
    ]

    events_res = await db.execute(
        select(func.count(ZenqEvent.id)).where(
            ZenqEvent.circle_id == circle_id,
            ZenqEvent.event_type == "chat_message",
        )
    )
    chat_events = int(events_res.scalar() or 0)

    spd_warning = build_spd_baseline_warning(
        students,
        spd_avg=float(circle_row.spd_avg) if circle_row.spd_avg is not None else None,
    )

    return {
        "scored": True,
        "circle": _circle_row_to_dict(circle_row),
        "spd_warning": spd_warning,
        "zcq_inputs": (circle_row.summary_json or {}).get("zcq_inputs"),
        "formula": (circle_row.summary_json or {}).get("summary"),
        "ras_summary": {
            "avg_ras_30d": round(sum(ras_values) / len(ras_values), 3) if ras_values else None,
            "sponsors_tracked": len(ras_values),
            "chat_events_total": chat_events,
        },
        "sponsors": sponsors,
        "students": students,
        "recent_snapshots": recent_snapshots,
    }


async def list_zenq_snapshots(
    db: AsyncSession,
    *,
    circle_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    q = select(ZenqComputationSnapshot).order_by(ZenqComputationSnapshot.created_at.desc())
    count_q = select(func.count(ZenqComputationSnapshot.id))
    if circle_id:
        q = q.where(ZenqComputationSnapshot.circle_id == circle_id)
        count_q = count_q.where(ZenqComputationSnapshot.circle_id == circle_id)
    total = int((await db.execute(count_q)).scalar() or 0)
    res = await db.execute(q.offset(offset).limit(limit))
    items = [
        {
            "id": snap.id,
            "scope_type": snap.scope_type,
            "scope_id": snap.scope_id,
            "circle_id": snap.circle_id,
            "trigger_source": snap.trigger_source,
            "algorithm_version": snap.algorithm_version,
            "created_at": snap.created_at.isoformat() if snap.created_at else None,
            "outputs": snap.outputs_json or {},
        }
        for snap in res.scalars().all()
    ]
    return {"total": total, "items": items}


async def run_zenq_backfill(db: AsyncSession) -> dict[str, Any]:
    return await backfill_all_circles(db)


async def run_zenq_recompute_circle(db: AsyncSession, circle_id: str) -> dict[str, Any]:
    result = await materialize_circle_by_id(db, circle_id, trigger_source="admin_recompute")
    if result is None:
        return {"ok": False, "error": "Circle not found"}
    return {"ok": True, "ziq": result.ziq, "zeq_avg": result.zeq_avg, "zcq": result.zcq}
