from __future__ import annotations
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.services.kia import _call_llm
from app.services.kia_priority_engine import compute_student_priority

logger = logging.getLogger(__name__)

_SCHOOL_CONSTITUTION = """You are Kia, ZenK's School AI Advisor.
You are speaking with the Principal of a ZenK Partner School — a dedicated educational leader
responsible for the academic progress and wellbeing of their students enrolled in ZenK-sponsored circles.

YOUR ROLE:
- Surface actionable insights about student attendance, academic performance, and ZQA scores.
- Flag students at risk and suggest concrete next steps (parent contact, tutor matching, circle engagement).
- Help the principal navigate ZenK platform tasks: submitting reports, reviewing ZQA milestones.
- Celebrate student achievements and school milestones warmly.

TONE: Professional, warm, and concise. You treat the principal as a trusted partner.

RULES:
1. Always base insights on the School Context provided — never hallucinate metrics.
2. Reference student names only when contextually appropriate.
3. Flag high-risk students proactively.
4. Keep dashboard responses under 3 short paragraphs.
5. No markdown, no bullet points, no headers in responses — plain conversational text only.
6. Never share information about other schools.

FORMATTING: Plain text. When you have a specific suggestion, prefix it: "Kia recommends: [text]"
"""


def _build_school_prompt(school_context: dict) -> str:
    prompt = _SCHOOL_CONSTITUTION + "\n\n"
    if school_context:
        prompt += "--- SCHOOL CONTEXT ---\n"
        for k, v in school_context.items():
            prompt += f"- {k.replace('_', ' ').title()}: {v}\n"
        prompt += "----------------------\n"
    return prompt


async def fetch_school_context(school_id: str, db: AsyncSession) -> dict:
    from app.models.school import (
        SchoolProfile,
        SchoolStudent,
        SchoolReport,
        SchoolStudentNarrative,
        SchoolFormSubmission,
    )

    profile_res = await db.execute(
        select(SchoolProfile).where(SchoolProfile.id == school_id)
    )
    profile = profile_res.scalar_one_or_none()
    if not profile:
        return {}

    students_res = await db.execute(
        select(SchoolStudent).where(SchoolStudent.school_id == school_id)
    )
    students = students_res.scalars().all()

    narratives_res = await db.execute(
        select(SchoolStudentNarrative).where(
            SchoolStudentNarrative.student_id.in_([s.id for s in students])
            if students
            else False
        )
    )
    narratives = narratives_res.scalars().all()
    narrative_by_student = {n.student_id: n for n in narratives}

    reports_res = await db.execute(
        select(SchoolReport).where(SchoolReport.school_id == school_id)
    )
    all_reports = reports_res.scalars().all()
    pending_reports = [r for r in all_reports if r.status == "Pending"]

    from app.models.school import SchoolFormSubmission

    pdf_pending_res = await db.execute(
        select(SchoolFormSubmission).where(
            SchoolFormSubmission.school_id == school_id,
            SchoolFormSubmission.status == "pending_review",
        )
    )
    pdf_pending = pdf_pending_res.scalars().all()

    subs_res = await db.execute(
        select(SchoolFormSubmission)
        .where(SchoolFormSubmission.school_id == school_id)
        .order_by(SchoolFormSubmission.submitted_at.desc())
        .limit(5)
    )
    recent_subs = subs_res.scalars().all()

    high_risk = [s.full_name for s in students if s.risk_level == "High"]
    below_attendance = [
        s.full_name for s in students if s.attendance_pct > 0 and s.attendance_pct < 75
    ]

    student_summaries = []
    for s in students:
        narr = narrative_by_student.get(s.id)
        narr_note = (
            f"narrative Q{narr.quarter}: {'finalized' if narr.finalized else 'draft'}"
            if narr
            else "no narrative yet"
        )
        student_summaries.append(
            f"{s.full_name} ({s.grade}): attendance {s.attendance_pct:.1f}%, "
            f"avg score {s.avg_score:.1f}%, ZQA {s.zqa_score:.1f}% (platform-calculated), risk {s.risk_level}, "
            f"report {s.q_report_status}; {narr_note}"
        )

    recent_activity = []
    for sub in recent_subs:
        name = next((s.full_name for s in students if s.id == sub.student_id), "Unknown")
        recent_activity.append(
            f"{sub.quarter} report for {name} submitted by {sub.submitted_by_name} "
            f"at {sub.submitted_at.isoformat()}"
        )

    return {
        "school_name": profile.school_name,
        "principal_name": profile.principal_name,
        "total_students": len(students),
        "avg_attendance": f"{profile.avg_attendance:.1f}%",
        "avg_academic_score": f"{profile.avg_academic_score:.1f}%",
        "high_risk_students": ", ".join(high_risk) if high_risk else "None",
        "students_below_attendance_threshold": ", ".join(below_attendance) if below_attendance else "None",
        "pending_reports_count": len(pending_reports),
        "next_zqa_date": profile.next_zqa_date or "Not scheduled",
        "fy": profile.fy_current,
        "live_student_data": "; ".join(student_summaries) if student_summaries else "No students",
        "recent_form_submissions": "; ".join(recent_activity) if recent_activity else "None yet",
        "pdf_reviews_pending": len(pdf_pending),
        "data_policy": "Use only the metrics above — they are loaded live from the database after form submissions.",
    }


