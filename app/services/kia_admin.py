"""Kia — ZenK platform admin advisor with live portal data and event feed."""

from __future__ import annotations

import logging
import re
import uuid
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin_kia import AdminKiaMessage
from app.models.enums import KycStatus
from app.models.signup import SignupRequest
from app.services.admin_dashboard_overview import build_admin_dashboard_overview
from app.services.circle_membership_ops import list_pending_admin_queue
from app.services.kia import _call_llm

logger = logging.getLogger(__name__)

_ADMIN_CONSTITUTION = """You are Kia, ZenK's Platform Admin Advisor for India.
You assist the ZenK operations admin managing sponsor circles, schools, vendors, KYC, safety, and spend.

CURRENCY (CRITICAL):
- ZenK money is ALWAYS Indian Rupees (INR).
- Write amounts as ₹2,49,000 or "₹2.49 lakh" — NEVER use $, USD, dollars, or £.
- If a figure in context is already labelled with ₹, copy that format.

YOUR ROLE:
- Answer with LIVE numbers from Admin Snapshot only — never invent or round into a different currency.
- When asked how many circles / total contributions / spend, quote the exact snapshot fields.
- Prioritize queues that need human action (KYC, circle ops, SOS, uplift, safety).
- Suggest concrete next steps with clickable portal paths.

TONE: Calm, precise, operational. Respect the admin's time.

RULES:
1. Use ONLY Admin Snapshot + Priority Events — never invent counts, names, or money.
2. Cite exact numbers from the snapshot (e.g. active_circles, total_contributions_inr).
3. Keep replies under 4 short paragraphs.
4. When recommending action, you MAY use: "Kia recommends: [text]"
5. Never expose passwords, API keys, or raw document content.
6. Portal paths MUST be markdown links so the UI can make them clickable, e.g.
   [Circle ops](/dashboard/circle-ops) — never bare paths without a link.

ADMIN PORTAL PATHS (use as markdown links):
- [Overview](/dashboard)
- [Signup & KYC](/dashboard/signup-review)
- [Circle ops](/dashboard/circle-ops)
- [Other requests](/dashboard/other-requests)
- [Uplift queue](/dashboard/uplift-queue)
- [SOS reports](/dashboard/report-queue)
- [Safety](/dashboard/safety)
- [Chat bans](/dashboard/chat-bans)
- [Suppliers](/dashboard/suppliers)
- [ZenQ observatory](/dashboard/zenq-lab)
"""


def _inr_indian(amount: Any) -> str:
    try:
        n = int(round(float(amount or 0)))
    except (TypeError, ValueError):
        n = 0
    if n < 0:
        return f"-{_inr_indian(-n)}"
    s = str(n)
    if len(s) <= 3:
        return f"₹{s}"
    last3 = s[-3:]
    rest = s[:-3]
    chunks: list[str] = []
    while rest:
        chunks.append(rest[-2:])
        rest = rest[:-2]
    return "₹" + ",".join(reversed(chunks)) + "," + last3


