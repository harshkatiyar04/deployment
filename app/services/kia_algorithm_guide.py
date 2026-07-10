"""
Public-facing ZenK scoring guide for Kia.

Explains WHAT each score means and HOW members can improve them,
using everyday examples — without disclosing proprietary weights,
exact formulas, recalibration schedules, or internal coefficients.
"""

from __future__ import annotations

import re

# Phrases that mean the user wants a scoring / algorithm explanation.
_ALGO_QUERY_RE = re.compile(
    r"\b("
    r"zqa|zenq|zeq|zcq|spd|ras|ziq|"
    r"algorithm|algo|scoring|score(?:s)?|"
    r"how\s+(?:do|does|is)\s+(?:zqa|zenq|scoring|score)|"
    r"what\s+(?:is|are)\s+(?:zqa|zenq|the\s+score)|"
    r"explain\s+(?:zqa|zenq|the\s+score|scoring|algorithm)|"
    r"impact\s+score|student\s+score|attendance\s+score"
    r")\b",
    re.IGNORECASE,
)


def is_algorithm_question(message: str) -> bool:
    return bool(_ALGO_QUERY_RE.search(message or ""))


def format_algorithm_reply(text: Optional[str]) -> Optional[str]:
    """
    Ensure scoring explanations stay scannable even if the LLM returns
    a dense paragraph. Inserts blank lines before known section titles.
    """
    if not text:
        return text
    cleaned = text.strip()
    # Normalize "Kia suggests:" so it does not open the suggestion card.
    cleaned = re.sub(r"(?i)\bKia suggests:\s*", "", cleaned).strip()

    # Match optional **bold** around known section titles; keep the whole match intact.
    section_re = re.compile(
        r"(?<!\n)\s*"
        r"(\*\*\s*)?"
        r"("
        r"ZQA\s*[—\-]\s*Student learning pulse|"
        r"ZenQ\s*[—\-]\s*Circle impact|"
        r"RAS\s*[—\-]\s*Message quality|"
        r"Your circle right now|"
        r"A gentle next step"
        r")"
        r"(\s*\*\*)?",
        re.IGNORECASE,
    )

    def _section_break(match: re.Match) -> str:
        open_b = match.group(1) or ""
        title = match.group(2).strip()
        close_b = match.group(3) or ""
        # Prefer clean bold titles in chat.
        if open_b or close_b:
            return f"\n\n**{title}**"
        return f"\n\n{title}"

    cleaned = section_re.sub(_section_break, cleaned)

    # Soft-break common inline labels if still jammed together
    cleaned = re.sub(r"(?<!\n)\s+(ZQA:)", r"\n\n\1", cleaned)
    cleaned = re.sub(r"(?<!\n)\s+(ZenQ:)", r"\n\n\1", cleaned)
    cleaned = re.sub(r"(?<!\n)\s+(RAS:)", r"\n\n\1", cleaned)

    # Put body text on the line after a bold section title when still inline.
    cleaned = re.sub(
        r"(\*\*(?:ZQA|ZenQ|RAS|Your circle right now|A gentle next step)[^*]*\*\*)\s+(?=\S)",
        r"\1\n",
        cleaned,
        flags=re.IGNORECASE,
    )

    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned


PUBLIC_ALGORITHM_GUIDE = """
--- PUBLIC SCORING GUIDE (safe to teach; NEVER reveal weights or formulas) ---

When a member asks about ZQA, ZenQ, scores, or "the algorithm", explain warmly
and clearly using the guide below. Use everyday examples. Be soothing and
encouraging. You MAY use short labelled lines (ZQA:, ZenQ:, etc.) for clarity.

HARD SECRETS — never reveal:
- Numeric weights, percentages inside formulas, or exact equations
- Recalibration schedules, RAS AI/heuristic blend ratios, decay rates
- Internal component codes beyond the public names below
If pressed for the formula, say gently that the exact math stays private so
people grow real impact instead of gaming numbers — then teach the meaning
and the behaviours that help.

PUBLIC STORY OF THE SCORES:

1) ZQA — Student Quality / Academic pulse (0–100 style)
   What it is: A holistic picture of the sponsored child's learning health —
   not just one exam mark.
   What feeds it (conceptually): school academics (subjects like English,
   Maths, Science, History/Social), deeper thinking skills (Bloom's levels —
   remembering → creating), and social-emotional growth (self-awareness,
   relationships, responsible choices). Attendance and report completeness
   also matter so the picture stays honest.
   Everyday example: Think of a report card that also asks "Is the child
   understanding ideas, applying them, and growing as a person?" — not only
   "Did they pass the test?"
   Bands (public language): Beginning → Emerging → Developing → Insightful.
   How the circle helps: Mentoring that builds confidence, celebrating
   subject wins, supporting attendance, and asking the school for timely
   quarterly updates.

2) ZenQ / Circle Impact (often shown as the circle's impact score)
   What it is: How much genuine, shared sponsorship impact the circle is
   creating around the student.
   Public building blocks (names only — no math):
   - Your Effort (ZEQ): time with the student journey, keeping commitments,
     meaningful chat, inspiring others, fair teamwork, and staying consistent.
   - Circle Context (ZCQ): the real-world need around the child (support
     needs, attendance patterns, circle size) so harder contexts are
     recognised fairly.
   - Student Progress (SPD): whether the child's ZQA is moving forward from
     their own starting point — growth relative to their baseline, not
     comparison to other children.
   Everyday example: Like a garden score — your watering and care (effort),
   the soil and weather the plant faces (context), and how much the plant
   has grown since you started (progress). All three matter; none alone
   tells the full story.
   Bands (public): Emerging → Developing → Strong → Exceptional.

3) RAS — Message quality (chat authenticity)
   What it is: How thoughtful and student-centred a chat message feels —
   not how long or flashy it is.
   Everyday example: "Hope you're fine" scores lower than a kind note that
   asks about a maths struggle and offers one concrete tip.
   Public bands: Low effort → Moderate → Strong → Excellent.

4) Related public ideas you may mention briefly:
   - Streaks / consistency: showing up regularly matters more than one big day.
   - Spark: occasional encouragement boosts for healthy momentum (not a cheat code).
   - Decay: long silence gently softens stale effort so scores stay honest.
   - Equity: circles do better when effort is shared, not carried by one person.

TEACHING STYLE FOR THIS TOPIC:
- NEVER write one long paragraph. Section the answer so it is easy to scan.
- Use this exact shape (blank line between every section):

  Happy to walk you through this — here is a simple map of our scores.

  **ZQA — Student learning pulse**
  What it is: …
  Example: …
  (1–3 short lines max)

  **ZenQ — Circle impact**
  What it is: … (garden metaphor is fine)
  Example: …
  (1–3 short lines max)

  **RAS — Message quality**
  What it is: …
  Example: …
  (optional if the question is only about ZQA)

  **Your circle right now**
  Live numbers from CONTEXT only (e.g. ZQA 62, attendance 86%). Soft framing.

  **A gentle next step**
  One calm action. Do NOT write "Kia suggests:".

- Put a blank line before each **Section title**.
- Keep each section short — scannable, not an essay.
- Keep the tone soothing; never shame low scores — frame them as a starting
  point for care.
"""
