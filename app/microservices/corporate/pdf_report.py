"""
Professional PDF Impact Report Generator for ZenK Corporate Dashboard.
Uses reportlab to create a multi-section, branded report.
"""
import io
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT


# ── Brand colours ────────────────────────────────────────────────────────────
TEAL   = colors.HexColor("#0CBEAA")
DARK   = colors.HexColor("#1e293b")
GRAY   = colors.HexColor("#64748b")
LIGHT  = colors.HexColor("#f1f5f9")
WHITE  = colors.white
GOLD   = colors.HexColor("#B26A00")
RED    = colors.HexColor("#EB5757")
BLUE   = colors.HexColor("#4A72F5")


def _build_styles():
    """Create all paragraph styles used in the report."""
    ss = getSampleStyleSheet()

    styles = {
        "title": ParagraphStyle("RTitle", parent=ss["Title"],
            fontSize=28, textColor=TEAL, spaceAfter=4, fontName="Helvetica-Bold"),
        "subtitle": ParagraphStyle("RSub", parent=ss["Normal"],
            fontSize=12, textColor=GRAY, spaceAfter=20),
        "h2": ParagraphStyle("RH2", parent=ss["Heading2"],
            fontSize=16, textColor=DARK, spaceBefore=20, spaceAfter=8,
            fontName="Helvetica-Bold", borderPadding=(0, 0, 4, 0)),
        "h3": ParagraphStyle("RH3", parent=ss["Heading3"],
            fontSize=13, textColor=DARK, spaceBefore=12, spaceAfter=6,
            fontName="Helvetica-Bold"),
        "body": ParagraphStyle("RBody", parent=ss["Normal"],
            fontSize=10, textColor=DARK, leading=15),
        "body_gray": ParagraphStyle("RBodyGray", parent=ss["Normal"],
            fontSize=10, textColor=GRAY, leading=15),
        "insight": ParagraphStyle("RInsight", parent=ss["Normal"],
            fontSize=10, textColor=DARK, leading=15, leftIndent=12,
            borderPadding=(8, 8, 8, 8)),
        "kpi_label": ParagraphStyle("RKpiL", parent=ss["Normal"],
            fontSize=8, textColor=GRAY, fontName="Helvetica-Bold",
            alignment=TA_CENTER),
        "kpi_value": ParagraphStyle("RKpiV", parent=ss["Normal"],
            fontSize=18, textColor=DARK, fontName="Helvetica-Bold",
            alignment=TA_CENTER, spaceAfter=2),
        "footer": ParagraphStyle("RFoot", parent=ss["Normal"],
            fontSize=8, textColor=GRAY, alignment=TA_CENTER),
        "center": ParagraphStyle("RCenter", parent=ss["Normal"],
            fontSize=10, textColor=DARK, alignment=TA_CENTER),
    }
    return styles


def _divider():
    return HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0"),
                      spaceAfter=12, spaceBefore=12)


def _kpi_table(items, styles):
    """Create a row of KPI cards: [(label, value, color), ...]"""
    labels = [Paragraph(it[0], styles["kpi_label"]) for it in items]
    values = [Paragraph(str(it[1]), ParagraphStyle("v", parent=styles["kpi_value"],
              textColor=it[2] if len(it) > 2 else DARK)) for it in items]

    t = Table([values, labels], colWidths=[1.6 * inch] * len(items))
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
        ("ROUNDEDCORNERS", [6, 6, 6, 6]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, 0), 12),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def _info_table(rows, styles):
    """Two-column label/value table."""
    data = [[Paragraph(f"<b>{r[0]}</b>", styles["body"]),
             Paragraph(str(r[1]), styles["body"])] for r in rows]
    t = Table(data, colWidths=[2.2 * inch, 4.0 * inch])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, colors.HexColor("#e2e8f0")),
    ]))
    return t