def _build_platform_snapshot(overview: dict[str, Any]) -> dict[str, Any]:
    k = overview.get("kpis") or {}
    q = overview.get("queues") or {}
    return {
        "currency": "INR (Indian Rupees) — NEVER use USD/$",
        "active_circles": int(k.get("active_circles") or 0),
        "circle_members": int(k.get("circle_members") or 0),
        "circles_new_this_month": int(k.get("circles_new_this_month") or 0),
        "total_users": int(k.get("total_users") or 0),
        "users_new_this_month": int(k.get("users_new_this_month") or 0),
        "total_contributions_inr": int(k.get("total_contributions") or 0),
        "total_contributions_display": _inr_indian(k.get("total_contributions") or 0),
        "circle_spend_total_inr": int(k.get("circle_spend_total") or 0),
        "circle_spend_total_display": _inr_indian(k.get("circle_spend_total") or 0),
        "marketplace_gmv_inr": float(k.get("marketplace_gmv") or 0),
        "marketplace_gmv_display": _inr_indian(k.get("marketplace_gmv") or 0),
        "gmv_mtd_display": _inr_indian(k.get("gmv_mtd") or 0),
        "suppliers_approved": int(k.get("suppliers_approved") or 0),
        "active_products": int(k.get("active_products") or 0),
        "time_this_month_minutes": int(k.get("circle_minutes_month") or 0),
        "queues": {
            "kyc_pending": int(q.get("kyc_pending") or 0),
            "circle_ops_pending": int(q.get("circle_ops_pending") or 0),
            "other_requests_pending": int(q.get("other_requests_pending") or 0),
            "uplift_pending": int(q.get("uplift_pending") or 0),
            "sos_open": int(q.get("sos_open") or 0),
            "chat_warned": int(q.get("chat_warned") or 0),
            "chat_bans": int(q.get("chat_bans") or 0),
        },
        "how_to_answer_examples": {
            "circles_question": (
                f"There are {int(k.get('active_circles') or 0)} circles on the platform."
            ),
            "contributions_question": (
                f"Total circle contributions collected so far: "
                f"{_inr_indian(k.get('total_contributions') or 0)}. "
                f"Total circle spend: {_inr_indian(k.get('circle_spend_total') or 0)}."
            ),
        },
    }


def _build_admin_prompt(context: dict, events: list[dict]) -> str:
    snapshot = context.get("platform_snapshot") or {}
    lines = [
        _ADMIN_CONSTITUTION,
        "",
        "--- ADMIN SNAPSHOT (live INR figures — source of truth) ---",
    ]
    for key, val in snapshot.items():
        if key == "how_to_answer_examples":
            continue
        if key == "queues" and isinstance(val, dict):
            lines.append("queues:")
            for qk, qv in val.items():
                lines.append(f"  {qk}: {qv}")
        else:
            lines.append(f"{key}: {val}")

    examples = snapshot.get("how_to_answer_examples") or {}
    if examples:
        lines.append("")
        lines.append("--- ANSWER STYLE (copy currency format) ---")
        for label, sample in examples.items():
            lines.append(f"{label}: {sample}")

    pending = context.get("pending_circle_ops") or []
    if pending:
        lines.append("")
        lines.append("--- PENDING CIRCLE OPS (sample) ---")
        for req in pending[:8]:
            lines.append(
                f"- {req.get('request_type')}: {req.get('circle_name')} "
                f"(leader={req.get('leader_name')}, status={req.get('status')})"
            )

    kyc = context.get("kyc_queue_sample") or []
    if kyc:
        lines.append("")
        lines.append("--- KYC QUEUE SAMPLE ---")
        for row in kyc[:6]:
            lines.append(f"- {row.get('name')} ({row.get('persona')})")

    lines.append("")
    lines.append("--- PRIORITY EVENTS ---")
    if events:
        for ev in events[:15]:
            path = ev.get("action_path") or ""
            lines.append(
                f"- [{str(ev.get('severity', 'info')).upper()}] {ev.get('title')}: "
                f"{ev.get('detail')} → link as [{ev.get('title')}]({path})"
            )
    else:
        lines.append("No urgent events right now.")

    return "\n".join(lines)


_DOLLAR_AMOUNT_RE = re.compile(
    r"\$\s*([0-9]{1,3}(?:,[0-9]{2,3})*(?:\.[0-9]+)?|[0-9]+(?:\.[0-9]+)?)\s*(k|K|lakh|L|cr|CR)?",
)
_BARE_DASHBOARD_PATH_RE = re.compile(
    r"(?<!\()(?<!\]\()(/dashboard(?:/[a-z0-9\-]+)*)",
    re.IGNORECASE,
)
_USD_WORD_RE = re.compile(r"\b(USD|US\$|dollars?)\b", re.IGNORECASE)


