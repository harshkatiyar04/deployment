"""Apply quarterly report data from in-app form (manual / future CSV / PDF)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.school import (
    SchoolAttendance,
    SchoolFormSubmission,
    SchoolProfile,
    SchoolReport,
    SchoolStudent,
    SchoolStudentBloomsAssessment,
    SchoolStudentNarrative,
    SchoolStudentSEL,
    SchoolStudentSubjectScore,
)
from app.models.signup import SignupRequest
from app.services.school_zqa_engine import assert_zqa_publishable, recompute_and_apply_zqa

SUBJECT_KEYS = {
    "maths": "Maths",
    "science": "Science",
    "english": "English",
    "social": "Social",
    "hindi": "Hindi",
    "sanskrit": "Sanskrit",
}

def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(value)))


def _derive_avg_score(subject_scores: dict[str, Any]) -> Optional[float]:
    vals = []
    for value in (subject_scores or {}).values():
        if value is None:
            continue
        vals.append(_clamp(float(value), 0, 100))
    if not vals:
        return None
    return round(sum(vals) / len(vals), 2)


async def _upsert_subject_scores(
    db: AsyncSession, student_id: str, quarter: str, scores: dict[str, float]
) -> None:
    for key, label in SUBJECT_KEYS.items():
        if key not in scores or scores[key] is None:
            continue
        score_val = _clamp(scores[key], 0, 100)
        res = await db.execute(
            select(SchoolStudentSubjectScore).where(
                SchoolStudentSubjectScore.student_id == student_id,
                SchoolStudentSubjectScore.quarter == quarter,
                SchoolStudentSubjectScore.subject == label,
            )
        )
        row = res.scalar_one_or_none()
        if row:
            row.score = score_val
        else:
            db.add(
                SchoolStudentSubjectScore(
                    id=str(uuid.uuid4()),
                    student_id=student_id,
                    subject=label,
                    quarter=quarter,
                    score=score_val,
                )
            )


async def _upsert_blooms(
    db: AsyncSession, student_id: str, quarter: str, blooms: dict, assessed_by: str
) -> None:
    res = await db.execute(
        select(SchoolStudentBloomsAssessment).where(
            SchoolStudentBloomsAssessment.student_id == student_id,
            SchoolStudentBloomsAssessment.quarter == quarter,
        )
    )
    row = res.scalar_one_or_none()
    if row:
        row.remember = _clamp(blooms["remember"], 0, 5)
        row.understand = _clamp(blooms["understand"], 0, 5)
        row.apply = _clamp(blooms["apply"], 0, 5)
        row.analyse = _clamp(blooms["analyse"], 0, 5)
        row.evaluate = _clamp(blooms["evaluate"], 0, 5)
        row.create = _clamp(blooms["create"], 0, 5)
        row.assessed_by = assessed_by
    else:
        db.add(
            SchoolStudentBloomsAssessment(
                id=str(uuid.uuid4()),
                student_id=student_id,
                quarter=quarter,
                remember=_clamp(blooms["remember"], 0, 5),
                understand=_clamp(blooms["understand"], 0, 5),
                apply=_clamp(blooms["apply"], 0, 5),
                analyse=_clamp(blooms["analyse"], 0, 5),
                evaluate=_clamp(blooms["evaluate"], 0, 5),
                create=_clamp(blooms["create"], 0, 5),
                assessed_by=assessed_by,
            )
        )


async def _upsert_sel(db: AsyncSession, student_id: str, quarter: str, sel: dict) -> None:
    res = await db.execute(
        select(SchoolStudentSEL).where(
            SchoolStudentSEL.student_id == student_id,
            SchoolStudentSEL.quarter == quarter,
        )
    )
    row = res.scalar_one_or_none()
    fields = {
        "self_awareness": _clamp(sel["self_awareness"], 0, 5),
        "self_management": _clamp(sel["self_management"], 0, 5),
        "social_awareness": _clamp(sel["social_awareness"], 0, 5),
        "relationship_skills": _clamp(sel["relationship_skills"], 0, 5),
        "responsible_decisions": _clamp(sel["responsible_decisions"], 0, 5),
    }
    if row:
        for k, v in fields.items():
            setattr(row, k, v)
    else:
        db.add(
            SchoolStudentSEL(
                id=str(uuid.uuid4()),
                student_id=student_id,
                quarter=quarter,
                **fields,
            )
        )


async def _upsert_narrative(
    db: AsyncSession,
    student_id: str,
    quarter: str,
    narrative: str,
    teacher_name: str,
    finalized: bool,
) -> None:
    res = await db.execute(
        select(SchoolStudentNarrative).where(
            SchoolStudentNarrative.student_id == student_id,
            SchoolStudentNarrative.quarter == quarter,
        )
    )
    row = res.scalar_one_or_none()
    if row:
        row.narrative = narrative
        row.teacher_name = teacher_name
        row.finalized = finalized
    else:
        db.add(
            SchoolStudentNarrative(
                id=str(uuid.uuid4()),
                student_id=student_id,
                quarter=quarter,
                teacher_name=teacher_name,
                narrative=narrative,
                finalized=finalized,
            )
        )


async def _upsert_school_report(
    db: AsyncSession,
    school_id: str,
    student_id: str,
    quarter: str,
    fy: str,
    *,
    submitted: bool,
    narrative: str,
) -> SchoolReport:
    res = await db.execute(
        select(SchoolReport).where(
            SchoolReport.school_id == school_id,
            SchoolReport.student_id == student_id,
            SchoolReport.quarter == quarter,
        )
    )
    report = res.scalar_one_or_none()
    now = datetime.utcnow()
    if report:
        report.status = "Submitted" if submitted else "Pending"
        report.submitted_at = now if submitted else report.submitted_at
        report.kia_draft = narrative[:500] if not submitted else report.kia_draft
        report.fy = fy
    else:
        report = SchoolReport(
            id=str(uuid.uuid4()),
            school_id=school_id,
            student_id=student_id,
            quarter=quarter,
            fy=fy,
            submitted_at=now if submitted else None,
            kia_draft=narrative[:500] if not submitted else None,
            status="Submitted" if submitted else "Pending",
        )
        db.add(report)
    return report


async def _recalc_school_profile(db: AsyncSession, school_id: str) -> None:
    res = await db.execute(select(SchoolStudent).where(SchoolStudent.school_id == school_id))
    students = res.scalars().all()
    profile_res = await db.execute(select(SchoolProfile).where(SchoolProfile.id == school_id))
    profile = profile_res.scalar_one_or_none()
    if not profile:
        return

    if not students:
        profile.total_enrolled = 0
        profile.avg_attendance = 0.0
        profile.avg_academic_score = 0.0
        profile.reports_pending = 0
        return

    profile.total_enrolled = len(students)
    profile.avg_attendance = sum(s.attendance_pct for s in students) / len(students)
    profile.avg_academic_score = sum(s.avg_score for s in students) / len(students)
    profile.reports_pending = sum(1 for s in students if s.q_report_status == "Pending")


async def apply_quarterly_report(
    db: AsyncSession,
    *,
    school_id: str,
    student: SchoolStudent,
    user: SignupRequest,
    payload: dict[str, Any],
    source: str = "manual",
) -> SchoolFormSubmission:
    quarter = payload["quarter"].upper()
    fy = payload.get("fy") or "2025-26"
    ready = bool(payload.get("ready_for_zenk", True))
    teacher_name = user.full_name or "School staff"

    subject_scores = payload.get("subject_scores") or {}
    blooms = payload.get("blooms") or {}
    sel = payload.get("sel") or {}
    narrative = (payload.get("narrative") or "").strip()
    tutor = (payload.get("tutor_recommendation") or "").strip() or None

    if payload.get("attendance_pct") is not None:
        student.attendance_pct = _clamp(payload["attendance_pct"], 0, 100)
    submitted_avg = (
        _clamp(payload["avg_score"], 0, 100)
        if payload.get("avg_score") is not None
        else None
    )
    derived_avg = _derive_avg_score(subject_scores)
    if submitted_avg is None and derived_avg is not None:
        student.avg_score = derived_avg
    elif submitted_avg is not None and derived_avg is None:
        student.avg_score = submitted_avg
    elif submitted_avg is not None and derived_avg is not None:
        # Robustness rule: when subject-wise marks disagree materially with overall avg,
        # trust the directly computed subject average.
        student.avg_score = derived_avg if abs(submitted_avg - derived_avg) > 10 else submitted_avg
    # zqa_score is computed by ZenK algorithm — not set from school form/CSV/PDF
    student.risk_level = payload.get("risk_level") or student.risk_level
    if payload.get("rank_in_class") is not None or payload.get("class_size") is not None:
        from app.services.school_class_rank import normalize_class_rank_fields

        rank_raw = payload.get("rank_in_class")
        size_raw = payload.get("class_size")
        size_int = int(size_raw) if size_raw is not None and str(size_raw).strip() != "" else None
        rank_norm, size_norm = normalize_class_rank_fields(
            str(rank_raw).strip() if rank_raw is not None and str(rank_raw).strip() else None,
            size_int,
        )
        student.rank_in_class = rank_norm
        student.class_size = size_norm
    if payload.get("circle_name"):
        student.circle_name = payload["circle_name"]
    student.tutor_recommendation = tutor
    student.tutor_recommendation_status = "matched" if tutor else "none"
    if not student.class_teacher:
        student.class_teacher = teacher_name

    await _upsert_subject_scores(db, student.id, quarter, subject_scores)
    if blooms:
        await _upsert_blooms(db, student.id, quarter, blooms, teacher_name)
    if sel:
        await _upsert_sel(db, student.id, quarter, sel)

    report_attendance = (
        _clamp(payload["attendance_pct"], 0, 100)
        if payload.get("attendance_pct") is not None
        else None
    )

    if ready:
        from app.services.school_zqa_engine import resolve_attendance_for_zqa

        attendance_for_check, _ = await resolve_attendance_for_zqa(
            db,
            student,
            quarter,
            fy,
            report_attendance=report_attendance,
        )
        assert_zqa_publishable(
            subject_scores=subject_scores,
            blooms=blooms if blooms else None,
            sel=sel if sel else None,
            attendance_pct=attendance_for_check,
            avg_score=student.avg_score,
            rank_in_class=student.rank_in_class,
            class_size=student.class_size,
            narrative=narrative,
        )

    student.q_report_status = "Finalized" if ready else "Pending"

    await recompute_and_apply_zqa(
        db,
        school_id=school_id,
        student=student,
        quarter=quarter,
        fy=fy,
        finalized=ready,
        subject_scores=subject_scores,
        blooms=blooms if blooms else None,
        sel=sel if sel else None,
        report_attendance=report_attendance,
        narrative=narrative,
    )

    await _upsert_narrative(
        db, student.id, quarter, narrative, teacher_name, finalized=ready
    )
    await _upsert_school_report(
        db,
        school_id,
        student.id,
        quarter,
        fy,
        submitted=ready,
        narrative=narrative,
    )
    await _recalc_school_profile(db, school_id)

    submission = SchoolFormSubmission(
        id=str(uuid.uuid4()),
        school_id=school_id,
        student_id=student.id,
        quarter=quarter,
        fy=fy,
        source=source,
        submitted_by_user_id=user.id,
        submitted_by_name=teacher_name,
        submitted_by_email=user.email or "",
        submitted_at=datetime.utcnow(),
        status="processed",
        payload=payload,
    )
    db.add(submission)
    await db.flush()
    return submission


async def latest_submission_map(
    db: AsyncSession, school_id: str, quarter: Optional[str] = None
) -> dict[tuple[str, str], SchoolFormSubmission]:
    q = select(SchoolFormSubmission).where(
        SchoolFormSubmission.school_id == school_id,
        SchoolFormSubmission.status == "processed",
    )
    if quarter:
        q = q.where(SchoolFormSubmission.quarter == quarter.upper())
    q = q.order_by(SchoolFormSubmission.submitted_at.desc())
    res = await db.execute(q)
    out: dict[tuple[str, str], SchoolFormSubmission] = {}
    for row in res.scalars().all():
        key = (row.student_id, row.quarter)
        if key not in out:
            out[key] = row
    return out