async def generate_school_response(message: str, school_context: dict) -> Optional[str]:
    try:
        system_prompt = _build_school_prompt(school_context)
        return await _call_llm(
            system_prompt=system_prompt,
            user_message=message,
            max_tokens=1024,
            temperature=0.65,
        )
    except Exception as e:
        logger.error(f"kia_school: LLM error: {e}")
        return None


async def generate_school_priorities(school_id: str, db: AsyncSession) -> list[dict]:
    from app.models.school import SchoolStudent, SchoolReport, SchoolFormSubmission

    students_res = await db.execute(
        select(SchoolStudent).where(SchoolStudent.school_id == school_id)
    )
    students = students_res.scalars().all()
    student_map = {s.id: s.full_name for s in students}

    reports_res = await db.execute(
        select(SchoolReport).where(
            SchoolReport.school_id == school_id,
            SchoolReport.status == "Pending",
        )
    )
    pending_reports = reports_res.scalars().all()

    pdf_pending_res = await db.execute(
        select(SchoolFormSubmission).where(
            SchoolFormSubmission.school_id == school_id,
            SchoolFormSubmission.status == "pending_review",
        )
    )
    pdf_pending = pdf_pending_res.scalars().all()

    priorities = []

    student_signals = []
    for s in students:
        signal = compute_student_priority(
            student_name=s.full_name,
            attendance_pct=float(s.attendance_pct or 0.0),
            zqa_score=float(s.zqa_score or 0.0),
            zqa_baseline_delta=s.zqa_baseline_delta,
            q_report_status=s.q_report_status or "Pending",
            risk_level=s.risk_level or "Low",
            tutor_recommendation_pending=bool(
                s.tutor_recommendation and s.tutor_recommendation_status == "none"
            ),
        )
        student_signals.append(signal)

    for s in students:
        if s.avg_score == 0 and s.attendance_pct == 0:
            priorities.append({
                "type": "report_due",
                "title": f"Submit quarterly report — {s.full_name}",
                "detail": (
                    f"No live metrics for {s.full_name} yet. "
                    f"Open Submit report and enter attendance, scores, Bloom's, SEL, and narrative."
                ),
                "student_name": s.full_name,
                "action_required": True,
            })

    for s in students:
        if s.attendance_pct > 0 and s.attendance_pct < 75:
            grade_part = s.grade.replace("Grade ", "Gr ")
            priorities.append({
                "type": "attendance_alert",
                "title": f"Attendance alert — {s.full_name} ({grade_part})",
                "detail": (
                    f"Attendance dropped to {s.attendance_pct:.0f}%, below the 75% ZenQ threshold. "
                    f"This risks a ZQA disqualification if sustained. "
                    f"Recommend contacting parent/guardian and alerting the Sponsor Leader."
                ),
                "student_name": s.full_name,
                "action_required": True,
            })

    if pending_reports:
        names = ", ".join(
            student_map.get(r.student_id, "Unknown") for r in pending_reports[:3]
        )
        quarters = list({r.quarter for r in pending_reports})
        priorities.append({
            "type": "report_due",
            "title": f"{pending_reports[0].quarter} reports pending — {len(pending_reports)}",
            "detail": (
                f"{names}: {', '.join(quarters)} report(s) not finalized. "
                f"Use Submit report on the school dashboard to enter live data."
            ),
            "student_name": None,
            "action_required": True,
        })

    if pdf_pending:
        priorities.insert(0, {
            "type": "report_due",
            "title": f"PDF reviews pending — {len(pdf_pending)}",
            "detail": (
                "AI extracted report data from uploaded PDFs. "
                "Open Import PDF, review fields, and approve to publish live dashboard data."
            ),
            "student_name": None,
            "action_required": True,
        })

    if not students:
        priorities.append({
            "type": "report_due",
            "title": "No students enrolled",
            "detail": "Add a student record, then submit the quarterly report form.",
            "student_name": None,
            "action_required": True,
        })

    # Deterministic intervention priorities (highest score first).
    for signal in sorted(student_signals, key=lambda x: x.score, reverse=True)[:5]:
        if signal.score < 30:
            continue
        priorities.append({
            "type": signal.type,
            "title": f"{signal.urgency.title()} priority — {signal.student_name}",
            "detail": signal.detail,
            "student_name": signal.student_name,
            "action_required": signal.action_required,
            "priority_score": signal.score,
            "urgency": signal.urgency,
            "recommended_action": signal.action,
            "reasons": signal.reasons[:4],
        })

    for s in students:
        if s.zqa_score >= 90:
            priorities.append({
                "type": "zqa_milestone",
                "title": f"ZQA milestone — {s.full_name}",
                "detail": (
                    f"{s.full_name} has a platform ZQA score of {s.zqa_score:.0f}% "
                    f"(ZenK-calculated from attendance, academics, and circle data)."
                ),
                "student_name": s.full_name,
                "action_required": False,
                "priority_score": 0,
                "urgency": "watch",
                "recommended_action": "Celebrate milestone and sustain progress",
                "reasons": ["High published ZQA score"],
            })

    for s in students:
        if s.tutor_recommendation and s.tutor_recommendation_status == "none":
            priorities.append({
                "type": "tutor_recommendation",
                "title": f"Tutor recommendation — {s.full_name}",
                "detail": s.tutor_recommendation,
                "student_name": s.full_name,
                "action_required": True,
                "priority_score": 55,
                "urgency": "high",
                "recommended_action": "Accept or reject tutor recommendation today",
                "reasons": ["Tutor recommendation pending decision"],
            })

    return priorities
