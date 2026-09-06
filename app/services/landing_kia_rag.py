"""Landing Kia RAG — retrieve platform chunks + grounded English answer."""

from __future__ import annotations

import hashlib
import logging
import re
import time
from typing import Dict, List, Optional, Tuple

from app.core.settings import settings
from app.services.landing_kia_kb import LANDING_KIA_CHUNKS, KiaChunk, SUGGESTION_PROMPTS

logger = logging.getLogger(__name__)

_OFF_TOPIC = re.compile(
    r"\b("
    r"invest(?:ment|ing|ments)?|stocks?|mutual\s*funds?|crypto|bitcoin|loans?|emi|interest\s*rates?|"
    r"tax\s*advice|portfolio|trading|forex|roi\b|returns?\s+on\s+investment|"
    r"medical\s*advice|diagnos\w*|prescription|lawsuit|attorney|politics|election|"
    r"how\s+to\s+hack|weapons?"
    r")\b",
    re.I,
)

_GREETING_PREFIX = re.compile(
    r"^\s*((hi there|hi!|hi,|hello there|hello!|hello,|hey there|hey!|hey,|"
    r"namaste[!.,]?|good (morning|afternoon|evening)[!.,]?)"
    r"[\s,—–-]*)+",
    re.I,
)

# Instant answers for common chips / near-matches (skip Groq latency)
_FAST: Dict[str, str] = {
    "what is zenk?": (
        "ZenK is a trust ecosystem where people form a circle around one student, "
        "support their growth, and make progress visible — Kizuna, a bond to educate "
        "one child and measure the impact."
    ),
    "how does scoring work?": (
        "Six signals feed one board: ZenQ (circle impact), ZEQ (effort), ZQA (learning pulse), "
        "ZCQ (context), SPD (progress from baseline), and RAS (mentorship quality). "
        "Together they show effort meeting evidence — proprietary weights stay unpublished."
    ),
    "what is zenq?": (
        "ZenQ is the circle’s live impact grade — the headline score. It rolls effort, "
        "context, and student growth into one number that updates as people show up."
    ),
    "what does zeq measure?": (
        "ZEQ tracks effort: mentoring time, kept promises, meaningful chat, and how fairly "
        "effort is shared across the circle. Showing up counts — quiet money alone doesn’t."
    ),
    "explain zqa": (
        "ZQA is the student learning pulse — more than a report card. It blends academics, "
        "deeper thinking, social-emotional growth, and attendance into one learning-health read."
    ),
    "explain zqa learning pulse": (
        "ZQA is the student learning pulse — more than a report card. It blends academics, "
        "deeper thinking, social-emotional growth, and attendance into one learning-health read."
    ),
    "what is zcq?": (
        "ZCQ is context fairness. It adjusts for the student’s real circumstances — need, "
        "attendance patterns, circle size — so harder journeys aren’t punished by a flat curve."
    ),
    "what is zcq context?": (
        "ZCQ is context fairness. It adjusts for the student’s real circumstances — need, "
        "attendance patterns, circle size — so harder journeys aren’t punished by a flat curve."
    ),
    "what is spd?": (
        "SPD measures how far the child has moved from their own baseline — never against "
        "classmates or national ranks. Growth from where they started is what counts."
    ),
    "what is spd progress delta?": (
        "SPD measures how far the child has moved from their own baseline — never against "
        "classmates or national ranks. Growth from where they started is what counts."
    ),
    "what is ras?": (
        "RAS rates whether guidance feels thoughtful and student-centred. Genuine messages rise; "
        "copy-paste check-ins don’t."
    ),
    "what is ras chat quality?": (
        "RAS rates whether guidance feels thoughtful and student-centred. Genuine messages rise; "
        "copy-paste check-ins don’t."
    ),
    "what is a circle?": (
        "A circle is a small group — sponsors, mentors, peers, and supporters — formed around "
        "one student so support is coordinated and progress stays visible."
    ),
    "who can join?": (
        "Circle leaders or members, mentors, students, schools, parents/guardians, and "
        "corporate/CSR partners. On the interest form you can pick leader, member, or not sure — "
        "no commitment at registration."
    ),
    "what am i committing to?": (
        "Nothing today. Registering interest isn’t a pledge, payment, or contract — you stay "
        "on the list, learn next steps, and decide later."
    ),
    "what am i committing to today?": (
        "Nothing today. Registering interest isn’t a pledge, payment, or contract — you stay "
        "on the list, learn next steps, and decide later."
    ),
    "when does money move?": (
        "Not before launch. No contributions during interest registration. When circles open, "
        "funds move only through governed escrow — visible and released against agreed support."
    ),
    "how does the demo work?": (
        "On this page, the Impact scores demo lets you join a sample circle and watch ZenQ, "
        "ZEQ, ZQA, ZCQ, SPD, and RAS move when someone shows up — a preview of the live board."
    ),
    "how does the live demo work?": (
        "On this page, the Impact scores demo lets you join a sample circle and watch ZenQ, "
        "ZEQ, ZQA, ZCQ, SPD, and RAS move when someone shows up — a preview of the live board."
    ),
    "what do mentors do?": (
        "Mentors invest time in real guidance. Mentor hours and participation show up on the "
        "board — thoughtful check-ins raise quality; empty pings don’t."
    ),
    "how do schools fit in?": (
        "Schools can partner so learning signals connect into the circle view. ZQA draws on "
        "learning health beyond exam day alone. School interest uses the same registration path."
    ),
}