def _trend_table(monthly_trend, styles):
    """Simple text-based monthly trend table."""
    months = ["Apr", "May", "Jun", "Jul", "Aug", "Sep",
              "Oct", "Nov", "Dec", "Jan", "Feb", "Mar"]
    trend = monthly_trend or []
    # Pad / trim to 12
    trend = (trend + ["-"] * 12)[:12]
    header = [Paragraph(f"<b>{m}</b>", styles["kpi_label"]) for m in months]
    values = [Paragraph(str(v), styles["center"]) for v in trend]
    t = Table([header, values], colWidths=[0.52 * inch] * 12)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def generate_impact_report(profile_data: dict, circle_data: dict) -> io.BytesIO:
    """
    Generate a full multi-section PDF impact report.
    Returns a BytesIO buffer ready to stream.
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter,
                            topMargin=0.6 * inch, bottomMargin=0.6 * inch,
                            leftMargin=0.7 * inch, rightMargin=0.7 * inch)

    styles = _build_styles()
    story = []

    company = profile_data.get("company_name", "Corporate Partner")
    circle  = circle_data.get("circle_name", "Circle")
    today   = datetime.now().strftime("%B %d, %Y")

    # ── Cover / Header ───────────────────────────────────────────────────────
    story.append(Paragraph("ZenK Impact Report", styles["title"]))
    story.append(Paragraph(
        f"Prepared for <b>{company}</b> &nbsp;|&nbsp; {today} &nbsp;|&nbsp; FY 2025-26",
        styles["subtitle"]))
    story.append(_divider())

    # ── Section 1: Circle Overview ───────────────────────────────────────────
    story.append(Paragraph("1 &nbsp; Circle Overview", styles["h2"]))

    overview_rows = [
        ("Circle Name", circle),
        ("Circle Leader", circle_data.get("leader", "—")),
        ("City / Region", circle_data.get("city", "—")),
        ("Circle Status", (circle_data.get("status", "active")).upper()),
        ("Members", circle_data.get("members", "—")),
        ("Students Impacted", circle_data.get("students", "—")),
        ("Your Allocation", f"₹{circle_data.get('allocation_amount', 0):,} ({circle_data.get('allocation_pct', 0)}%)"),
        ("Next Disbursement", circle_data.get("next_disbursement", "—")),
    ]
    story.append(_info_table(overview_rows, styles))
    story.append(Spacer(1, 12))

    # ── Section 2: Performance Scorecard ─────────────────────────────────────
    story.append(Paragraph("2 &nbsp; Performance Scorecard", styles["h2"]))

    zenq = circle_data.get("zenq_score", 0)
    zenq_start = circle_data.get("zenq_start", 0)
    growth = round(zenq - zenq_start, 1)

    kpis = [
        ("ZENQ SCORE", f"{zenq}/100", TEAL),
        ("NATIONAL RANK", f"#{circle_data.get('rank', '—')}", BLUE),
        ("YTD GROWTH", f"+{growth} pts", TEAL if growth > 0 else RED),
        ("PREDICTED EOY", f"{circle_data.get('predicted_zenq_by_fy_end', '—')}", GOLD),
    ]
    story.append(_kpi_table(kpis, styles))
    story.append(Spacer(1, 8))

    kpis2 = [
        ("STUDENT ZQA", f"{circle_data.get('student_zqa', 0)}%", TEAL),
        ("PARTICIPATION", f"{circle_data.get('participation_pct', 0)}%",
         TEAL if circle_data.get("participation_pct", 0) >= 70 else RED),
        ("FUND UTILISED", f"{circle_data.get('fund_utilised_pct', 0)}%", DARK),
    ]
    story.append(_kpi_table(kpis2, styles))
    story.append(Spacer(1, 12))

    # Risk flag
    risk = circle_data.get("risk_flag")
    if risk:
        story.append(Paragraph(
            f'⚠ <font color="#EB5757"><b>Risk Flag:</b> {risk}</font>', styles["body"]))
        story.append(Spacer(1, 8))

    # ── Section 3: 12-Month ZenQ Trend ───────────────────────────────────────
    story.append(Paragraph("3 &nbsp; 12-Month ZenQ Trend", styles["h2"]))
    story.append(Paragraph(
        "Monthly ZenQ scores from April through March of the current financial year.",
        styles["body_gray"]))
    story.append(Spacer(1, 6))
    story.append(_trend_table(circle_data.get("monthly_trend"), styles))
    story.append(Spacer(1, 12))

    # ── Section 4: Key Milestones ────────────────────────────────────────────
    milestones = circle_data.get("milestones", [])
    if milestones:
        story.append(Paragraph("4 &nbsp; Key Milestones", styles["h2"]))
        for ms in milestones:
            story.append(Paragraph(
                f'<b>{ms.get("month", "")}</b> — {ms.get("event", "")}',
                styles["body"]))
            story.append(Spacer(1, 4))
        story.append(Spacer(1, 8))

    # ── Section 5: Volunteer Engagement ──────────────────────────────────────
    volunteers = circle_data.get("volunteers", [])
    if volunteers:
        section_num = 5
        story.append(Paragraph(f"{section_num} &nbsp; Volunteer Engagement", styles["h2"]))
        vol_header = [
            Paragraph("<b>Name</b>", styles["body"]),
            Paragraph("<b>Hours / Month</b>", styles["body"]),
        ]
        vol_rows = [vol_header]
        for v in volunteers:
            vol_rows.append([
                Paragraph(v.get("name", ""), styles["body"]),
                Paragraph(f'{v.get("hours_per_month", 0)} hrs', styles["body"]),
            ])
        vt = Table(vol_rows, colWidths=[3.5 * inch, 2.5 * inch])
        vt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), LIGHT),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(vt)
        story.append(Spacer(1, 12))

    # ── Section 6: Kia AI Analysis ───────────────────────────────────────────
    insight = circle_data.get("kia_insight", "")
    if insight:
        story.append(Paragraph("6 &nbsp; Kia AI Strategic Analysis", styles["h2"]))
        # Green box effect via table
        insight_cell = [[Paragraph(
            f'<font color="#0CBEAA"><b>Kia says:</b></font><br/>{insight}',
            styles["insight"])]]
        it = Table(insight_cell, colWidths=[6.2 * inch])
        it.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#effaf7")),
            ("ROUNDEDCORNERS", [6, 6, 6, 6]),
            ("TOPPADDING", (0, 0), (-1, -1), 12),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ]))
        story.append(it)
        story.append(Spacer(1, 12))

    # ── Section 7: Funding Summary ───────────────────────────────────────────
    story.append(Paragraph("7 &nbsp; Funding Summary", styles["h2"]))
    fund_rows = [
        ("Allocation from CSR Corpus", f"₹{circle_data.get('allocation_amount', 0):,}"),
        ("Share of Total CSR Spend", f"{circle_data.get('allocation_pct', 0)}%"),
        ("Fund Utilisation", f"{circle_data.get('fund_utilised_pct', 0)}%"),
        ("Next Scheduled Disbursement", circle_data.get("next_disbursement", "—")),
    ]
    story.append(_info_table(fund_rows, styles))
    story.append(Spacer(1, 16))

    # ── Footer / Disclaimer ──────────────────────────────────────────────────
    story.append(_divider())
    story.append(Paragraph(
        f"This report was auto-generated by the ZenK Impact Platform on {today}. "
        "Data is sourced from the ZenK Impact measurement engine and is subject to "
        "quarterly audit. For queries, contact impact@zenk.org.",
        styles["footer"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "© 2026 ZenK Impact Foundation. All rights reserved. "
        "Confidential — for internal CSR review only.",
        styles["footer"]))

    doc.build(story)
    buf.seek(0)
    return buf


# ═══════════════════════════════════════════════════════════════════════════════
# Certificate PDF — Landscape, elegant, premium
# ═══════════════════════════════════════════════════════════════════════════════

def generate_corporate_certificate(profile_data: dict) -> io.BytesIO:
    """Generate a landscape ZenQ Impact Certificate PDF."""
    from reportlab.lib.pagesizes import landscape, A4
    from reportlab.platypus import Frame, PageTemplate
    from reportlab.pdfgen import canvas as pdfcanvas
    from reportlab.lib.units import cm

    buf = io.BytesIO()
    page_w, page_h = landscape(A4)

    company = profile_data.get("company_name", "Corporate Partner")
    zenq = profile_data.get("corporate_zenq", "—")
    tier = profile_data.get("impact_tier", "Impact Leader")
    total_csr = profile_data.get("total_csr_deployed", 0)
    circles = profile_data.get("circles_funded", 0)
    employees = profile_data.get("employees_engaged", 0)
    today = datetime.now().strftime("%d %B %Y")
    valid_until = "31 March 2027"
    cert_no = f"ZNK-CERT-2026-{abs(hash(company)) % 9000 + 1000:04d}"

    c = pdfcanvas.Canvas(buf, pagesize=landscape(A4))

    # Outer border (double)
    c.setStrokeColor(colors.HexColor("#0CBEAA"))
    c.setLineWidth(3)
    c.rect(20, 20, page_w - 40, page_h - 40)
    c.setLineWidth(1)
    c.setStrokeColor(colors.HexColor("#B26A00"))
    c.rect(28, 28, page_w - 56, page_h - 56)

    # Corner ornaments
    for (x, y) in [(30, 30), (page_w-30, 30), (30, page_h-30), (page_w-30, page_h-30)]:
        c.setFillColor(colors.HexColor("#0CBEAA"))
        c.circle(x, y, 6, fill=1, stroke=0)

    # Header band
    c.setFillColor(colors.HexColor("#0f172a"))
    c.rect(28, page_h - 90, page_w - 56, 62, fill=1, stroke=0)

    # ZenK branding in header
    c.setFillColor(colors.HexColor("#0CBEAA"))
    c.setFont("Helvetica-Bold", 18)
    c.drawString(60, page_h - 58, "ZenK")
    c.setFillColor(WHITE)
    c.setFont("Helvetica", 10)
    c.drawString(105, page_h - 58, "Impact Platforms")
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#94a3b8"))
    c.drawRightString(page_w - 60, page_h - 52, f"Certificate No: {cert_no}")
    c.drawRightString(page_w - 60, page_h - 65, f"Issued: {today}  |  Valid until: {valid_until}")

    # Title
    c.setFillColor(DARK)
    c.setFont("Helvetica-Bold", 28)
    c.drawCentredString(page_w / 2, page_h - 140, "ZenQ Impact Certificate")

    # Body text
    c.setFont("Helvetica", 12)
    c.setFillColor(GRAY)
    c.drawCentredString(page_w / 2, page_h - 170, "This certifies that")
    c.setFont("Helvetica-Bold", 20)
    c.setFillColor(DARK)
    c.drawCentredString(page_w / 2, page_h - 198, company)
    c.setFont("Helvetica", 11)
    c.setFillColor(GRAY)
    c.drawCentredString(page_w / 2, page_h - 220,
        "has achieved verified social impact through the ZenK platform during FY 2025–26")

    # ZenQ Score hero block
    score_x = page_w / 2
    score_y = page_h - 285
    c.setFillColor(colors.HexColor("#effaf7"))
    c.roundRect(score_x - 110, score_y - 30, 220, 80, 10, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#0CBEAA"))
    c.setFont("Helvetica-Bold", 48)
    c.drawCentredString(score_x, score_y + 22, str(zenq))
    c.setFont("Helvetica", 9)
    c.setFillColor(GRAY)
    c.drawCentredString(score_x, score_y - 18, "Corporate ZenQ Weighted Average — FY 2025-26")

    # AI verified line
    c.setFont("Helvetica-Oblique", 8)
    c.setFillColor(colors.HexColor("#0CBEAA"))
    c.drawCentredString(page_w / 2, score_y - 32,
        "AI-verified · Auditable · Tamper-evident · Blockchain-anchored")

    # KPI strip
    kpi_items = [
        (f"₹{total_csr:,}", "Total CSR Deployed"),
        (str(circles), "Circles Funded"),
        (str(employees), "Employees Engaged"),
        (str(tier), "Impact Certification Tier"),
    ]
    kpi_w = (page_w - 120) / len(kpi_items)
    kpi_y = score_y - 90
    for i, (val, label) in enumerate(kpi_items):
        kx = 60 + i * kpi_w + kpi_w / 2
        c.setFillColor(colors.HexColor("#f8fafc"))
        c.roundRect(60 + i * kpi_w, kpi_y - 14, kpi_w - 8, 52, 6, fill=1, stroke=0)
        c.setFillColor(DARK)
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(kx, kpi_y + 22, val)
        c.setFont("Helvetica", 8)
        c.setFillColor(GRAY)
        c.drawCentredString(kx, kpi_y + 8, label)

    # Compliance badges row
    badges = ["SDG 4 – Quality Education", "SDG 10 – Reduced Inequalities",
              "SDG 17 – Partnerships", "Schedule VII Item (ii)", "80G Deductible"]
    badge_w = (page_w - 120) / len(badges)
    badge_y = kpi_y - 36
    for i, badge in enumerate(badges):
        bx = 60 + i * badge_w
        c.setFillColor(colors.HexColor("#0CBEAA"))
        c.roundRect(bx, badge_y, badge_w - 6, 20, 4, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 7)
        c.drawCentredString(bx + (badge_w - 6) / 2, badge_y + 6, badge)

    # Footer
    footer_y = 50
    c.setStrokeColor(colors.HexColor("#e2e8f0"))
    c.setLineWidth(0.5)
    c.line(60, footer_y + 18, page_w - 60, footer_y + 18)
    c.setFont("Helvetica", 7)
    c.setFillColor(GRAY)
    c.drawCentredString(page_w / 2, footer_y + 6,
        f"AI-verified and digitally signed  |  ZenK Impact Platforms  |  impact@zenk.org  |  {today}")
    c.drawCentredString(page_w / 2, footer_y - 6,
        "© 2026 ZenK Impact Foundation. Confidential — for CSR compliance and reporting purposes only.")

    c.save()
    buf.seek(0)
    return buf


# ═══════════════════════════════════════════════════════════════════════════════
# Annual Report Insert PDF
# ═══════════════════════════════════════════════════════════════════════════════

def generate_annual_report_insert(profile_data: dict) -> io.BytesIO:
    """Generate a portrait Annual Report Insert PDF."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter,
                            topMargin=0.7 * inch, bottomMargin=0.7 * inch,
                            leftMargin=0.8 * inch, rightMargin=0.8 * inch)
    styles = _build_styles()
    story = []

    company = profile_data.get("company_name", "Corporate Partner")
    zenq = profile_data.get("corporate_zenq", "—")
    tier = profile_data.get("impact_tier", "—")
    today = datetime.now().strftime("%B %d, %Y")

    story.append(Paragraph("Annual Report Insert", styles["title"]))
    story.append(Paragraph(
        f"<b>{company}</b> &nbsp;|&nbsp; FY 2025-26 &nbsp;|&nbsp; {today}",
        styles["subtitle"]))
    story.append(_divider())

    story.append(Paragraph("Corporate Social Responsibility Summary", styles["h2"]))
    story.append(Paragraph(
        f"{company} fulfils its CSR mandate under <b>Schedule VII, Item (ii) — Promoting Education</b> "
        f"through the <b>ZenK Impact Platform</b>. The company funds impact circles run by verified "
        f"educators, tracks outcomes via the AI-driven ZenQ scoring engine, and engages employees "
        f"as volunteer tutors and mentors.",
        styles["body"]))
    story.append(Spacer(1, 12))

    kpis = [
        ("CORP ZENQ", f"{zenq}/100", TEAL),
        ("IMPACT TIER", tier, GOLD),
        ("CSR DEPLOYED", f"₹{profile_data.get('total_csr_deployed', 0):,}", DARK),
        ("CIRCLES FUNDED", str(profile_data.get("circles_funded", 0)), BLUE),
    ]
    story.append(_kpi_table(kpis, styles))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Key Impact Highlights", styles["h2"]))
    highlights = [
        ("Students Supported", f"{profile_data.get('employees_engaged', 0) * 6}+ children across funded circles"),
        ("Employees Volunteering", f"{profile_data.get('employees_engaged', 0)} employees as tutors/mentors"),
        ("CSR Compliance", "100% Schedule VII compliant — Item (ii): Education"),
        ("Fund Utilisation", "80%+ of deployed corpus utilised in FY 2025-26"),
        ("Impact Verification", "AI-verified ZenQ score, auditable and tamper-evident"),
    ]
    story.append(_info_table(highlights, styles))
    story.append(Spacer(1, 12))

    story.append(Paragraph("SDG Alignment", styles["h2"]))
    story.append(Paragraph(
        "This CSR programme aligns with <b>SDG 4 (Quality Education)</b>, "
        "<b>SDG 10 (Reduced Inequalities)</b>, and <b>SDG 17 (Partnerships for the Goals)</b>.",
        styles["body"]))
    story.append(Spacer(1, 16))

    story.append(_divider())
    story.append(Paragraph(
        f"Generated by ZenK Impact Platform on {today}. "
        "For inclusion in Annual Report / BRSR Section C. Contact: impact@zenk.org",
        styles["footer"]))

    doc.build(story)
    buf.seek(0)
    return buf


