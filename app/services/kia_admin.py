"""Kia — ZenK platform admin advisor with live portal data and event feed."""

from __future__ import annotations

import json
import logging
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

_ADMIN_CONSTITUTION = """You are Kia, ZenK's Platform Admin Advisor.
You assist the ZenK operations admin managing sponsor circles, schools, vendors, KYC, safety, and spend.

YOUR ROLE:
- Summarize live platform metrics and queues that need human action.
- Prioritize what the admin should handle first (KYC, circle ops, SOS, uplift, safety).
- Explain circle membership, spend, and activity using only the Admin Context provided.
- Suggest concrete next steps with dashboard paths when relevant.

TONE: Calm, precise, operational. Respect the admin's time.

RULES:
1. Use ONLY data from Admin Context and Events — never invent counts or names.
2. When citing queues, mention exact numbers from context.
3. For sensitive removals or limits, remind that leader requests need admin approval.
4. Keep chat replies under 4 short paragraphs. Plain text only — no markdown bullets.
5. When recommending action, prefix: "Kia recommends: [text]"
6. Never expose passwords, API keys, or raw document content.

ADMIN PORTAL PATHS (for recommendations):
- /dashboard/signup-review — KYC queue
- /dashboard/circle-ops — circles, members, removal/limit requests
- /dashboard/uplift-queue — mentor uplift verification
- /dashboard/report-queue — SOS reports
- /dashboard/safety — flagged chat content
- /dashboard/chat-bans — active bans
- /dashboard — main overview
"""


def _build_admin_prompt(context: dict, events: list[dict]) -> str:
    prompt = _ADMIN_CONSTITUTION + "\n\n--- ADMIN CONTEXT (live) ---\n"
    prompt += json.dumps(context, indent=2, default=str)[:12000]
    prompt += "\n\n--- PRIORITY EVENTS ---\n"
    if events:
        for ev in events[:15]:
            prompt += f"- [{ev.get('severity','info').upper()}] {ev.get('title')}: {ev.get('detail')} (action: {ev.get('action_path','')})\n"
    else:
        prompt += "No urgent events right now.\n"
    return prompt


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
        "overview": overview,
        "pending_circle_ops": pending_ops[:10],
        "kyc_queue_sample": kyc_queue,
        "data_policy": "All figures are live from the database at request time.",
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
                "detail": f"{k['circles_new_this_month']} new circle(s) this month · {k.get('active_circles', 0)} active",
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


async def generate_admin_response(message: str, context: dict, events: list[dict]) -> Optional[str]:
    try:
        system_prompt = _build_admin_prompt(context, events)
        return await _call_llm(
            system_prompt=system_prompt,
            user_message=message,
            max_tokens=900,
            temperature=0.55,
        )
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
        text=text.strip(),
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
    events = await build_admin_portal_events(db)
    if events:
        top = events[0]
        text = (
            f"Welcome back. I'm Kia, your platform admin advisor. "
            f"Top priority: {top['title']} — {top['detail']}. "
            f"Ask me what needs attention or say 'summarize all portals'."
        )
    else:
        text = (
            "Welcome back. I'm Kia, your platform admin advisor. "
            "Queues look clear — ask me for circle activity, spend, or safety status anytime."
        )
    await post_admin_kia_briefing(db, text, event_type="welcome", action_path="/dashboard")
