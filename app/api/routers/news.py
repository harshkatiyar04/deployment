from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.jwt_auth import get_current_user
from app.models.signup import SignupRequest
from app.services.circle_budget import resolve_user_circle
from app.services.impact_briefing import build_briefing_feed_for_circle, fetch_impact_briefing

router = APIRouter(prefix="/news", tags=["news"])


@router.get("/briefing")
async def get_impact_briefing(
    refresh: bool = Query(False),
    circle_id: str | None = Query(None),
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Impact briefing: Zenk circle insights + filtered India education/charity RSS.
    No Guardian API, no mock articles.
    """
    if circle_id:
        circle, _ = await resolve_user_circle(db, user.id, circle_id)
        return await build_briefing_feed_for_circle(db, circle, force_refresh=refresh)
    return await fetch_impact_briefing(force_refresh=refresh)


@router.get("/impact")
async def get_impact_news(
    refresh: bool = Query(False),
    circle_id: str | None = Query(None),
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Alias for /news/briefing."""
    if circle_id:
        circle, _ = await resolve_user_circle(db, user.id, circle_id)
        return await build_briefing_feed_for_circle(db, circle, force_refresh=refresh)
    return await fetch_impact_briefing(force_refresh=refresh)
