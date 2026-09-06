"""Curated ZenK platform knowledge for landing Kia (English only).

Scope: product, circles, roles, scoring algorithms, waitlist, trust framing.
Out of scope: investment advice, personal finance, legal/tax, medical, politics.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class KiaChunk:
    id: str
    title: str
    tags: tuple[str, ...]
    text: str


LANDING_KIA_CHUNKS: List[KiaChunk] = [
    KiaChunk(
        id="what-zenk",
        title="What is ZenK",
        tags=("zenk", "what", "platform", "kizuna", "bond", "overview"),
        text=(
            "ZenK is a trust ecosystem where people form a circle around one student, "
            "support their growth, and make progress visible. The brand idea is Kizuna — "
            "a bond between people — to educate one child and measure the impact. "
            "It is not scattered charity; it is coordinated support with evidence."
        ),
    ),
    KiaChunk(
        id="circle",
        title="What is a circle",
        tags=("circle", "sponsor", "team", "around student"),
        text=(
            "A circle is a small group — sponsors, mentors, peers, and supporters — "
            "formed around one student. The circle shows up together so effort and "
            "progress are shared and visible on the dashboard."
        ),
    ),
    KiaChunk(
        id="roles",
        title="Roles on ZenK",
        tags=("role", "leader", "member", "mentor", "student", "school", "corporate", "parent"),
        text=(
            "People join as circle leaders or members, mentors, students, schools, "
            "parents/guardians, or corporate/CSR partners. On the interest form you can "
            "say leader, member, or not sure — there is no commitment at registration."
        ),
    ),
    KiaChunk(
        id="scoring-overview",
        title="Scoring overview",
        tags=("score", "scoring", "algorithm", "zenq", "board", "metrics", "six"),
        text=(
            "Six algorithms feed one impact board: ZenQ (circle impact), ZEQ (effort), "
            "ZQA (learning pulse), ZCQ (context), SPD (progress delta), and RAS "
            "(mentorship authenticity / chat quality). Together they show effort meeting evidence."
        ),
    ),
    KiaChunk(
        id="zenq",
        title="ZenQ — Circle Impact",
        tags=("zenq", "ziq", "circle impact", "headline"),
        text=(
            "ZenQ is the circle’s live impact grade — the headline score your circle sees. "
            "It rolls effort, context, and student growth into one score that updates as "
            "people show up and the child progresses. Example story: Developing → Strong "
            "after a term of consistent mentoring because growth became visible."
        ),
    ),
    KiaChunk(
        id="zeq",
        title="ZEQ — Effort",
        tags=("zeq", "effort", "sponsor effort", "mentoring hours", "showing up"),
        text=(
            "ZEQ tracks sponsor/circle effort: mentoring time, kept promises, meaningful chat, "
            "and how fairly effort is shared. Showing up counts — quiet money alone does not "
            "define the score. Example: four members and about twelve mentor hours with weekly "
            "check-ins keeps effort Active."
        ),
    ),
    KiaChunk(
        id="zqa",
        title="ZQA — Learning Pulse",
        tags=("zqa", "learning", "academics", "student pulse", "report card"),
        text=(
            "ZQA is the student learning pulse — more than a report card. It blends academics, "
            "deeper thinking, social-emotional growth, and attendance into one learning-health read. "
            "Demo story: ZQA moved 54 → 62 as the circle supported the student."
        ),
    ),
    KiaChunk(
        id="zcq",
        title="ZCQ — Context Quotient",
        tags=("zcq", "context", "fairness", "need", "circumstances"),
        text=(
            "ZCQ is context fairness. It adjusts for the student’s real circumstances — need level, "
            "attendance patterns, circle size — so harder journeys are not punished by a one-size curve."
        ),
    ),
    KiaChunk(
        id="spd",
        title="SPD — Progress Delta",
        tags=("spd", "progress", "delta", "baseline", "growth"),
        text=(
            "SPD measures how far the child moved from their own baseline — never against classmates "
            "or national ranks. Growth from where they started is what matters. Example: +8 points "
            "over six months is celebrated momentum."
        ),
    ),
    KiaChunk(
        id="ras",
        title="RAS — Mentorship Authenticity",
        tags=("ras", "chat", "message quality", "authenticity", "mentorship"),
        text=(
            "RAS rates whether guidance feels thoughtful and student-centred. Genuine messages rise; "
            "copy-paste check-ins do not. Example: asking about algebra and suggesting one problem "
            "beats a generic ‘hope you’re fine’ every week."
        ),
    ),
    KiaChunk(
        id="formula",
        title="How scores relate",
        tags=("formula", "multiply", "relation", "how scores work"),
        text=(
            "On the marketing story board, circle impact is framed as effort, context, and progress "
            "working together — often summarised as impact emerging from effort × context × progress. "
            "ZenK does not publish proprietary weights. Dashboards update as the circle shows up."
        ),
    ),
    KiaChunk(
        id="demo",
        title="Live scoring demo",
        tags=("demo", "try", "interactive", "join circle", "asha"),
        text=(
            "The landing page has an interactive Impact scores demo. You can join a demo circle "
            "(name stays on the page) and watch ZenQ, ZEQ, ZQA, ZCQ, SPD, and RAS move together "
            "when someone shows up — a preview of how the board responds to participation."
        ),
    ),
    KiaChunk(
        id="waitlist",
        title="Interest registration / Founding Circles",
        tags=("waitlist", "launch", "founding", "register", "interest", "commit"),
        text=(
            "Interest registration is open for Founding Circles. Registering interest is not a pledge, "
            "payment, or contract — no commitment today. After a short intro call, first circles form. "
            "A clear public launch date is shared as founding seats fill."
        ),
    ),
    KiaChunk(
        id="what-needed",
        title="What we need on the interest form",
        tags=("form", "fields", "privacy", "kyc", "pan", "password"),
        text=(
            "The interest form asks for name, email, mobile with country code, city and country, "
            "role, how many people you could bring, how you heard about ZenK, optional message, "
            "and privacy consent. No PAN, KYC, or password at this stage."
        ),
    ),
    KiaChunk(
        id="trust",
        title="Trust and safety framing",
        tags=("trust", "safety", "escrow", "audit", "funds", "protection"),
        text=(
            "ZenK emphasises trust and safety: founders do not casually touch circle funds; "
            "controlled escrow and audit trails are part of the design; students are protected. "
            "During interest registration, no contributions are collected. When circles open, "
            "funds move only through governed escrow against agreed support — visible and logged. "
            "Kia does not give investment, banking, or personal finance advice."
        ),
    ),
    KiaChunk(
        id="money-timing",
        title="When money moves",
        tags=("money", "payment", "contribute", "donate", "escrow timing"),
        text=(
            "No contributions are collected during interest registration. Money does not move before "
            "launch. When circles open, transfers happen through escrow with visibility and governance — "
            "not informal cash handoffs. Ask about product process, not investment returns."
        ),
    ),
    KiaChunk(
        id="mentor",
        title="Mentors and participation",
        tags=("mentor", "hours", "participation", "guidance"),
        text=(
            "Mentor hours and participation matter on the board. Participation reflects how consistently "
            "the circle shows up around the student. Mentors invest time in guidance — the demo board "
            "shows hours and participation rising when people engage."
        ),
    ),
    KiaChunk(
        id="school",
        title="Schools on ZenK",
        tags=("school", "teacher", "institution", "partner"),
        text=(
            "Schools can partner so learning signals and student progress connect into the circle view. "
            "ZQA draws on school-relevant learning health, not exam day alone. School interest can be "
            "registered on the same interest path."
        ),
    ),
    KiaChunk(
        id="corporate",
        title="Corporate / CSR",
        tags=("corporate", "csr", "company", "esg"),
        text=(
            "Corporate and CSR partners can support circles as part of structured impact — "
            "with visibility into effort and student progress rather than one-off donations. "
            "Register interest to explore partnership; Kia explains the product, not financial returns."
        ),
    ),
    KiaChunk(
        id="kia",
        title="Who is Kia",
        tags=("kia", "guide", "assistant", "help"),
        text=(
            "Kia is ZenK’s guide on the landing page. She explains the platform, circles, and scoring "
            "in clear English. She stays on product topics and will decline personal finance, legal, "
            "medical, or unrelated questions."
        ),
    ),
    KiaChunk(
        id="privacy",
        title="Privacy",
        tags=("privacy", "gdpr", "dpdp", "data", "consent"),
        text=(
            "Interest registration requires privacy consent aligned with applicable data protection "
            "expectations (including DPDP in India and UK GDPR framing where relevant). "
            "Read the privacy policy linked from the form for details."
        ),
    ),
]


SUGGESTION_PROMPTS: List[str] = [
    "What is ZenK?",
    "How does scoring work?",
    "What is ZenQ?",
    "What does ZEQ measure?",
    "Explain ZQA learning pulse",
    "What is ZCQ context?",
    "What is SPD progress delta?",
    "What is RAS chat quality?",
    "What is a circle?",
    "Who can join?",
    "What am I committing to today?",
    "When does money move?",
    "How does the live demo work?",
    "What do mentors do?",
    "How do schools fit in?",
]
