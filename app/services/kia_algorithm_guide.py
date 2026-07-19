"""
Public-facing ZenK scoring guide for Kia.

Explains WHAT each score means and HOW members can improve them,
using everyday examples — without disclosing proprietary weights,
exact formulas, recalibration schedules, or internal coefficients.
"""

from __future__ import annotations

import re
from typing import Optional

# Phrases that mean the user wants a scoring / algorithm explanation.
_ALGO_QUERY_RE = re.compile(
    r"\b("
    r"zqa|zenq|zeq|zcq|spd|ras|ziq|"
    r"algorithm|algo|scoring|score(?:s)?|"
    r"how\s+(?:do|does|is|can|should)\s+(?:i\s+|we\s+)?(?:increase|improve|raise|boost)?\s*"
    r"(?:my\s+|our\s+)?(?:zqa|zenq|ziq|scoring|score)|"
    r"how\s+(?:do|does|is)\s+(?:zqa|zenq|ziq|scoring|score)|"
    r"what\s+(?:is|are)\s+(?:my\s+)?(?:zqa|zenq|ziq|the\s+score)|"
    r"explain\s+(?:zqa|zenq|ziq|the\s+score|scoring|algorithm)|"
    r"impact\s+score|student\s+score|attendance\s+score|"
    r"umbrella\s+(?:of\s+)?score|"
    r"increase\s+(?:my\s+|our\s+)?(?:ziq|zenq|zqa)"
    r")\b",
    re.IGNORECASE,
)

_FOCUS_ZIQ_RE = re.compile(
    r"\b(ziq|circle\s+impact(?:\s+score)?)\b",
    re.IGNORECASE,
)
_FOCUS_ZQA_RE = re.compile(
    r"\b(zqa|student\s+(?:learning\s+)?(?:pulse|score)|learning\s+pulse)\b",
    re.IGNORECASE,
)
_FOCUS_UMBRELLA_RE = re.compile(
    r"\b(zenq|umbrella|zeq|zcq|spd|ras|algorithm|scoring)\b",
    re.IGNORECASE,
)


def is_algorithm_question(message: str) -> bool:
    return bool(_ALGO_QUERY_RE.search(message or ""))


def score_question_focus(message: str) -> str:
    """
    Which score the user is asking about.

    Returns: ziq | zqa | umbrella | general
    """
    text = message or ""
    if re.search(r"\bziq\b", text, re.IGNORECASE):
        return "ziq"
    if re.search(r"\bcircle\s+impact\b", text, re.IGNORECASE):
        return "ziq"
    if _FOCUS_ZQA_RE.search(text) and not re.search(
        r"\b(zenq|ziq|zeq|zcq|spd)\b", text, re.I
    ):
        return "zqa"
    if re.search(r"\bzqa\b", text, re.IGNORECASE) and not re.search(
        r"\b(zenq|ziq)\b", text, re.IGNORECASE
    ):
        return "zqa"
    if _FOCUS_UMBRELLA_RE.search(text) or _FOCUS_ZIQ_RE.search(text):
        return "umbrella"
    return "general"


def format_algorithm_reply(text: Optional[str]) -> Optional[str]:
    """
    Clean scoring explanations: scannable sections, no orphan bullets,
    no raw engine decimals leaked as “breakdown”.
    """
    if not text:
        return text
    cleaned = text.strip()
    cleaned = re.sub(r"(?i)\bKia suggests:\s*", "", cleaned).strip()

    # Strip leaked raw component decimals (0.6025 style) with optional labels.
    cleaned = re.sub(
        r"(?im)^\s*[-•*]?\s*(?:ZEQ|ZCQ|SPD)\s*(?:\([^)]+\))?\s*:\s*0\.\d{2,}\b.*$",
        "",
        cleaned,
    )
    cleaned = re.sub(
        r"(?i)\b(ZEQ|ZCQ|SPD)\s*(?:\([^)]+\))?\s*:\s*0\.\d{2,}\b(?:\s*\([^)]*\))?",
        "",
        cleaned,
    )

    # Fix broken "Increasing\nZEQ" / "Enhancing\nZCQ" / "Supporting\nSPD"
    cleaned = re.sub(
        r"(?i)\b(Increasing|Enhancing|Supporting|Improving)\s*\n+\s*((?:ZEQ|ZCQ|SPD)\b)",
        r"\1 \2",
        cleaned,
    )

    # Collapse orphan bullet-only lines
    cleaned = re.sub(r"(?m)^\s*[-•*]\s*$", "", cleaned)
    cleaned = re.sub(r"(?m)^\s*[-•*]\s*\n+(?=\s*[-•*]?\s*(?:ZEQ|ZCQ|SPD|Increasing|Enhancing|Supporting))", "", cleaned)

    # Normalize list markers to "- "
    cleaned = re.sub(r"(?m)^\s*[•*]\s+", "- ", cleaned)

    section_re = re.compile(
        r"(?<!\n)\s*"
        r"(\*\*\s*)?"
        r"("
        r"ZenQ\s+[Uu]mbrella|"
        r"ZIQ\s*[—\-]\s*Circle [Ii]mpact|"
        r"ZQA\s*[—\-]\s*Student learning pulse|"
        r"ZenQ\s*[—\-]\s*Circle impact|"
        r"Understanding ZIQ|"
        r"How to raise your ZIQ|"
        r"Breaking down ZIQ|"
        r"Increasing ZIQ|"
        r"RAS\s*[—\-]\s*Message quality|"
        r"Your circle right now|"
        r"A gentle next step"
        r")"
        r"(\s*\*\*)?",
        re.IGNORECASE,
    )

    def _section_break(match: re.Match) -> str:
        title = match.group(2).strip()
        return f"\n\n**{title}**"

    cleaned = section_re.sub(_section_break, cleaned)

    cleaned = re.sub(r"(?<!\n)\s+(ZQA:)", r"\n\n\1", cleaned)
    cleaned = re.sub(r"(?<!\n)\s+(ZenQ:)", r"\n\n\1", cleaned)
    cleaned = re.sub(r"(?<!\n)\s+(ZIQ:)", r"\n\n\1", cleaned)
    cleaned = re.sub(r"(?<!\n)\s+(RAS:)", r"\n\n\1", cleaned)

    cleaned = re.sub(
        r"(\*\*(?:ZenQ umbrella|ZIQ|ZQA|ZenQ|Understanding ZIQ|How to raise your ZIQ|"
        r"Breaking down ZIQ|Increasing ZIQ|RAS|Your circle right now|"
        r"A gentle next step)[^*]*\*\*)\s+(?=\S)",
        r"\1\n",
        cleaned,
        flags=re.IGNORECASE,
    )

    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned


