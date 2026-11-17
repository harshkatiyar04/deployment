"""
Public-facing ZenK scoring guide for Kia (ZenQ).

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
    r"zqa|zenq|pcs|sgi|spd|ras|ziq|zeq|zcq|"
    r"algorithm|algo|scoring|score(?:s)?|"
    r"how\s+(?:do|does|is|can|should)\s+(?:i\s+|we\s+)?(?:increase|improve|raise|boost)?\s*"
    r"(?:my\s+|our\s+)?(?:zqa|zenq|pcs|scoring|score)|"
    r"how\s+(?:do|does|is)\s+(?:zqa|zenq|pcs|scoring|score)|"
    r"what\s+(?:is|are)\s+(?:my\s+)?(?:zqa|zenq|pcs|the\s+score|spd)|"
    r"explain\s+(?:zqa|zenq|pcs|spd|the\s+score|scoring|algorithm)|"
    r"impact\s+score|student\s+score|attendance\s+score|"
    r"your\s+contribution|lifetime|sponsor\s+yield|impact\s+return|"
    r"increase\s+(?:my\s+|our\s+)?(?:zenq|pcs|zqa)"
    r")\b",
    re.IGNORECASE,
)

_FOCUS_ZENQ_RE = re.compile(
    r"\b(zenq|circle\s+impact|lifetime|this\s+month|season)\b",
    re.IGNORECASE,
)
_FOCUS_PCS_RE = re.compile(
    r"\b(pcs|your\s+contribution|my\s+contribution|personal\s+contribution)\b",
    re.IGNORECASE,
)
_FOCUS_ZQA_RE = re.compile(
    r"\b(zqa|student\s+(?:learning\s+)?(?:pulse|score)|learning\s+pulse|sgi)\b",
    re.IGNORECASE,
)
_FOCUS_SPD_RE = re.compile(r"\b(spd|ziq|zeq|zcq)\b", re.IGNORECASE)


def is_algorithm_question(message: str) -> bool:
    return bool(_ALGO_QUERY_RE.search(message or ""))


def score_question_focus(message: str) -> str:
    """
    Which score the user is asking about.

    Returns: zenq | pcs | zqa | spd_legacy | general
    """
    text = message or ""
    if _FOCUS_SPD_RE.search(text) and not _FOCUS_PCS_RE.search(text):
        # Explicit legacy names — answer with cutover story
        if re.search(r"\bspd\b", text, re.I) or re.search(
            r"\b(ziq|zeq|zcq)\b", text, re.I
        ):
            if not re.search(r"\b(zenq|pcs|lifetime)\b", text, re.I):
                return "spd_legacy"
    if _FOCUS_PCS_RE.search(text):
        return "pcs"
    if _FOCUS_ZQA_RE.search(text) and not re.search(
        r"\b(zenq|pcs|lifetime)\b", text, re.I
    ):
        return "zqa"
    if _FOCUS_ZENQ_RE.search(text) or re.search(
        r"\b(algorithm|scoring|umbrella)\b", text, re.I
    ):
        return "zenq"
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

    # Strip leaked raw legacy component decimals
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

    cleaned = re.sub(
        r"(?i)\b(Increasing|Enhancing|Supporting|Improving)\s*\n+\s*((?:ZEQ|ZCQ|SPD|PCS|ZenQ)\b)",
        r"\1 \2",
        cleaned,
    )

    cleaned = re.sub(r"(?m)^\s*[-•*]\s*$", "", cleaned)
    cleaned = re.sub(
        r"(?m)^\s*[-•*]\s*\n+(?=\s*[-•*]?\s*(?:ZEQ|ZCQ|SPD|PCS|ZenQ|Increasing|Enhancing|Supporting))",
        "",
        cleaned,
    )

    cleaned = re.sub(r"(?m)^\s*[•*]\s+", "- ", cleaned)

    section_re = re.compile(
        r"(?<!\n)\s*"
        r"(\*\*\s*)?"
        r"("
        r"ZenQ\s+v2|"
        r"ZenQ\s*[—\-]\s*Circle impact|"
        r"What\s+replaced\s+SPD|"
        r"Your\s+contribution\s*\(PCS\)|"
        r"PCS|"
        r"ZQA\s*[—\-]\s*Student learning pulse|"
        r"How\s+to\s+raise\s+ZenQ|"
        r"How\s+to\s+raise\s+your\s+contribution|"
        r"RAS\s*[—\-]\s*Message quality|"
        r"Your\s+circle\s+right\s+now|"
        r"A\s+gentle\s+next\s+step|"
        # legacy titles that may still appear — normalize spacing
        r"ZenQ\s+[Uu]mbrella|"
        r"ZIQ\s*[—\-]\s*Circle [Ii]mpact"
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
    cleaned = re.sub(r"(?<!\n)\s+(PCS:)", r"\n\n\1", cleaned)
    cleaned = re.sub(r"(?<!\n)\s+(RAS:)", r"\n\n\1", cleaned)

    cleaned = re.sub(
        r"(\*\*(?:ZenQ|PCS|Your contribution \(PCS\)|ZQA|How to raise ZenQ|"
        r"How to raise your contribution|What replaced SPD|RAS|Your circle right now|"
        r"A gentle next step)[^*]*\*\*)\s+(?=\S)",
        r"\1\n",
        cleaned,
        flags=re.IGNORECASE,
    )

    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned


PUBLIC_ALGORITHM_GUIDE = """
--- PUBLIC SCORING GUIDE — ZenQ (safe to teach; NEVER reveal weights or formulas) ---

