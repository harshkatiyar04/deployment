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
        tags=("score", "scoring", "algorithm", "zenq", "board", "metrics", "pcs", "v2"),
        text=(
            "ZenQ is the product scoring system. Circle ZenQ (lifetime / this month / season) "
            "comes from scored activity on an event ledger. Your contribution is PCS (personal). "
            "ZQA is the student learning pulse; growth from the child’s own baseline informs G/SGI "
            "(it no longer multiplies circle stock as old SPD did). RAS rates chat quality."
        ),
    ),
    KiaChunk(
        id="zenq",
        title="ZenQ — Circle Impact",
        tags=("zenq", "ziq", "circle impact", "headline", "lifetime"),
        text=(
            "ZenQ is the circle’s cumulative impact — lifetime never resets; season resets each "
            "January; this month shows current earnings. It rises from sessions, thoughtful chat, "
            "targets, Kia, pledges, referrals, and sparks — not from student ZQA alone. "
            "Example: a circle moves milestone Seed → Sprout as people keep showing up."
        ),
    ),
    KiaChunk(
        id="pcs",
        title="PCS — Your contribution",
        tags=("pcs", "contribution", "member", "personal"),
        text=(
            "PCS (Your contribution) is each member’s own cumulative impact from attributed "
            "activity. It is not the same as circle Lifetime. Quiet months may fade PCS after "
            "long silence; the circle lifetime stock is not erased by a hard student quarter."
        ),
    ),
    KiaChunk(
        id="zeq",
        title="Effort (sessions & showing up)",
        tags=("zeq", "effort", "sponsor effort", "mentoring hours", "showing up", "presence"),
        text=(
            "Effort still matters in ZenQ as presence and learning events: mentoring time, "
            "kept promises, and meaningful participation. Showing up counts — quiet money alone "
            "does not define the score. Example: weekly sessions and targets keep presence IP moving."
        ),
    ),
    KiaChunk(
        id="zqa",
        title="ZQA — Learning Pulse",
        tags=("zqa", "learning", "academics", "student pulse", "report card", "sgi"),
        text=(
            "ZQA is the student learning pulse — more than a report card. It blends academics and "
            "related signals into a learning-health read. Growth from the student’s own baseline "
            "informs growth multiplier G and SGI bands. ZQA is never equal to circle ZenQ. "
            "Demo story: ZQA moved 54 → 62 as the circle supported the student."
        ),
    ),
    KiaChunk(
        id="zcq",
        title="Context (need band)",
        tags=("zcq", "context", "fairness", "need", "circumstances", "k"),
        text=(
            "Context fairness remains via the circle need band K — adjusting for the student’s "
            "real circumstances so harder journeys are not punished by a one-size curve. "
            "This is not the old ZCQ×SPD product formula."
        ),
    ),
    KiaChunk(
        id="spd",
        title="SPD — legacy name",
        tags=("spd", "progress", "delta", "baseline", "growth", "legacy"),
        text=(
            "SPD was the old circle multiplier that could shrink the whole ZenQ score. "
            "In ZenQ, student progress no longer multiplies lifetime stock that way. "
            "Progress from the child’s own baseline now informs growth G (≥ 1) and SGI narrative. "
            "School ZQA may still track progress vs baseline internally — that is not a public "
            "SPD card on the circle scoreboard."
        ),
    ),
    KiaChunk(
        id="ras",
        title="RAS — Mentorship Authenticity",
        tags=("ras", "chat", "message quality", "authenticity", "mentorship"),
        text=(
            "RAS rates whether guidance feels thoughtful and student-centred. Genuine messages rise; "
            "copy-paste check-ins do not. In ZenQ, better chat quality maps into chat impact "
            "points. Example: asking about algebra and suggesting one problem beats a generic "
            "‘hope you’re fine’ every week."
        ),
    ),
    KiaChunk(
        id="formula",
        title="How scores relate",
        tags=("formula", "multiply", "relation", "how scores work", "e"),
        text=(
            "ZenQ: scored activity → impact points → monthly earnings E (weighted, × need K × "
            "growth G) → lifetime and season. PCS is personal. Yield and return are display ratios "
            "for funders — they do not add back into IP. ZenK does not publish proprietary weights. "
            "Do not teach live ZIQ = ZEQ × ZCQ × SPD."
        ),
    ),
    KiaChunk(
        id="demo",
        title="Live scoring demo",
        tags=("demo", "try", "interactive", "join circle", "asha"),
        text=(
            "The landing page has an interactive Impact scores demo. You can join a demo circle "
            "(name stays on the page) and watch signals move when someone shows up — a preview of "
            "how the board responds to participation. Product scoring is ZenQ (lifetime, PCS, "
            "ZQA/SGI, RAS) — not the old SPD multiplier story."
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
    "What is PCS?",
    "Explain ZQA learning pulse",
    "What is SPD?",
    "What is RAS chat quality?",
    "What is a circle?",
    "Who can join?",
    "What am I committing to today?",
    "When does money move?",
    "How does the live demo work?",
    "What do mentors do?",
    "How do schools fit in?",
]