_FOLLOW_OPENERS = (
    "Great question — ",
    "Interesting question — ",
    "Love that you asked — ",
    "That’s a really useful one — ",
    "Glad you brought this up — ",
    "Nice one — ",
    "I’m glad you asked — ",
)

# Strip leftover “wrapper” openers from older replies / model habits
_ROBOT_OPENER = re.compile(
    r"^\s*((here'?s the short version|quick take|in short|to put it simply|"
    r"simply put|in a nutshell|tl;?dr|alright|on zenk)"
    r"\s*[:—–-]?\s*)+",
    re.I,
)

_answer_cache: Dict[str, Tuple[float, dict]] = {}
_CACHE_TTL = 600.0  # seconds


def _system_prompt(first_turn: bool) -> str:
    # UI already greets once when the sheet opens — answers never re-greet.
    _ = first_turn
    return """You are Kia, ZenK Impact's warm, human-sounding landing guide (natural Indian English is welcome).
You sound like a thoughtful teammate explaining the product — never like a chatbot template.

ONLY answer using the PLATFORM CONTEXT below. Topics allowed:
- What ZenK is, Kizuna, circles, roles, waitlist / Founding Circles
- Scoring: ZenQ, ZEQ, ZQA, ZCQ, SPD, RAS and how the board shows effort → evidence
- Trust/escrow at a product level (process), demo on the landing page, privacy consent on the form

HARD REFUSALS (politely redirect to platform topics):
- Personal finance, investing, banking products, tax/legal/medical advice
- Guaranteed returns, fundraising strategy for unrelated ventures
- Anything not about ZenK the product

Style:
- English only. Short (2–4 sentences). Warm, specific, conversational.
- Never say Hi, Hello, Hey, Hi there, Namaste, or Good morning/afternoon.
- Never use robotic wrappers like “Here’s the short version”, “Quick take”, “In a nutshell”, or “TL;DR”.
- Open with a human reaction that fits the question, e.g. “Great question —”, “Interesting question —”, “Love that you asked —”, “That’s a really useful one —”, then explain in plain words.
- No inventing proprietary weights, secret formulas, or future dates you do not know.
- If context is thin, say what you do know and suggest registering interest or exploring the Impact scores demo.
- Never claim you can move money or open accounts.
"""


