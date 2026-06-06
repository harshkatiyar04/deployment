"""Admin Kia — live portal advisor (admin API key required)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_deps import require_admin_api_key
from app.db.session import get_db
from app.models.admin_kia import AdminKiaMessage
from app.services.kia_admin import (
    build_admin_portal_events,
    fetch_admin_context,
    generate_admin_response,
    post_admin_kia_briefing,
    seed_welcome_if_empty,
)

router = APIRouter(
    prefix="/admin/kia",
    tags=["admin-kia"],
    dependencies=[Depends(require_admin_api_key)],
)


class AdminKiaMessageOut(BaseModel):
    id: str
    role: str
    text: str
    event_type: Optional[str] = None
    action_path: Optional[str] = None
    created_at: Optional[str] = None


class AdminPortalEventOut(BaseModel):
    id: str
    severity: str
    title: str
    detail: str
    action_path: str
    event_type: Optional[str] = None
    at: Optional[str] = None


class AdminKiaChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)


class AdminKiaChatResponse(BaseModel):
    reply: str
    message_id: str


@router.get("/events", response_model=list[AdminPortalEventOut])
async def list_admin_portal_events(db: AsyncSession = Depends(get_db)):
    events = await build_admin_portal_events(db)
    return [AdminPortalEventOut(**e) for e in events]


@router.get("/history", response_model=list[AdminKiaMessageOut])
async def admin_kia_history(db: AsyncSession = Depends(get_db)):
    await seed_welcome_if_empty(db)
    await db.commit()
    res = await db.execute(
        select(AdminKiaMessage).order_by(AdminKiaMessage.created_at.asc()).limit(80)
    )
    rows = res.scalars().all()
    return [
        AdminKiaMessageOut(
            id=r.id,
            role=r.role,
            text=r.text,
            event_type=r.event_type,
            action_path=r.action_path,
            created_at=r.created_at.isoformat() if r.created_at else None,
        )
        for r in rows
    ]


@router.post("/chat", response_model=AdminKiaChatResponse)
async def admin_kia_chat(body: AdminKiaChatRequest, db: AsyncSession = Depends(get_db)):
    msg = (body.message or "").strip()
    if not msg:
        raise HTTPException(status_code=400, detail="Message is required.")

    db.add(AdminKiaMessage(role="user", text=msg))
    await db.flush()

    context = await fetch_admin_context(db)
    events = await build_admin_portal_events(db)
    reply = await generate_admin_response(msg, context, events)
    if not reply:
        raise HTTPException(status_code=503, detail="Kia is temporarily unavailable.")

    kia_row = await post_admin_kia_briefing(db, reply, event_type="chat_reply")
    await db.commit()
    return AdminKiaChatResponse(reply=reply, message_id=kia_row.id)


@router.post("/briefing", response_model=AdminKiaMessageOut)
async def refresh_admin_briefing(db: AsyncSession = Depends(get_db)):
    """Proactive briefing from current queues (posts to history)."""
    events = await build_admin_portal_events(db)
    if not events:
        text = "All clear — no urgent portal queues. Circles, KYC, safety, and uplift are within normal limits."
    else:
        lines = [f"{e['title']}: {e['detail']}" for e in events[:6]]
        text = "Priority briefing — " + " | ".join(lines)
    row = await post_admin_kia_briefing(
        db, text, event_type="briefing", action_path="/dashboard"
    )
    await db.commit()
    return AdminKiaMessageOut(
        id=row.id,
        role=row.role,
        text=row.text,
        event_type=row.event_type,
        action_path=row.action_path,
        created_at=row.created_at.isoformat() if row.created_at else None,
    )
