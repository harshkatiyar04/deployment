"""Human-readable ZQA policy and validation messages (transparency without exposing full algorithm)."""

from __future__ import annotations

ZQA_POLICY_TEXT = """
ZQA (ZenK Quality Assessment) — what schools need to know
=========================================================

ZQA is calculated by the ZenK platform after you submit a quarterly report.
Schools never enter a ZQA score manually.

WHAT GOES INTO ZQA (high level)
-------------------------------
• Academic pillar — English, Maths, Science, and Social/Hindi (history slot).
  When a subject is missing, remaining subjects are re-weighted fairly.
• Bloom's pillar — six classroom cognitive ratings (0–5) from your report.
• SEL pillar — five social-emotional ratings (0–5) from your report.
• Attendance integrity — we prefer the monthly attendance grid for the quarter;
  if attendance falls below 92%, a integrity adjustment applies (score is reduced).

WHAT IS REQUIRED TO PUBLISH ZQA ("Ready for ZenK")
--------------------------------------------------
You cannot finalize / publish ZQA until ALL of the following are present:
• At least two academic subjects (English, Maths, Science, and/or Social/Hindi)
• Complete Bloom's assessment (all six levels)
• Complete SEL assessment (all five dimensions)
• Class rank and class size
• Teacher narrative

Marks-only PDF imports can be saved as drafts, but ZQA stays unpublished until
Bloom's and SEL are completed in the dashboard.

WHAT WE DO NOT DISCLOSE
-----------------------
Exact internal weights, anti-gaming thresholds, and ZenQ circle formulas are
not published — this protects fairness and prevents gaming. Use "Explain ZQA"
in the dashboard for your student's published breakdown.

ESTIMATED ZENQ UPLIFT (school dashboard)
----------------------------------------
The "Estimated ZenQ uplift" on the student profile is a school-side indicator
derived from report data. It is NOT the live Circle ZenQ score used in sponsor
circles and youth chat.
"""

ZQA_ISSUE_MESSAGES: dict[str, str] = {
    "finalized_report_requires_blooms": "Bloom's taxonomy assessment is missing.",
    "finalized_report_requires_sel": "SEL assessment is missing.",
    "finalized_report_incomplete_blooms": "Bloom's assessment must include all six levels (Remember through Create).",
    "finalized_report_incomplete_sel": "SEL assessment must include all five dimensions.",
    "finalized_report_requires_academic_subjects": "At least two academic subjects are required (English, Maths, Science, and/or Social/Hindi).",
    "finalized_report_requires_rank": "Rank in class is required (e.g. 3/42).",
    "finalized_report_requires_class_size": "Class size is required.",
    "finalized_report_requires_narrative": "Teacher narrative is required.",
    "no_academic_subjects": "No academic subject scores were found.",
}

ZQA_PUBLISH_BLOCKERS = frozenset(ZQA_ISSUE_MESSAGES.keys())


def issue_label(code: str) -> str:
    return ZQA_ISSUE_MESSAGES.get(code, code.replace("_", " "))


def publish_blocking_issues(issues: list[str]) -> list[str]:
    return [code for code in issues if code in ZQA_PUBLISH_BLOCKERS]


def format_publish_blockers(codes: list[str]) -> str:
    if not codes:
        return ""
    lines = [ZQA_ISSUE_MESSAGES.get(c, c.replace("_", " ")) for c in codes]
    return (
        "Cannot finalize report for ZenK — ZQA will not be published until these are resolved: "
        + " ".join(f"• {line}" for line in lines)
    )