def _refuse_message(first_turn: bool = False) -> str:
    _ = first_turn
    return (
        "Interesting question — I stay with ZenK itself: circles, scoring, and how the platform works. "
        "I can’t help with personal finance or unrelated advice. "
        "Ask me about ZenQ, effort scores, or how a circle supports one student."
    )


def _apply_opener(body: str, first_turn: bool = False, salt: str = "") -> str:
    _ = first_turn
    text = body.strip()
    text = _GREETING_PREFIX.sub("", text).lstrip(" —–-").strip()
    text = _ROBOT_OPENER.sub("", text).lstrip(" —–-").strip()
    # Drop existing human openers so we don't double up
    low = text.lower()
    for o in _FOLLOW_OPENERS:
        stem = o.strip().lower().rstrip("—-: ")
        if stem and low.startswith(stem):
            text = text[len(stem) :].lstrip(" —–-").strip()
            low = text.lower()
            break
    idx = sum(ord(c) for c in (salt or text[:24])) % len(_FOLLOW_OPENERS)
    opener = _FOLLOW_OPENERS[idx]
    if not text:
        return opener.rstrip(" —")
    # Keep sentence case after the em dash
    return f"{opener}{text}"


def _postprocess(answer: str, first_turn: bool, salt: str) -> str:
    _ = first_turn
    text = _strip_think(answer).strip()
    text = _GREETING_PREFIX.sub("", text).lstrip(" —–-").strip()
    text = _ROBOT_OPENER.sub("", text).lstrip(" —–-").strip()
    if re.match(r"^(hi|hello|hey|namaste)\b", text, re.I):
        text = _GREETING_PREFIX.sub("", text).lstrip(" —–-").strip()
    return _apply_opener(text, salt=salt)


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) > 2}


def retrieve(question: str, k: int = 3) -> List[Tuple[float, KiaChunk]]:
    q = _tokens(question)
    if not q:
        return [(1.0, c) for c in LANDING_KIA_CHUNKS[:3]]

    scored: List[Tuple[float, KiaChunk]] = []
    low = question.lower()
    for chunk in LANDING_KIA_CHUNKS:
        bag = _tokens(chunk.title + " " + chunk.text + " " + " ".join(chunk.tags))
        overlap = len(q & bag)
        tag_hits = sum(
            1 for t in chunk.tags if any(tok in t.replace(" ", "") or t in low for tok in q)
        )
        phrase = 0.0
        for t in chunk.tags:
            if t in low:
                phrase += 2.5
        score = overlap + tag_hits * 1.5 + phrase
        if score > 0:
            scored.append((score, chunk))

    scored.sort(key=lambda x: x[0], reverse=True)
    if not scored:
        by_id = {c.id: c for c in LANDING_KIA_CHUNKS}
        return [
            (1.0, by_id["what-zenk"]),
            (1.0, by_id["scoring-overview"]),
            (1.0, by_id["circle"]),
        ]
    return scored[:k]


def _format_context(chunks: List[KiaChunk]) -> str:
    return "\n\n".join(f"### {c.title}\n{c.text}" for c in chunks)


def _fallback_from_chunks(chunks: List[KiaChunk], first_turn: bool = False) -> str:
    if not chunks:
        body = (
            "ZenK helps people form a circle around one student and make progress visible "
            "through scores like ZenQ, ZEQ, and ZQA. Ask about any score, or try the Impact scores demo."
        )
        salt = "x"
    else:
        body = chunks[0].text
        salt = chunks[0].id
    return _apply_opener(body, first_turn=first_turn, salt=salt)


def _strip_think(text: str) -> str:
    cleaned = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.I)
    cleaned = re.sub(r"</?think>", "", cleaned, flags=re.I)
    return cleaned.strip()


def _normalize_q(q: str) -> str:
    return re.sub(r"\s+", " ", q.strip().lower())