def format_admin_reply(text: Optional[str]) -> Optional[str]:
    """Force INR currency and ensure portal paths are markdown-linked."""
    if not text:
        return text
    cleaned = text.strip()

    def _dollar_to_inr(match: re.Match) -> str:
        raw = match.group(1).replace(",", "")
        suffix = (match.group(2) or "").lower()
        try:
            n = float(raw)
        except ValueError:
            return f"₹{match.group(1)}"
        if suffix == "k":
            n *= 1000
        elif suffix in ("l", "lakh"):
            n *= 100_000
        elif suffix in ("cr",):
            n *= 10_000_000
        return _inr_indian(n)

    cleaned = _DOLLAR_AMOUNT_RE.sub(_dollar_to_inr, cleaned)
    cleaned = _USD_WORD_RE.sub("INR", cleaned)

    # Linkify bare /dashboard/... paths that are not already markdown links.
    def _linkify_path(match: re.Match) -> str:
        path = match.group(1)
        label_map = {
            "/dashboard": "Overview",
            "/dashboard/signup-review": "Signup & KYC",
            "/dashboard/circle-ops": "Circle ops",
            "/dashboard/other-requests": "Other requests",
            "/dashboard/uplift-queue": "Uplift queue",
            "/dashboard/report-queue": "SOS reports",
            "/dashboard/safety": "Safety",
            "/dashboard/chat-bans": "Chat bans",
            "/dashboard/suppliers": "Suppliers",
            "/dashboard/zenq-observatory": "ZenQ observatory",
            "/dashboard/zenq-lab": "ZenQ observatory",
            "/dashboard/student-progress": "Student progress",
            "/dashboard/users": "Users",
            "/dashboard/legal": "Legal & terms",
            "/dashboard/suppliers": "Suppliers",
        }
        label = label_map.get(path.rstrip("/"), path.split("/")[-1].replace("-", " ").title())
        return f"[{label}]({path})"

    cleaned = _BARE_DASHBOARD_PATH_RE.sub(_linkify_path, cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned


async def fetch_admin_context(db: AsyncSession) -> dict[str, Any]:
    overview = await build_admin_dashboard_overview(db)
    pending_ops = await list_pending_admin_queue(db)

    kyc_pending_res = await db.execute(
        select(SignupRequest.full_name, SignupRequest.persona, SignupRequest.created_at)
        .where(SignupRequest.kyc_status == KycStatus.pending)
        .order_by(SignupRequest.created_at.desc())
        .limit(8)
    )
    kyc_queue = [
        {
            "name": name,
            "persona": p.value if hasattr(p, "value") else str(p),
            "submitted_at": created.isoformat() if created else None,
        }
        for name, p, created in kyc_pending_res.all()
    ]

    return {
        "platform_snapshot": _build_platform_snapshot(overview),
        "pending_circle_ops": pending_ops[:10],
        "kyc_queue_sample": kyc_queue,
        "data_policy": (
            "All figures are live from the database at request time. "
            "Money fields are INR. Prefer *_display strings when speaking to the admin."
        ),
    }


async def build_admin_portal_events(db: AsyncSession) -> list[dict[str, Any]]:
    overview = await build_admin_dashboard_overview(db)
    q = overview.get("queues") or {}
    k = overview.get("kpis") or {}
    events: list[dict[str, Any]] = []

    if q.get("kyc_pending", 0) > 0:
        events.append(
            {
                "id": "kyc-pending",
                "severity": "high" if q["kyc_pending"] >= 5 else "medium",
                "title": "KYC reviews pending",
                "detail": f"{q['kyc_pending']} signup(s) awaiting approval",
                "action_path": "/dashboard/signup-review",
                "event_type": "kyc_pending",
            }
        )

    if q.get("circle_ops_pending", 0) > 0:
        from app.services.circle_membership_ops import list_pending_membership_ops_queue

        pending = await list_pending_membership_ops_queue(db)
        for req in pending[:5]:
            label = (
                f"Remove {req.get('target_user_name')} from {req.get('circle_name')}"
                if req.get("request_type") == "member_removal"
                else f"Raise {req.get('circle_name')} limit to {req.get('requested_limit')}"
            )
            events.append(
                {
                    "id": req.get("id"),
                    "severity": "high",
                    "title": "Circle ops request",
                    "detail": label,
                    "action_path": "/dashboard/circle-ops",
                    "event_type": req.get("request_type"),
                    "at": req.get("created_at"),
                }
            )

    if q.get("other_requests_pending", 0) > 0:
        from app.services.circle_membership_ops import list_pending_other_requests_queue

        other = await list_pending_other_requests_queue(db)
        for req in other[:5]:
            if req.get("request_type") == "circle_rename":
                detail = (
                    f"Rename {req.get('circle_name')}: "
                    f"{req.get('current_circle_name')} → {req.get('requested_circle_name')}"
                )
            else:
                detail = req.get("leader_comment") or "Leader request"
            events.append(
                {
                    "id": req.get("id"),
                    "severity": "medium",
                    "title": "Other request",
                    "detail": detail,
                    "action_path": "/dashboard/other-requests",
                    "event_type": req.get("request_type"),
                    "at": req.get("created_at"),
                }
            )

    if q.get("sos_open", 0) > 0:
        events.append(
            {
                "id": "sos-open",
                "severity": "high",
                "title": "Open SOS reports",
                "detail": f"{q['sos_open']} student SOS report(s) unresolved",
                "action_path": "/dashboard/report-queue",
                "event_type": "sos_open",
            }
        )

    if q.get("chat_warned", 0) > 0:
        events.append(
            {
                "id": "chat-warned",
                "severity": "medium",
                "title": "Flagged chat messages",
                "detail": f"{q['chat_warned']} message(s) flagged by AI shield",
                "action_path": "/dashboard/safety",
                "event_type": "chat_warned",
            }
        )

    if q.get("uplift_pending", 0) > 0:
        events.append(
            {
                "id": "uplift-pending",
                "severity": "medium",
                "title": "Mentor uplift queue",
                "detail": f"{q['uplift_pending']} community action(s) need verification",
                "action_path": "/dashboard/uplift-queue",
                "event_type": "uplift_pending",
            }
        )

    if k.get("circles_new_this_month", 0) > 0:
        events.append(
            {
                "id": "circles-growth",
                "severity": "info",
                "title": "Circle growth",
                "detail": (
                    f"{k['circles_new_this_month']} new circle(s) this month · "
                    f"{k.get('active_circles', 0)} active · "
                    f"contributions {_inr_indian(k.get('total_contributions') or 0)}"
                ),
                "action_path": "/dashboard/circle-ops",
                "event_type": "circle_growth",
            }
        )

    for item in (overview.get("recent_activity") or [])[:4]:
        events.append(
            {
                "id": f"activity-{item.get('at')}-{item.get('type')}",
                "severity": "info",
                "title": item.get("action") or "Platform activity",
                "detail": item.get("subject") or "",
                "action_path": "/dashboard",
                "event_type": item.get("type"),
                "at": item.get("at"),
            }
        )

    return events


async def generate_admin_response(
    message: str,
    context: dict,
    events: list[dict],
    history: Optional[list] = None,
) -> Optional[str]:
    try:
        system_prompt = _build_admin_prompt(context, events)
        reply = await _call_llm(
            system_prompt=system_prompt,
            user_message=message,
            history=history,
            max_tokens=900,
            temperature=0.35,
        )
        return format_admin_reply(reply)
    except Exception as exc:
        logger.error("kia_admin LLM error: %s", exc)
        return None


async def post_admin_kia_briefing(
    db: AsyncSession,
    text: str,
    *,
    event_type: Optional[str] = None,
    action_path: Optional[str] = None,
) -> AdminKiaMessage:
    row = AdminKiaMessage(
        id=str(uuid.uuid4()),
        role="kia",
        text=format_admin_reply(text.strip()) or text.strip(),
        event_type=event_type,
        action_path=action_path,
    )
    db.add(row)
    await db.flush()
    return row


async def seed_welcome_if_empty(db: AsyncSession) -> None:
    res = await db.execute(select(AdminKiaMessage.id).limit(1))
    if res.scalar_one_or_none():
        return
    await post_admin_kia_briefing(
        db,
        "I'm Kia, your platform admin advisor. Ask about circles, KYC queues, "
        "safety, or spend — I'll answer with live INR figures and portal links like "
        "[Circle ops](/dashboard/circle-ops).",
        event_type="welcome",
        action_path="/dashboard",
    )