PRODUCT MODE: ZenQ. Circle impact is cumulative from an event ledger.
Do NOT teach the old live formula ZIQ = ZEQ × ZCQ × SPD as current product math.
Never say "ZenQ v2" to users — the product name is ZenQ.

HARD SECRETS — never reveal:
- Numeric weights, exact equations, recalibration schedules, RAS blend ratios
- Raw internal IP decimals meant for engines only
If pressed for the formula, say gently that exact coefficients stay private so
people grow real impact instead of gaming numbers — then teach behaviours.

PUBLIC MAP:

0) **ZenQ — Circle impact**
   Scored activity (chat, sessions, targets, Kia, pledges, referrals, sparks)
   earns impact points → monthly circle earnings E → Lifetime (never resets)
   and Season (calendar year). Board display uses raw IP (display_divisor=1).

1) **Your contribution (PCS)** — each member's own cumulative contribution
   from their attributed events (with inactivity fade after long silence).
   Not the same as circle Lifetime. Never rank members out of N — use bands.

2) **ZQA** — Student learning pulse / school assessments. Not equal to ZenQ.
   Growth from the student's own baseline informs a growth multiplier G on
   monthly earnings (floored so a hard quarter does not erase lifetime).
   Student Growth Index (SGI) is a growth band for the child narrative.

3) **RAS** — chat message quality (thoughtful > one-liners). Helps chat IP.

4) **Sponsor yield / Impact return** — display ratios for funders (per-lakh
   impact; month vs recent months). They do NOT add back into ZenQ IP.

════════════════════════════════════════════════════════════
IF ASKED ABOUT SPD / ZIQ / ZEQ / ZCQ (legacy names):
════════════════════════════════════════════════════════════
**What replaced SPD**
SPD was the old circle multiplier that could shrink the whole circle score.
ZenQ no longer multiplies circle stock by SPD.
Student progress now informs growth G (≥ 1) and SGI bands; school ZQA may
still track progress vs baseline internally — that is not a public SPD card
on the circle scoreboard.
ZIQ/ZEQ/ZCQ were the old umbrella labels. Use ZenQ lifetime / this month / PCS.

════════════════════════════════════════════════════════════
IF THE QUESTION IS ABOUT ZenQ / circle impact / lifetime:
════════════════════════════════════════════════════════════

**ZenQ — Circle impact**
Use CONTEXT lifetime / this month / milestone when present.
One sentence: ZenQ is cumulative circle impact from real activity — not ZQA alone.

**How to raise ZenQ**
Give 3 concrete "- " actions (prefer CONTEXT how_to_raise_zenq / how_to_raise_ziq):
- Verified sessions and learning targets with the student
- Substantive encouraging chat (not one-liners)
- Sparks / referrals when the circle is ready; keep pledges current

**Your circle right now**
Lifetime, this month, milestone, PCS if present — correct product labels only (never "v2").

**A gentle next step**
ONE specific next action for the next 48 hours. No "Kia suggests:" prefix.

════════════════════════════════════════════════════════════
IF THE QUESTION IS ABOUT PCS / Your contribution:
════════════════════════════════════════════════════════════

**Your contribution (PCS)**
Personal cumulative impact from their own scored activity.
Never invent another member's PCS.

**How to raise your contribution**
Same concrete behaviours as above, attributed to them.

════════════════════════════════════════════════════════════
IF THE QUESTION IS ABOUT ZQA / SGI:
════════════════════════════════════════════════════════════
Teach ZQA as student learning pulse; never call it ZenQ.
SGI / growth bands describe the child's trajectory from their own baseline.

Formatting rules:
- Blank line before every **Section title**
- Lists: each item on one line starting with "- "
- Never dump a ZQA essay when they asked for ZenQ/PCS
- Never shame low scores — early circles are a starting point for care
- Never claim live ZIQ = ZEQ × ZCQ × SPD
"""
