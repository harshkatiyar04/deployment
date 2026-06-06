"""Zenk Admin — persistent 1:1 support threads."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.admin_support import ZENK_ADMIN_CHANNEL_NAME, ZenkAdminMessage, ZenkAdminThread
from app.models.signup import SignupRequest

PERSONA_LABELS = {
    "sponsor": "Sponsor",
    "sponsor_leader": "Sponsor leader",
    "sponsor_member": "Sponsor member",
    "vendor": "Vendor",
    "student": "Student",
    "corporate": "Corporate",
    "mentor": "Mentor",
    "school": "School",
}


def _iso(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


async def get_or_create_thread(db: AsyncSession, user_id: str) -> ZenkAdminThread:
    res = await db.execute(
        select(ZenkAdminThread).where(ZenkAdminThread.user_id == user_id)
    )
    thread = res.scalar_one_or_none()
    if thread:
        return thread
    thread = ZenkAdminThread(id=str(uuid.uuid4()), user_id=user_id)
    db.add(thread)
    await db.flush()
    return thread


def _thread_row(thread: ZenkAdminThread, user: SignupRequest) -> dict[str, Any]:
    persona = user.persona.value if hasattr(user.persona, "value") else str(user.persona)
    return {
        "thread_id": thread.id,
        "user_id": user.id,
        "user_name": user.full_name,
        "user_email": user.email,
        "user_mobile": user.mobile,
        "persona": persona,
        "persona_label": PERSONA_LABELS.get(persona, persona),
        "channel_name": ZENK_ADMIN_CHANNEL_NAME,
        "admin_unread_count": thread.admin_unread_count or 0,
        "last_message_text": thread.last_message_text,
        "last_message_at": _iso(thread.last_message_at),
        "has_messages": bool(thread.last_message_at),
    }


async def list_support_contacts(
    db: AsyncSession,
    *,
    search: Optional[str] = None,
    persona: Optional[str] = None,
    limit: int = 40,
) -> list[dict[str, Any]]:
    q = (
        select(SignupRequest, ZenkAdminThread)
        .outerjoin(ZenkAdminThread, ZenkAdminThread.user_id == SignupRequest.id)
        .where(SignupRequest.email != "admin@zenk")
        .order_by(SignupRequest.full_name)
        .limit(limit)
    )
    if persona and persona != "all":
        from app.models.enums import Persona

        try:
            q = q.where(SignupRequest.persona == Persona(persona))
        except ValueError:
            pass
    needle = (search or "").strip().lower()
    if needle:
        q = q.where(
            SignupRequest.full_name.ilike(f"%{needle}%")
            | SignupRequest.email.ilike(f"%{needle}%")
            | SignupRequest.mobile.ilike(f"%{needle}%")
        )
    res = await db.execute(q)
    out = []
    for user, thread in res.all():
        if user.email == "kia@zenk.ai":
            continue
        p = user.persona.value if hasattr(user.persona, "value") else str(user.persona)
        out.append(
            {
                "user_id": user.id,
                "user_name": user.full_name,
                "user_email": user.email,
                "user_mobile": user.mobile or "",
                "persona": p,
                "persona_label": PERSONA_LABELS.get(p, p),
                "thread_id": thread.id if thread else None,
                "has_thread": thread is not None,
                "has_messages": bool(thread and thread.last_message_at),
                "admin_unread_count": (thread.admin_unread_count or 0) if thread else 0,
            }
        )
    return out


async def open_admin_thread(db: AsyncSession, user_id: str) -> dict[str, Any]:
    res = await db.execute(select(SignupRequest).where(SignupRequest.id == user_id))
    user = res.scalar_one_or_none()
    if not user:
        raise ValueError("User not found.")
    thread = await get_or_create_thread(db, user_id)
    return _thread_row(thread, user)


async def list_admin_threads(db: AsyncSession, *, limit: int = 100) -> list[dict[str, Any]]:
    res = await db.execute(
        select(ZenkAdminThread, SignupRequest)
        .join(SignupRequest, SignupRequest.id == ZenkAdminThread.user_id)
        .order_by(ZenkAdminThread.last_message_at.desc().nullslast(), ZenkAdminThread.created_at.desc())
        .limit(limit)
    )
    return [_thread_row(thread, user) for thread, user in res.all()]


async def get_thread_messages(
    db: AsyncSession,
    *,
    thread_id: str,
    mark_read_for: Optional[str] = None,
) -> list[dict[str, Any]]:
    res = await db.execute(
        select(ZenkAdminMessage)
        .where(ZenkAdminMessage.thread_id == thread_id)
        .order_by(ZenkAdminMessage.created_at.asc())
        .limit(500)
    )
    messages = res.scalars().all()

    if mark_read_for == "admin":
        thread_res = await db.execute(
            select(ZenkAdminThread).where(ZenkAdminThread.id == thread_id)
        )
        thread = thread_res.scalar_one_or_none()
        if thread and thread.admin_unread_count:
            thread.admin_unread_count = 0
            thread.updated_at = datetime.now(timezone.utc)
    elif mark_read_for == "user":
        thread_res = await db.execute(
            select(ZenkAdminThread).where(ZenkAdminThread.id == thread_id)
        )
        thread = thread_res.scalar_one_or_none()
        if thread and thread.user_unread_count:
            thread.user_unread_count = 0
            thread.updated_at = datetime.now(timezone.utc)

    return [_message_row(m) for m in messages]


def _message_row(m: ZenkAdminMessage) -> dict[str, Any]:
    return {
        "id": m.id,
        "sender_role": m.sender_role,
        "text": m.text or "",
        "attachment_url": m.attachment_url,
        "attachment_type": m.attachment_type,
        "created_at": _iso(m.created_at),
    }


async def post_thread_message(
    db: AsyncSession,
    *,
    thread_id: str,
    sender_role: str,
    text: str,
    attachment_url: Optional[str] = None,
    attachment_type: Optional[str] = None,
) -> dict[str, Any]:
    body = (text or "").strip()
    attach = (attachment_url or "").strip() or None
    if not body and not attach:
        raise ValueError("Message cannot be empty.")
    if sender_role not in ("user", "admin"):
        raise ValueError("Invalid sender role.")

    thread_res = await db.execute(
        select(ZenkAdminThread).where(ZenkAdminThread.id == thread_id)
    )
    thread = thread_res.scalar_one_or_none()
    if not thread:
        raise ValueError("Thread not found.")

    msg = ZenkAdminMessage(
        id=str(uuid.uuid4()),
        thread_id=thread_id,
        sender_role=sender_role,
        text=body,
        attachment_url=attach,
        attachment_type=(attachment_type or None) if attach else None,
    )
    db.add(msg)

    now = datetime.now(timezone.utc)
    preview = body[:500] if body else f"[{(attachment_type or 'attachment').capitalize()}]"
    thread.last_message_text = preview[:500]
    thread.last_message_at = now
    thread.updated_at = now
    if sender_role == "user":
        thread.admin_unread_count = (thread.admin_unread_count or 0) + 1
    else:
        thread.user_unread_count = (thread.user_unread_count or 0) + 1

    await db.flush()
    return _message_row(msg)


async def get_user_support_state(db: AsyncSession, user: SignupRequest) -> dict[str, Any]:
    thread = await get_or_create_thread(db, user.id)
    persona = user.persona.value if hasattr(user.persona, "value") else str(user.persona)
    return {
        "thread_id": thread.id,
        "channel_name": ZENK_ADMIN_CHANNEL_NAME,
        "user_unread_count": thread.user_unread_count,
        "persona_label": PERSONA_LABELS.get(persona, persona),
    }


async def admin_support_summary(db: AsyncSession) -> dict[str, int]:
    res = await db.execute(select(ZenkAdminThread))
    threads = res.scalars().all()
    return {
        "total_threads": len(threads),
        "unread_threads": sum(1 for t in threads if (t.admin_unread_count or 0) > 0),
        "unread_messages": sum(t.admin_unread_count or 0 for t in threads),
    }
