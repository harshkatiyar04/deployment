"""Public first-party marketing analytics ingest (no auth)."""

import logging
import time
from collections import defaultdict
from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import limiter
from app.db.session import get_db
from app.services.landing_analytics_store import ingest_batch
from app.services.landing_visitor_meta import collect_visitor_meta

router = APIRouter(prefix="/analytics", tags=["analytics"])
logger = logging.getLogger(__name__)

# Soft per-session cap (in addition to SlowAPI IP limit)
_SESSION_HITS = defaultdict(list)
_SESSION_WINDOW_S = 60.0
_SESSION_MAX = 80


def _session_rate_ok(session_id: Optional[str]) -> bool:
    sid = (session_id or "").strip()
    if not sid:
        return True
    now = time.monotonic()
    bucket = _SESSION_HITS[sid]
    cutoff = now - _SESSION_WINDOW_S
    while bucket and bucket[0] < cutoff:
        bucket.pop(0)
    if len(bucket) >= _SESSION_MAX:
        return False
    bucket.append(now)
    if len(_SESSION_HITS) > 5000:
        for k in list(_SESSION_HITS.keys())[:500]:
            _SESSION_HITS.pop(k, None)
    return True


class VisitorMetaIn(BaseModel):
    session_id: Optional[str] = Field(default=None, max_length=64)
    referrer: Optional[str] = Field(default=None, max_length=2000)
    landing_path: Optional[str] = Field(default=None, max_length=500)
    utm_source: Optional[str] = Field(default=None, max_length=120)
    utm_medium: Optional[str] = Field(default=None, max_length=120)
    utm_campaign: Optional[str] = Field(default=None, max_length=120)
    timezone: Optional[str] = Field(default=None, max_length=80)
    screen: Optional[str] = Field(default=None, max_length=40)
    user_agent: Optional[str] = Field(default=None, max_length=2000)


class AnalyticsItemIn(BaseModel):
    type: str = Field(max_length=40)
    path: Optional[str] = Field(default=None, max_length=500)
    referrer: Optional[str] = Field(default=None, max_length=2000)
    cta_id: Optional[str] = Field(default=None, max_length=120)
    event_name: Optional[str] = Field(default=None, max_length=80)
    duration_ms: Optional[int] = Field(default=None, ge=0, le=3_600_000)
    scroll_pct: Optional[int] = Field(default=None, ge=0, le=100)
    meta: Optional[dict] = None


class AnalyticsCollectIn(BaseModel):
    visitor: VisitorMetaIn
    events: list[AnalyticsItemIn] = Field(default_factory=list, max_length=40)


class AnalyticsCollectOut(BaseModel):
    ok: bool = True
    pageviews: int = 0
    events: int = 0
    skipped: int = 0


@router.post("/collect", response_model=AnalyticsCollectOut, status_code=status.HTTP_200_OK)
@limiter.limit("480/hour")
async def collect_analytics(
    request: Request,
    payload: AnalyticsCollectIn = Body(...),
    db: AsyncSession = Depends(get_db),
) -> AnalyticsCollectOut:
    """Batch pageviews + CTA events. Designed for sendBeacon / keepalive."""
    purpose = (request.headers.get("purpose") or request.headers.get("sec-purpose") or "").lower()
    if "prefetch" in purpose:
        return AnalyticsCollectOut(ok=True, skipped=len(payload.events or []))

    if not _session_rate_ok(payload.visitor.session_id if payload.visitor else None):
        return AnalyticsCollectOut(ok=True, skipped=len(payload.events or []))

    try:
        meta = await collect_visitor_meta(request, client_meta=payload.visitor.model_dump())
        items = [e.model_dump() for e in (payload.events or [])]
        counts = await ingest_batch(db, visitor_meta=meta, items=items)
        return AnalyticsCollectOut(
            pageviews=counts.get("pageviews", 0),
            events=counts.get("events", 0),
            skipped=counts.get("skipped", 0),
        )
    except Exception:
        logger.exception("Analytics collect failed")
        return AnalyticsCollectOut(ok=True, skipped=len(payload.events or []))