PUBLIC_ALGORITHM_GUIDE = """
--- PUBLIC SCORING GUIDE (safe to teach; NEVER reveal weights or formulas) ---

ZenQ is an UMBRELLA of scores — not a single student number.
Never treat student ZQA as ZenQ or ZIQ.

HARD SECRETS — never reveal:
- Numeric weights, percentages inside formulas, or exact equations
- Raw engine decimals for ZEQ/ZCQ/SPD (like 0.6025) — use BAND LABELS only
- Recalibration schedules, RAS AI/heuristic blend ratios, decay rates
If pressed for the formula, say gently that the exact math stays private so
people grow real impact instead of gaming numbers — then teach behaviours.

PUBLIC MAP:

0) **ZenQ umbrella** = ZIQ + ZEQ + ZCQ + SPD (+ RAS for chat). ZQA feeds SPD only.

1) **ZQA** — Student learning pulse (0–100 style). Not Circle Impact.

2) **ZIQ — Circle Impact** — headline under ZenQ.
   Built from three public building blocks (names only):
   - ZEQ — circle effort (showing up, thoughtful chat, helping)
   - ZCQ — student/context need (you support it; you don't "hack" it)
   - SPD — student progress vs their own baseline (ZQA movement)
   Bands for ZIQ: Emerging → Developing → Strong → Exceptional.

3) **RAS** — chat message quality (thoughtful > one-liners).

════════════════════════════════════════════════════════════
IF THE QUESTION IS ABOUT ZIQ (or "how do I increase my ZIQ"):
════════════════════════════════════════════════════════════
Use THIS shape exactly (blank line between sections). Be concrete — no fluff.

**ZIQ — Circle Impact**
Your circle's ZIQ is <number from CONTEXT> (<band from CONTEXT>).
One sentence: what that band means (from CONTEXT band description).
One sentence: ZenQ is the umbrella; ZIQ is the Circle Impact headline.

**Understanding ZIQ**
In plain words: ZIQ rises when the circle's effort (ZEQ), care for the child's
real situation (ZCQ), and the student's progress from their own start (SPD)
all move in a healthy way — like watering, soil, and growth in a garden.
Do NOT list raw decimals. If CONTEXT has component bands, say e.g.
"Effort looks Active, context is Standard, student progress is On track."

**How to raise your ZIQ**
Give 3 concrete actions as a clean list (each line starts with "- "):
- Prefer items from CONTEXT how_to_raise_ziq when present.
- Make them this-week actions (chat quality, school update, attendance check-in).
- Never say vague things like "provide resources and a nurturing environment" alone.

**Your circle right now**
Live ZIQ + student ZQA/attendance from CONTEXT only (correct labels).

**A gentle next step**
ONE specific next action for the next 48 hours. No "Kia suggests:" prefix.

════════════════════════════════════════════════════════════
IF THE QUESTION IS ABOUT ZenQ (umbrella) OR ZQA — adapt; do not paste the ZIQ essay.
════════════════════════════════════════════════════════════

Formatting rules:
- Blank line before every **Section title**
- Lists: each item on one line starting with "- " (never a lonely bullet on its own line)
- Never dump the same ZQA template when they asked for ZIQ
- Never shame low scores — Emerging is a starting point for care
"""