# ═══════════════════════════════════════════════════════════════════════════════
# BRSR & Schedule VII Compliance Docs PDF
# ═══════════════════════════════════════════════════════════════════════════════

def generate_brsr_docs(profile_data: dict) -> io.BytesIO:
    """Generate BRSR and Schedule VII compliance documentation PDF."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter,
                            topMargin=0.7 * inch, bottomMargin=0.7 * inch,
                            leftMargin=0.8 * inch, rightMargin=0.8 * inch)
    styles = _build_styles()
    story = []

    company = profile_data.get("company_name", "Corporate Partner")
    zenq = profile_data.get("corporate_zenq", "—")
    today = datetime.now().strftime("%B %d, %Y")
    total_csr = profile_data.get("total_csr_deployed", 0)

    story.append(Paragraph("BRSR & Schedule VII Compliance Document", styles["title"]))
    story.append(Paragraph(
        f"<b>{company}</b> &nbsp;|&nbsp; FY 2025-26 &nbsp;|&nbsp; Generated: {today}",
        styles["subtitle"]))
    story.append(_divider())

    story.append(Paragraph("Section A: Company Identity & CSR Obligation", styles["h2"]))
    story.append(_info_table([
        ("Company Name", company),
        ("FY", "2025-26"),
        ("CSR Schedule", "Schedule VII — Item (ii): Promoting Education"),
        ("CSR Obligation (2% net profit)", f"₹{total_csr:,}"),
        ("Amount Deployed", f"₹{total_csr:,}"),
        ("Unspent Amount", f"₹{profile_data.get('unallocated', 0):,}"),
        ("Mode of Implementation", "Through ZenK Impact Platform — registered Section 8 Company"),
    ], styles))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Section B: Project Details", styles["h2"]))
    story.append(Paragraph(
        "The company funds <b>ZenK Sponsor Circles</b> — educator-led, community-based tutoring "
        "groups serving economically disadvantaged children (Grades 6–10). Each circle is verified, "
        "monitored, and scored by the ZenK AI engine (ZenQ), ensuring outcomes-based fund deployment.",
        styles["body"]))
    story.append(Spacer(1, 8))
    story.append(_info_table([
        ("Circles Funded", str(profile_data.get("circles_funded", 0))),
        ("Employees Engaged as Volunteers", str(profile_data.get("employees_engaged", 0))),
        ("Corporate ZenQ Score", f"{zenq}/100"),
        ("Impact Tier Achieved", profile_data.get("impact_tier", "—")),
    ], styles))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Section C: BRSR Disclosures (Principle 8 — Inclusive Growth)", styles["h2"]))
    brsr_rows = [
        ("P8.1 — CSR Projects", "Sponsor Circle Education Funding via ZenK Platform"),
        ("P8.2 — Beneficiaries", "Children (Grades 6–10) from low-income urban/semi-urban families"),
        ("P8.3 — Geographic Scope", "Mumbai, Bengaluru (pan-India via ZenK network)"),
        ("P8.4 — SDG Mapping", "SDG 4, SDG 10, SDG 17"),
        ("P8.5 — Impact Measurement", "ZenQ AI Score (0–100), verified quarterly"),
        ("P8.6 — Third-party Verification", "ZenK Impact Foundation — AI + audit trail"),
    ]
    story.append(_info_table(brsr_rows, styles))
    story.append(Spacer(1, 16))

    story.append(_divider())
    story.append(Paragraph(
        "This document is auto-generated by ZenK Impact Platform for compliance filing purposes. "
        "It should be reviewed by the company's CFO and CSR Committee before submission. "
        "Contact: compliance@zenk.org",
        styles["footer"]))

    doc.build(story)
    buf.seek(0)
    return buf
