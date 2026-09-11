"""Admin website traffic analytics (first-party)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_deps import require_admin_api_key
from app.db.session import get_db
from app.services.landing_analytics_store import (
    cta_leaderboard,
    get_session_timeline,
    list_recent_sessions,
    traffic_overview,
)

router = APIRouter(
    prefix="/admin/website-traffic",
    tags=["admin-website-traffic"],
    dependencies=[Depends(require_admin_api_key)],
)


@router.get("/overview")
async def get_traffic_overview(
    days: int = Query(default=7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
):
    return await traffic_overview(db, days=days)


@router.get("/ctas")
async def get_cta_leaderboard(
    days: int = Query(default=7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
):
    return {"days": days, "items": await cta_leaderboard(db, days=days)}


@router.get("/sessions")
async def get_recent_sessions(
    days: int = Query(default=7, ge=1, le=90),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    return {"days": days, "items": await list_recent_sessions(db, days=days, limit=limit)}


@router.get("/sessions/{session_id}")
async def get_session_detail(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    data = await get_session_timeline(db, session_id)
    if not data:
        raise HTTPException(status_code=404, detail="Session not found")
    return data
