"""Downloadable templates for school quarterly data entry."""

from __future__ import annotations

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.models.school import SchoolStudent

from app.algorithms.zenq.zqa_policy import ZQA_POLICY_TEXT

TEAL = colors.HexColor("#0d9488")
DARK = colors.HexColor("#0f172a")
GRAY = colors.HexColor("#64748b")


IMPORT_GUIDE_TEXT = """Zenk Impact — School quarterly report import guide
============================================================

THREE WAYS TO SUBMIT DATA (all update the same live dashboard & Kia):

1) WEB FORM — Dashboard → Submit report → 5-step wizard

2) CSV BULK — Dashboard → Import CSV
   • Download CSV template (includes your student_id values)
   • One row per student per quarter
   • Required columns: student_id OR student_name, quarter (Q1–Q4),
     attendance_pct, avg_score, risk_level,
     maths, science, english, social, hindi,
     blooms_remember … blooms_create (0–5),
     sel_self_awareness … sel_responsible_decisions (0–5),
     narrative, ready_for_zenk (yes/no)
   • Save as UTF-8 CSV and upload

3) PDF + AI — Dashboard → Import PDF
   • Download blank PDF template, fill or type the report, export/save as PDF
   • Upload PDF → Kia extracts fields → you review & approve
   • Only approved rows are saved to student records

MONTHLY ATTENDANCE (Attendance tab)
---------------------------------
4) ATTENDANCE — Dashboard → Attendance
   • In app: click any month cell → enter working days + days present (% calculated)
   • CSV: download template; working_days + days_present required (attendance_pct optional)
   • Fills the 12-month grid; updates annual % on student profile automatically

MATCHING STUDENTS
-----------------
Use student_id from the CSV template or Students tab. Names must match exactly if using student_name.

QUARTERS
--------
Q4 = Jan–Mar  |  Q3 = Oct–Dec  |  Q2 = Jul–Sep  |  Q1 = Apr–Jun  |  fy = 2025-26

After import, check Academic Reports for submitted_by and timestamp audit line.

BLOOM'S TAXONOMY (0–5) — plain language
---------------------------------------
Rate what you see in class this quarter (class teacher). You do not need to know Bloom's theory.

  0 = not seen   1 = needs support   2 = beginning   3 = meets class level
  4 = strong     5 = exceptional

  remember   — recalls facts, tables, definitions
  understand — explains in own words, not only repeats book
  apply      — uses methods on homework and routine exams
  analyse    — compares, finds patterns, spots mistakes
  evaluate   — judges quality, justifies choices
  create     — original project, essay, presentation, model

SEL (0–5) — behaviour & wellbeing (not exam marks)
--------------------------------------------------
  self_awareness        — knows strengths/weaknesses
  self_management       — on task, punctual, controls behaviour
  social_awareness      — empathy, respects peers
  relationship_skills   — works with others, polite
  responsible_decisions — sensible choices, accepts consequences
"""

IMPORT_GUIDE_TEXT = IMPORT_GUIDE_TEXT.rstrip() + "\n\n" + ZQA_POLICY_TEXT.strip() + "\n"


def import_guide_text() -> str:
    return IMPORT_GUIDE_TEXT


def generate_blank_report_pdf(school_name: str, students: list[SchoolStudent]) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=0.6 * inch, bottomMargin=0.6 * inch)
    ss = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle("t", parent=ss["Title"], fontSize=20, textColor=TEAL, alignment=TA_CENTER),
        "sub": ParagraphStyle("s", parent=ss["Normal"], fontSize=10, textColor=GRAY, alignment=TA_CENTER),
        "h2": ParagraphStyle("h2", parent=ss["Heading2"], fontSize=12, textColor=DARK, spaceBefore=14),
        "body": ParagraphStyle("b", parent=ss["Normal"], fontSize=10, textColor=DARK, leading=14),
        "label": ParagraphStyle("l", parent=ss["Normal"], fontSize=9, textColor=GRAY),
    }

    story = [
        Paragraph("Zenk Quarterly Student Report", styles["title"]),
        Paragraph(f"{school_name} · FY 2025-26 · Fill then upload via Import PDF", styles["sub"]),
        Spacer(1, 0.2 * inch),
        Paragraph(
            "Complete one copy per student per quarter. Upload the saved PDF on the school dashboard "
            "for AI extraction, then review and approve before data goes live.",
            styles["body"],
        ),
    ]

    student_block = students[0] if students else None
    sid = student_block.id if student_block else "________________"
    sname = student_block.full_name if student_block else "________________"

    sections = [
        ("Student", [
            ["Student name", sname],
            ["Student ID (from dashboard)", sid],
            ["Grade", student_block.grade if student_block else "________"],
            ["Quarter", "Q4"],
            ["Financial year", "2025-26"],
        ]),
        ("Summary metrics", [
            ["Attendance %", ""],
            ["Average score %", ""],
            ["Risk level (Low/Medium/High)", ""],
            ["ZQA score", "(calculated by ZenK — do not fill)"],
            ["Rank in class (e.g. 3/42)", ""],
            ["Class size", ""],
            ["Circle name", ""],
        ]),
        ("Subject scores (0–100)", [
            ["Maths", ""], ["Science", ""], ["English", ""],
            ["Social", ""], ["Hindi", ""], ["Sanskrit (optional)", ""],
        ]),
        ("Bloom's taxonomy (0–5)", [
            ["Remember", ""], ["Understand", ""], ["Apply", ""],
            ["Analyse", ""], ["Evaluate", ""], ["Create", ""],
        ]),
        ("SEL (0–5)", [
            ["Self-awareness", ""], ["Self-management", ""], ["Social awareness", ""],
            ["Relationship skills", ""], ["Responsible decisions", ""],
        ]),
        ("Narrative", [
            ["Teacher narrative", ""],
            ["Tutor recommendation (optional)", ""],
            ["Ready for Zenk (yes/no)", "yes"],
        ]),
    ]

    for title, rows in sections:
        story.append(Paragraph(title, styles["h2"]))
        table = Table(rows, colWidths=[2.2 * inch, 4.3 * inch])
        table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("TEXTCOLOR", (0, 0), (0, -1), GRAY),
            ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(table)

    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph(
        f"Generated {datetime.utcnow().strftime('%d %b %Y')} · Zenk Impact Platform",
        styles["label"],
    ))

    doc.build(story)
    return buf.getvalue()
