"""Orchestrate ZQA v2 computation from DB records + persist audit snapshots."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.algorithms.zenq.core import (
    compute_a,
    compute_comm_index,
    compute_inspire_index,
    compute_s,
    compute_t,
    compute_zcq,
    compute_zeq,
    compute_ziq,
    compute_ziq_per_member,
    get_k,
    get_k_att,
    get_n_eff,
)
from app.algorithms.zenq.zqa import ZqaComputationResult, compute_zqa_result
from app.algorithms.zenq.zqa_policy import format_publish_blockers, publish_blocking_issues
from app.models.school import (
    SchoolAttendance,
    SchoolStudent,
    SchoolStudentBloomsAssessment,
    SchoolStudentNarrative,
    SchoolStudentSEL,
    SchoolStudentSubjectScore,
    SchoolZqaSnapshot,
)


QUARTER_MONTHS: dict[str, tuple[int, ...]] = {
    "Q1": (4, 5, 6),
    "Q2": (7, 8, 9),
    "Q3": (10, 11, 12),
    "Q4": (1, 2, 3),
}


def _fy_start_year(fy: str) -> int:
    return int(str(fy).split("-")[0])


def _month_calendar_year(fy: str, quarter: str, month: int) -> int:
    start = _fy_start_year(fy)
    if quarter.upper() == "Q4" and month <= 3:
        return start + 1
    return start


async def quarter_attendance_from_grid(
    db: AsyncSession,
    student_id: str,
    quarter: str,
    fy: str,
) -> Optional[float]:
    """Aggregate monthly attendance rows for the report quarter (working-day weighted)."""
    q = quarter.upper()
    months = QUARTER_MONTHS.get(q)
    if not months:
        return None

    res = await db.execute(
        select(SchoolAttendance).where(SchoolAttendance.student_id == student_id)
    )
    rows = res.scalars().all()
    if not rows:
        return None

    wanted = {
        (_month_calendar_year(fy, q, m), m)
        for m in months
    }
    matched = [r for r in rows if (r.year, r.month) in wanted]
    if not matched:
        return None

    total_wd = sum(r.working_days for r in matched)
    total_dp = sum(r.days_present for r in matched)
    if total_wd > 0:
        return round((total_dp / total_wd) * 100, 1)
    return round(sum(r.attendance_pct for r in matched) / len(matched), 1)


async def resolve_attendance_for_zqa(
    db: AsyncSession,
    student: SchoolStudent,
    quarter: str,
    fy: str,
    *,
    report_attendance: Optional[float] = None,
) -> tuple[float, str]:
    grid_pct = await quarter_attendance_from_grid(db, student.id, quarter, fy)
    if grid_pct is not None:
        return grid_pct, "monthly_grid_quarter"
    if report_attendance is not None:
        return float(report_attendance), "report_submission"
    return float(student.attendance_pct), "profile_annual"


def assert_zqa_publishable(
    *,
    subject_scores: dict[str, float],
    blooms: Optional[dict[str, float]],
    sel: Optional[dict[str, float]],
    attendance_pct: float,
    avg_score: Optional[float],
    rank_in_class: Optional[str],
    class_size: Optional[int],
    narrative: Optional[str] = None,
) -> None:
    from app.algorithms.zenq.zqa import validate_zqa_inputs

    issues = validate_zqa_inputs(
        subject_scores=subject_scores,
        blooms=blooms,
        sel=sel,
        attendance_pct=attendance_pct,
        avg_score=avg_score,
        rank_in_class=rank_in_class,
        class_size=class_size,
        finalized=True,
        narrative=narrative,
    )
    blockers = publish_blocking_issues(issues)
    if blockers:
        raise ValueError(format_publish_blockers(blockers))


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(value)))


def _need_band_from_risk(risk_level: str) -> str:
    if risk_level == "High":
        return "critical"
    if risk_level == "Medium":
        return "high"
    return "developing"


def _achievement_status(zqa_composite: float, blooms_score: Optional[float]) -> str:
    cognitive = blooms_score or 0.0
    if zqa_composite >= 85 and cognitive >= 70:
        return "stretch"
    if zqa_composite >= 70:
        return "full"
    if zqa_composite >= 45:
        return "partial"
    return "none"


def compute_school_zenq_contribution(
    *,
    zqa_composite: float,
    blooms_score: Optional[float],
    sel_score: Optional[float],
    attendance_pct: float,
    risk_level: str,
    class_size: Optional[int],
    spd: float,
) -> float:
    attendance_ratio = _clamp(attendance_pct / 100.0, 0.0, 1.0)
    session_mins = max(5.0, attendance_ratio * 45.0)
    t = compute_t(session_mins=session_mins, ras=1.0)
    a = compute_a(_achievement_status(zqa_composite, blooms_score))
    streak_days = max(0, int(round(attendance_ratio * 30.0)))
    s = compute_s(days=streak_days, new_user=False, spark_active=False)

    sel_norm = _clamp((sel_score or 0.0) / 100.0, 0.0, 1.0)
    comm = compute_comm_index(
        message_count=max(0, int(round(sel_norm * 20))),
        substantive_message_count=max(0, int(round(sel_norm * 12))),
        avg_ras=1.0,
    )
    blooms_norm = _clamp((blooms_score or 0.0) / 100.0, 0.0, 1.0)
    inspire = compute_inspire_index(
        active=max(0, int(round(blooms_norm * 8))),
        passive=max(0, int(round(sel_norm * 5))),
    )

    commitment = 1.0 + min(0.15, max(0.0, (zqa_composite - 50.0) / 200.0))
    zeq = compute_zeq(
        t=t,
        a=a,
        s=s,
        comm_index=comm,
        inspire_index=inspire,
        equity=1.0,
        commitment_factor=commitment,
    )

    k = get_k(_need_band_from_risk(risk_level))
    k_att = get_k_att(attendance_ratio, absent_today=False)
    n_eff = get_n_eff(max(1, int(class_size or 1)))
    zcq = compute_zcq(k=k, k_att=k_att, n_eff=n_eff)
    ziq = compute_ziq(zeq=zeq, zcq=zcq, spd=spd)
    return round(compute_ziq_per_member(ziq=ziq, n_eff=n_eff), 2)


def _subject_rows_to_dict(rows: list[SchoolStudentSubjectScore]) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for row in rows:
        slot = out.setdefault(row.quarter.upper(), {})
        key = row.subject.lower()
        if key == "english":
            slot["english"] = float(row.score)
        elif key == "maths":
            slot["maths"] = float(row.score)
        elif key == "science":
            slot["science"] = float(row.score)
        elif key in ("social", "hindi"):
            slot[key] = float(row.score)
        elif key == "science":
            slot["science"] = float(row.score)
    return out


def _blooms_row_to_dict(row: SchoolStudentBloomsAssessment) -> dict[str, float]:
    return {
        "remember": row.remember,
        "understand": row.understand,
        "apply": row.apply,
        "analyse": row.analyse,
        "evaluate": row.evaluate,
        "create": row.create,
    }


def _sel_row_to_dict(row: SchoolStudentSEL) -> dict[str, float]:
    return {
        "self_awareness": row.self_awareness,
        "self_management": row.self_management,
        "social_awareness": row.social_awareness,
        "relationship_skills": row.relationship_skills,
        "responsible_decisions": row.responsible_decisions,
    }


async def _load_quarter_narrative(
    db: AsyncSession, student_id: str, quarter: str
) -> Optional[str]:
    res = await db.execute(
        select(SchoolStudentNarrative).where(
            SchoolStudentNarrative.student_id == student_id,
            SchoolStudentNarrative.quarter == quarter.upper(),
        )
    )
    row = res.scalar_one_or_none()
    if not row or not row.narrative:
        return None
    text = str(row.narrative).strip()
    return text or None


async def load_student_quarter_context(
    db: AsyncSession, student_id: str, quarter: str
) -> tuple[
    dict[str, float],
    Optional[dict[str, float]],
    Optional[dict[str, float]],
    dict[str, dict[str, float]],
    dict[str, dict[str, float]],
    dict[str, dict[str, float]],
]:
    q = quarter.upper()
    scores_res = await db.execute(
        select(SchoolStudentSubjectScore).where(
            SchoolStudentSubjectScore.student_id == student_id
        )
    )
    score_rows = scores_res.scalars().all()
    by_quarter = _subject_rows_to_dict(score_rows)
    subject_scores = by_quarter.get(q, {})

    blooms_res = await db.execute(
        select(SchoolStudentBloomsAssessment).where(
            SchoolStudentBloomsAssessment.student_id == student_id
        )
    )
    blooms_by_q: dict[str, dict[str, float]] = {}
    blooms_current: Optional[dict[str, float]] = None
    for row in blooms_res.scalars().all():
        blooms_by_q[row.quarter.upper()] = _blooms_row_to_dict(row)
        if row.quarter.upper() == q:
            blooms_current = blooms_by_q[q]

    sel_res = await db.execute(
        select(SchoolStudentSEL).where(SchoolStudentSEL.student_id == student_id)
    )
    sel_by_q: dict[str, dict[str, float]] = {}
    sel_current: Optional[dict[str, float]] = None
    for row in sel_res.scalars().all():
        sel_by_q[row.quarter.upper()] = _sel_row_to_dict(row)
        if row.quarter.upper() == q:
            sel_current = sel_by_q[q]

    prior_subjects = {k: v for k, v in by_quarter.items() if k != q}
    return (
        subject_scores,
        blooms_current,
        sel_current,
        prior_subjects,
        blooms_by_q,
        sel_by_q,
    )


async def compute_student_zqa(
    db: AsyncSession,
    student: SchoolStudent,
    quarter: str,
    *,
    subject_scores: Optional[dict[str, float]] = None,
    blooms: Optional[dict[str, float]] = None,
    sel: Optional[dict[str, float]] = None,
    finalized: bool = False,
    fy: str = "2025-26",
    report_attendance: Optional[float] = None,
    narrative: Optional[str] = None,
) -> ZqaComputationResult:
    q = quarter.upper()
    attendance_pct, attendance_source = await resolve_attendance_for_zqa(
        db, student, q, fy, report_attendance=report_attendance
    )
    (
        loaded_subjects,
        loaded_blooms,
        loaded_sel,
        prior_subjects,
        prior_blooms,
        prior_sel,
    ) = await load_student_quarter_context(db, student.id, q)

    scores = subject_scores if subject_scores is not None else loaded_subjects
    blooms_data = blooms if blooms is not None else loaded_blooms
    sel_data = sel if sel is not None else loaded_sel
    narrative_text = narrative
    if narrative_text is None and finalized:
        narrative_text = await _load_quarter_narrative(db, student.id, q)

    result = compute_zqa_result(
        quarter=q,
        subject_scores=scores,
        blooms=blooms_data,
        sel=sel_data,
        attendance_pct=attendance_pct,
        avg_score=student.avg_score,
        rank_in_class=student.rank_in_class,
        class_size=student.class_size,
        finalized=finalized,
        narrative=narrative_text,
        prior_quarter_subjects=prior_subjects,
        prior_quarter_blooms={k: v for k, v in prior_blooms.items() if k != q},
        prior_quarter_sel={k: v for k, v in prior_sel.items() if k != q},
        attendance_source=attendance_source,
    )

    if result.zqa_published:
        blooms_idx = result.blooms.get("index_0_100")
        sel_idx = result.sel.get("index_0_100")
        result.zenq_contribution = compute_school_zenq_contribution(
            zqa_composite=result.zqa_composite,
            blooms_score=float(blooms_idx) if blooms_idx is not None else None,
            sel_score=float(sel_idx) if sel_idx is not None else None,
            attendance_pct=attendance_pct,
            risk_level=student.risk_level,
            class_size=student.class_size,
            spd=result.spd,
        )
    else:
        result.zenq_contribution = None
    return result


async def persist_zqa_snapshot(
    db: AsyncSession,
    *,
    school_id: str,
    student_id: str,
    quarter: str,
    fy: str,
    result: ZqaComputationResult,
) -> SchoolZqaSnapshot:
    q = quarter.upper()
    res = await db.execute(
        select(SchoolZqaSnapshot).where(
            SchoolZqaSnapshot.student_id == student_id,
            SchoolZqaSnapshot.quarter == q,
        )
    )
    row = res.scalar_one_or_none()
    breakdown = result.to_breakdown_dict()
    if row:
        row.zqa_composite = result.zqa_composite
        row.zqa_band = result.zqa_band
        row.spd = result.spd
        row.baseline_zqa = result.baseline_zqa
        row.baseline_quarter = result.baseline_quarter
        row.zqa_baseline_delta = result.zqa_baseline_delta
        row.zenq_contribution = result.zenq_contribution or 0.0
        row.confidence = result.confidence
        row.breakdown_json = breakdown
        row.validation_issues = result.validation_issues
        row.computed_at = datetime.utcnow()
        row.fy = fy
    else:
        row = SchoolZqaSnapshot(
            id=str(uuid.uuid4()),
            school_id=school_id,
            student_id=student_id,
            quarter=q,
            fy=fy,
            zqa_composite=result.zqa_composite,
            zqa_band=result.zqa_band,
            spd=result.spd,
            baseline_zqa=result.baseline_zqa,
            baseline_quarter=result.baseline_quarter,
            zqa_baseline_delta=result.zqa_baseline_delta,
            zenq_contribution=result.zenq_contribution or 0.0,
            confidence=result.confidence,
            breakdown_json=breakdown,
            validation_issues=result.validation_issues,
            computed_at=datetime.utcnow(),
        )
        db.add(row)
    await db.flush()
    return row


async def get_zqa_breakdown(
    db: AsyncSession, student: SchoolStudent, quarter: str
) -> dict[str, Any]:
    q = quarter.upper()
    snap_res = await db.execute(
        select(SchoolZqaSnapshot).where(
            SchoolZqaSnapshot.student_id == student.id,
            SchoolZqaSnapshot.quarter == q,
        )
    )
    snap = snap_res.scalar_one_or_none()
    if snap and snap.breakdown_json:
        payload = dict(snap.breakdown_json)
        payload["student_id"] = student.id
        payload["student_name"] = student.full_name
        payload["student_record_snapshot"] = {
            "avg_score": student.avg_score,
            "attendance_pct": student.attendance_pct,
            "risk_level": student.risk_level,
            "zenq_contribution": student.zenq_contribution,
        }
        payload["from_snapshot"] = True
        return payload

    result = await compute_student_zqa(db, student, q, finalized=False, fy="2025-26")
    payload = result.to_breakdown_dict()
    payload["student_id"] = student.id
    payload["student_name"] = student.full_name
    payload["student_record_snapshot"] = {
        "avg_score": student.avg_score,
        "attendance_pct": student.attendance_pct,
        "risk_level": student.risk_level,
        "zenq_contribution": result.zenq_contribution,
    }
    payload["from_snapshot"] = False
    return payload


async def recompute_and_apply_zqa(
    db: AsyncSession,
    *,
    school_id: str,
    student: SchoolStudent,
    quarter: str,
    fy: str = "2025-26",
    finalized: bool = True,
    subject_scores: Optional[dict[str, float]] = None,
    blooms: Optional[dict[str, float]] = None,
    sel: Optional[dict[str, float]] = None,
    report_attendance: Optional[float] = None,
    narrative: Optional[str] = None,
) -> ZqaComputationResult:
    """Run ZQA v2, persist snapshot; update student row only when published."""
    result = await compute_student_zqa(
        db,
        student,
        quarter,
        subject_scores=subject_scores,
        blooms=blooms,
        sel=sel,
        finalized=finalized,
        fy=fy,
        report_attendance=report_attendance,
        narrative=narrative,
    )
    if result.zqa_published:
        student.zqa_score = result.zqa_composite
        student.zqa_baseline_delta = result.zqa_baseline_delta
        if result.zenq_contribution is not None:
            student.zenq_contribution = result.zenq_contribution
    await persist_zqa_snapshot(
        db,
        school_id=school_id,
        student_id=student.id,
        quarter=quarter,
        fy=fy,
        result=result,
    )
    return result