def _fast_answer(q: str) -> Optional[str]:
    key = _normalize_q(q)
    if key in _FAST:
        return _FAST[key]
    # loose: strip trailing punctuation
    key2 = key.rstrip("?.!")
    if key2 in _FAST:
        return _FAST[key2]
    for prompt in SUGGESTION_PROMPTS:
        if _normalize_q(prompt) == key or _normalize_q(prompt).rstrip("?.!") == key2:
            return _FAST.get(_normalize_q(prompt)) or _FAST.get(_normalize_q(prompt).rstrip("?.!"))
    return None


def _call_groq(system: str, user: str) -> Optional[str]:
    try:
        from groq import Groq
    except Exception as exc:
        logger.warning("Groq unavailable: %s", exc)
        return None

    api_key = (settings.groq_api_key or "").strip()
    if not api_key:
        return None

    client = Groq(api_key=api_key)
    model = (settings.groq_kia_model or "qwen/qwen3.6-27b").strip()
    try:
        kwargs = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.4,
            "max_tokens": 160,
        }
        if model.startswith("qwen/"):
            kwargs["reasoning_effort"] = "none"
        elif model.startswith("openai/gpt-oss"):
            kwargs["reasoning_effort"] = "low"

        resp = client.chat.completions.create(**kwargs)
        text = (resp.choices[0].message.content or "").strip()
        text = _strip_think(text)
        return text or None
    except Exception as exc:
        logger.warning("Landing Kia Groq failed: %s", exc)
        return None


def answer_question(question: str, *, first_turn: bool = False) -> dict:
    q = (question or "").strip()
    if len(q) < 2:
        return {
            "ok": False,
            "refused": False,
            "answer": "Ask me anything about ZenK — scoring, circles, or how interest registration works.",
            "chunk_ids": [],
            "fast": True,
        }

    if len(q) > 500:
        q = q[:500]

    cache_key = hashlib.sha256(f"{int(first_turn)}|{_normalize_q(q)}".encode()).hexdigest()
    cached = _answer_cache.get(cache_key)
    if cached and (time.time() - cached[0]) < _CACHE_TTL:
        return dict(cached[1])

    if _OFF_TOPIC.search(q):
        out = {
            "ok": True,
            "refused": True,
            "answer": _refuse_message(first_turn),
            "chunk_ids": [],
            "fast": True,
        }
        _answer_cache[cache_key] = (time.time(), out)
        return dict(out)

    # Instant path for known starters
    fast = _fast_answer(q)
    if fast:
        answer = _apply_opener(fast, first_turn, salt=_normalize_q(q))
        out = {
            "ok": True,
            "refused": False,
            "answer": answer,
            "chunk_ids": [],
            "fast": True,
        }
        _answer_cache[cache_key] = (time.time(), out)
        return dict(out)

    scored = retrieve(q, k=3)
    chunks = [c for _, c in scored]
    top_score = scored[0][0] if scored else 0

    # Strong retrieval → skip LLM
    if top_score >= 6 and chunks:
        answer = _apply_opener(chunks[0].text, first_turn, salt=chunks[0].id)
        out = {
            "ok": True,
            "refused": False,
            "answer": answer,
            "chunk_ids": [c.id for c in chunks],
            "fast": True,
        }
        _answer_cache[cache_key] = (time.time(), out)
        return dict(out)

    context = _format_context(chunks)
    user = (
        f"PLATFORM CONTEXT:\n{context}\n\n"
        f"VISITOR QUESTION:\n{q}\n\n"
        f"Answer as Kia. first_turn={first_turn}."
    )
    llm = _call_groq(_system_prompt(first_turn), user)
    if llm:
        answer = _postprocess(llm, first_turn, salt=chunks[0].id if chunks else q)
    else:
        answer = _fallback_from_chunks(chunks, first_turn)

    if llm and _OFF_TOPIC.search(llm) and not _OFF_TOPIC.search(q):
        answer = _fallback_from_chunks(chunks, first_turn)

    out = {
        "ok": True,
        "refused": False,
        "answer": answer.strip(),
        "chunk_ids": [c.id for c in chunks],
        "fast": False,
    }
    _answer_cache[cache_key] = (time.time(), out)
    return dict(out)
