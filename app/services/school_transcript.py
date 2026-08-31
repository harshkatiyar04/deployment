"""Premium student progress transcript (same payload as on-screen preview)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.school import (
    SchoolProfile,
    SchoolStudent,
    SchoolStudentBloomsAssessment,
    SchoolStudentNarrative,
    SchoolStudentSEL,
    SchoolStudentSubjectScore,
)


async def build_student_transcript(
    db: AsyncSession,
    *,
    profile: SchoolProfile,
    student: SchoolStudent,
) -> dict:
    """Structured premium transcript payload + plain-text fallback."""
    scores_res = await db.execute(
        select(SchoolStudentSubjectScore).where(SchoolStudentSubjectScore.student_id == student.id)
    )
    scores = list(scores_res.scalars().all())

    blooms_res = await db.execute(
        select(SchoolStudentBloomsAssessment).where(
            SchoolStudentBloomsAssessment.student_id == student.id
        )
    )
    blooms = list(blooms_res.scalars().all())

    sel_res = await db.execute(
        select(SchoolStudentSEL).where(SchoolStudentSEL.student_id == student.id)
    )
    sels = list(sel_res.scalars().all())

    narrative_res = await db.execute(
        select(SchoolStudentNarrative).where(SchoolStudentNarrative.student_id == student.id)
    )
    narratives = list(narrative_res.scalars().all())

    subjects_by_quarter: dict[str, list[dict]] = {}
    for s in scores:
        q = (s.quarter or "Q4").upper()
        subjects_by_quarter.setdefault(q, []).append(
            {"subject": s.subject, "score": float(s.score or 0), "quarter": q}
        )

    latest_blooms = blooms[0] if blooms else None
    latest_sel = sels[0] if sels else None
    latest_narrative = narratives[0] if narratives else None
    for n in narratives:
        if n.finalized:
            latest_narrative = n
            break

    attendance = float(student.attendance_pct or 0)
    avg_score = float(student.avg_score or 0)
    zqa = float(student.zqa_score or 0)

    transcript = {
        "school_name": profile.school_name,
        "school_logo_url": getattr(profile, "school_logo_url", None),
        "fy": profile.fy_current or "2025-26",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "student": {
            "id": student.id,
            "full_name": student.full_name,
            "zenk_id": student.zenk_id,
            "grade": student.grade,
            "circle_id": student.circle_id,
            "circle_name": student.circle_name,
            "class_teacher": student.class_teacher,
            "sponsor_lead": student.sl_name,
            "mentor_name": student.mentor_name,
        },
        "metrics": {
            "attendance_pct": attendance,
            "avg_score": avg_score,
            "zqa_score": zqa,
            "rank_in_class": student.rank_in_class,
            "class_size": student.class_size,
            "zenq_contribution": float(student.zenq_contribution or 0),
            "risk_level": student.risk_level,
        },
        "subjects_by_quarter": subjects_by_quarter,
        "blooms": (
            {
                "quarter": latest_blooms.quarter,
                "remember": float(latest_blooms.remember or 0),
                "understand": float(latest_blooms.understand or 0),
                "apply": float(latest_blooms.apply or 0),
                "analyse": float(latest_blooms.analyse or 0),
                "evaluate": float(latest_blooms.evaluate or 0),
                "create": float(latest_blooms.create or 0),
                "assessed_by": latest_blooms.assessed_by,
            }
            if latest_blooms
            else None
        ),
        "sel": (
            {
                "quarter": latest_sel.quarter,
                "self_awareness": float(latest_sel.self_awareness or 0),
                "self_management": float(latest_sel.self_management or 0),
                "social_awareness": float(latest_sel.social_awareness or 0),
                "relationship_skills": float(latest_sel.relationship_skills or 0),
                "responsible_decisions": float(latest_sel.responsible_decisions or 0),
            }
            if latest_sel
            else None
        ),
        "narrative": (
            {
                "quarter": latest_narrative.quarter,
                "teacher_name": latest_narrative.teacher_name,
                "narrative": latest_narrative.narrative,
                "finalized": bool(latest_narrative.finalized),
            }
            if latest_narrative
            else None
        ),
        "finalized": bool(latest_narrative.finalized) if latest_narrative else False,
    }

    lines = [
        "ZENK STUDENT PROGRESS REPORT",
        f"{profile.school_name} — {transcript['fy']}",
        "",
        f"Student: {student.full_name}",
        f"Grade: {student.grade or '—'}",
        f"Circle: {student.circle_name or 'Unassigned'}",
        f"Class Teacher: {student.class_teacher or '—'}",
        f"Sponsor Lead: {student.sl_name or '—'}",
        "",
        "KEY METRICS",
        f"Attendance: {attendance}%",
        f"Average Score: {avg_score}%",
        f"ZQA Score: {zqa if zqa > 0 else 'Pending'}",
        f"Class Rank: {student.rank_in_class or '—'} / {student.class_size or '—'}",
        f"Risk Level: {student.risk_level or '—'}",
        "",
    ]
    if subjects_by_quarter:
        lines.append("SUBJECT PERFORMANCE")
        for q, rows in sorted(subjects_by_quarter.items()):
            for row in rows:
                lines.append(f"  {row['subject']} ({q}): {int(round(row['score']))}%")
        lines.append("")
    if latest_narrative and latest_narrative.narrative:
        lines.append(f"TEACHER NARRATIVE ({latest_narrative.quarter})")
        lines.append(latest_narrative.narrative)
        lines.append("")
    lines.append("Generated by ZenK Impact Platform")
    transcript["report_text"] = "\n".join(lines)
    return transcript
