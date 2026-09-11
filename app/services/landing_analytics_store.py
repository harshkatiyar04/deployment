"""Persist and query first-party marketing analytics."""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import and_, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.datetime_utils import to_utc_iso
from app.models.landing_analytics import LandingEvent, LandingPageview, LandingSession
from app.models.landing_contact import LandingContactInquiry
from app.models.landing_feedback import LandingFeedbackSubmission

_BOT_RE = re.compile(
    r"(bot|crawl|spider|slurp|facebookexternalhit|preview|headless|phantom|selenium|wget|curl)",
    re.I,
)

_CTA_DEBOUNCE = timedelta(milliseconds=800)
_FUNNEL_DEBOUNCE = timedelta(seconds=8)
_MIN_ABANDON_MS = 2500


def _is_bot(ua: Optional[str]) -> bool:
    if not ua:
        return False
    return bool(_BOT_RE.search(ua))


def _device_class(ua: Optional[str], screen: Optional[str]) -> str:
    u = (ua or "").lower()
    if "ipad" in u or "tablet" in u:
        return "tablet"
    if "mobi" in u or "android" in u and "mobile" in u:
        return "mobile"
    if screen:
        try:
            w = int(str(screen).split("x")[0])
            if w and w < 768:
                return "mobile"
            if w and w < 1100:
                return "tablet"
        except Exception:
            pass
    return "desktop"


def _parse_days(days: int) -> datetime:
    d = max(1, min(int(days or 7), 90))
    return datetime.now(timezone.utc) - timedelta(days=d)


async def upsert_session(
    db: AsyncSession,
    *,
    visitor_meta: dict[str, Any],
    path: Optional[str] = None,
) -> Optional[LandingSession]:
    session_id = (visitor_meta.get("session_id") or "").strip()
    if not session_id:
        return None
    if _is_bot(visitor_meta.get("user_agent")):
        return None

    now = datetime.now(timezone.utc)
    row = (
        await db.execute(
            select(LandingSession).where(LandingSession.session_id == session_id)
        )
    ).scalar_one_or_none()

    if row is None:
        row = LandingSession(
            session_id=session_id,
            first_seen_at=now,
            last_seen_at=now,
            entry_path=path or visitor_meta.get("landing_path"),
            referrer=visitor_meta.get("referrer"),
            utm_source=visitor_meta.get("utm_source"),
            utm_medium=visitor_meta.get("utm_medium"),
            utm_campaign=visitor_meta.get("utm_campaign"),
            ip_address=visitor_meta.get("ip_address"),
            user_agent=visitor_meta.get("user_agent"),
            accept_language=visitor_meta.get("accept_language"),
            timezone=visitor_meta.get("timezone"),
            screen=visitor_meta.get("screen"),
            device_class=_device_class(
                visitor_meta.get("user_agent"), visitor_meta.get("screen")
            ),
            geo_country=visitor_meta.get("geo_country"),
            geo_region=visitor_meta.get("geo_region"),
            geo_city=visitor_meta.get("geo_city"),
            pageview_count=0,
            event_count=0,
        )
        db.add(row)
    else:
        row.last_seen_at = now
        if not row.utm_source and visitor_meta.get("utm_source"):
            row.utm_source = visitor_meta.get("utm_source")
            row.utm_medium = visitor_meta.get("utm_medium")
            row.utm_campaign = visitor_meta.get("utm_campaign")
        if not row.geo_country and visitor_meta.get("geo_country"):
            row.geo_country = visitor_meta.get("geo_country")
            row.geo_region = visitor_meta.get("geo_region")
            row.geo_city = visitor_meta.get("geo_city")
    return row


async def record_pageview(
    db: AsyncSession,
    *,
    visitor_meta: dict[str, Any],
    path: str,
    referrer: Optional[str] = None,
    duration_ms: Optional[int] = None,
    scroll_pct: Optional[int] = None,
) -> Optional[LandingPageview]:
    session = await upsert_session(db, visitor_meta=visitor_meta, path=path)
    if session is None:
        return None
    clean_path = (path or "/").strip()[:500] or "/"
    # Deduplicate Strict Mode / double-beacon pageviews
    recent_cut = datetime.now(timezone.utc) - timedelta(seconds=3)
    recent = (
        await db.execute(
            select(LandingPageview.id)
            .where(LandingPageview.session_id == session.session_id)
            .where(LandingPageview.path == clean_path)
            .where(LandingPageview.started_at >= recent_cut)
            .limit(1)
        )
    ).scalar_one_or_none()
    if recent:
        return None
    pv = LandingPageview(
        session_id=session.session_id,
        path=clean_path,
        referrer=(referrer or visitor_meta.get("referrer") or None),
        duration_ms=duration_ms if duration_ms is not None and duration_ms >= 0 else None,
        scroll_pct=(
            max(0, min(100, int(scroll_pct)))
            if scroll_pct is not None
            else None
        ),
        utm_source=visitor_meta.get("utm_source"),
        utm_medium=visitor_meta.get("utm_medium"),
        utm_campaign=visitor_meta.get("utm_campaign"),
    )
    db.add(pv)
    session.pageview_count = int(session.pageview_count or 0) + 1
    return pv


async def record_event(
    db: AsyncSession,
    *,
    visitor_meta: dict[str, Any],
    event_name: str,
    cta_id: Optional[str] = None,
    path: Optional[str] = None,
    meta: Optional[dict] = None,
) -> Optional[LandingEvent]:
    session = await upsert_session(db, visitor_meta=visitor_meta, path=path)
    if session is None:
        return None

    name = (event_name or "").strip()[:80] or "event"
    cid = (cta_id or "").strip()[:120] or None
    clean_path = (path or visitor_meta.get("landing_path") or None)
    if clean_path:
        clean_path = str(clean_path)[:500]

    # Debounce duplicate CTA clicks
    if name == "cta_click" and cid:
        cutoff = datetime.now(timezone.utc) - _CTA_DEBOUNCE
        dup = (
            await db.execute(
                select(LandingEvent.id)
                .where(LandingEvent.session_id == session.session_id)
                .where(LandingEvent.event_name == "cta_click")
                .where(LandingEvent.cta_id == cid)
                .where(LandingEvent.created_at >= cutoff)
                .limit(1)
            )
        ).scalar_one_or_none()
        if dup:
            return None

    # Funnel noise: React Strict Mode / remount double-fires
    if name in ("interest_view", "interest_start", "interest_abandon", "interest_complete"):
        if name == "interest_abandon" and isinstance(meta, dict):
            try:
                dur = int(meta.get("duration_ms") or 0)
            except (TypeError, ValueError):
                dur = 0
            if dur and dur < _MIN_ABANDON_MS:
                return None
        funnel_cut = datetime.now(timezone.utc) - _FUNNEL_DEBOUNCE
        funnel_dup = (
            await db.execute(
                select(LandingEvent.id)
                .where(LandingEvent.session_id == session.session_id)
                .where(LandingEvent.event_name == name)
                .where(LandingEvent.created_at >= funnel_cut)
                .limit(1)
            )
        ).scalar_one_or_none()
        if funnel_dup:
            return None

    ev = LandingEvent(
        session_id=session.session_id,
        event_name=name,
        cta_id=cid,
        path=clean_path,
        meta_json=json.dumps(meta)[:4000] if meta else None,
    )
    db.add(ev)
    session.event_count = int(session.event_count or 0) + 1
    return ev


async def complete_pageview(
    db: AsyncSession,
    *,
    visitor_meta: dict[str, Any],
    path: str,
    duration_ms: Optional[int] = None,
    scroll_pct: Optional[int] = None,
) -> bool:
    """Attach duration/scroll to the latest matching pageview for this session."""
    session_id = (visitor_meta.get("session_id") or "").strip()
    if not session_id or _is_bot(visitor_meta.get("user_agent")):
        return False
    clean_path = (path or "/").strip()[:500] or "/"
    row = (
        await db.execute(
            select(LandingPageview)
            .where(LandingPageview.session_id == session_id)
            .where(LandingPageview.path == clean_path)
            .order_by(LandingPageview.started_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if not row:
        return False
    if duration_ms is not None and duration_ms >= 0:
        row.duration_ms = min(int(duration_ms), 3_600_000)
    if scroll_pct is not None:
        row.scroll_pct = max(0, min(100, int(scroll_pct)))
    sess = (
        await db.execute(
            select(LandingSession).where(LandingSession.session_id == session_id)
        )
    ).scalar_one_or_none()
    if sess:
        sess.last_seen_at = datetime.now(timezone.utc)
    return True


async def ingest_batch(
    db: AsyncSession,
    *,
    visitor_meta: dict[str, Any],
    items: list[dict[str, Any]],
) -> dict[str, int]:
    """Process a batch of pageview / event payloads. Returns counts."""
    recorded_pv = 0
    recorded_ev = 0
    skipped = 0

    if _is_bot(visitor_meta.get("user_agent")):
        return {"pageviews": 0, "events": 0, "skipped": len(items)}

    for raw in items[:40]:
        kind = (raw.get("type") or raw.get("kind") or "").strip().lower()
        if kind in ("pageview", "page_view", "pv"):
            path = (raw.get("path") or visitor_meta.get("landing_path") or "/").strip()
            pv = await record_pageview(
                db,
                visitor_meta=visitor_meta,
                path=path,
                referrer=raw.get("referrer"),
                duration_ms=raw.get("duration_ms"),
                scroll_pct=raw.get("scroll_pct"),
            )
            if pv:
                recorded_pv += 1
            else:
                skipped += 1
        elif kind in ("pageview_complete", "page_leave", "page_complete"):
            path = (raw.get("path") or visitor_meta.get("landing_path") or "/").strip()
            ok = await complete_pageview(
                db,
                visitor_meta=visitor_meta,
                path=path,
                duration_ms=raw.get("duration_ms"),
                scroll_pct=raw.get("scroll_pct"),
            )
            if not ok:
                skipped += 1
        elif kind in ("cta_click", "click", "event"):
            ev = await record_event(
                db,
                visitor_meta=visitor_meta,
                event_name=raw.get("event_name") or "cta_click",
                cta_id=raw.get("cta_id") or raw.get("id"),
                path=raw.get("path"),
                meta=raw.get("meta") if isinstance(raw.get("meta"), dict) else None,
            )
            if ev:
                recorded_ev += 1
            else:
                skipped += 1
        else:
            skipped += 1

    await db.commit()
    return {"pageviews": recorded_pv, "events": recorded_ev, "skipped": skipped}


async def traffic_overview(db: AsyncSession, *, days: int = 7) -> dict:
    cutoff = _parse_days(days)
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    sessions_total = (
        await db.execute(
            select(func.count())
            .select_from(LandingSession)
            .where(LandingSession.first_seen_at >= cutoff)
        )
    ).scalar_one()
    sessions_today = (
        await db.execute(
            select(func.count())
            .select_from(LandingSession)
            .where(LandingSession.first_seen_at >= today_start)
        )
    ).scalar_one()
    pageviews_total = (
        await db.execute(
            select(func.count())
            .select_from(LandingPageview)
            .where(LandingPageview.started_at >= cutoff)
        )
    ).scalar_one()
    unique_sessions_pv = (
        await db.execute(
            select(func.count(func.distinct(LandingPageview.session_id)))
            .where(LandingPageview.started_at >= cutoff)
        )
    ).scalar_one()
    cta_clicks = (
        await db.execute(
            select(func.count())
            .select_from(LandingEvent)
            .where(LandingEvent.event_name == "cta_click")
            .where(LandingEvent.created_at >= cutoff)
        )
    ).scalar_one()

    waitlist_submits = (
        await db.execute(
            select(func.count())
            .select_from(LandingContactInquiry)
            .where(LandingContactInquiry.source == "waitlist_interest")
            .where(LandingContactInquiry.created_at >= cutoff)
        )
    ).scalar_one()
    contact_submits = (
        await db.execute(
            select(func.count())
            .select_from(LandingContactInquiry)
            .where(LandingContactInquiry.source != "waitlist_interest")
            .where(LandingContactInquiry.created_at >= cutoff)
        )
    ).scalar_one()
    feedback_submits = (
        await db.execute(
            select(func.count())
            .select_from(LandingFeedbackSubmission)
            .where(LandingFeedbackSubmission.created_at >= cutoff)
        )
    ).scalar_one()

    # Daily series
    day_rows = (
        await db.execute(
            text(
                """
                SELECT date_trunc('day', started_at AT TIME ZONE 'UTC')::date AS d,
                       COUNT(*)::int AS pageviews,
                       COUNT(DISTINCT session_id)::int AS sessions
                FROM "ZENK"."landing_pageviews"
                WHERE started_at >= :cutoff
                GROUP BY 1
                ORDER BY 1
                """
            ),
            {"cutoff": cutoff},
        )
    ).mappings().all()

    top_pages = (
        await db.execute(
            select(
                LandingPageview.path,
                func.count().label("views"),
                func.count(func.distinct(LandingPageview.session_id)).label("sessions"),
            )
            .where(LandingPageview.started_at >= cutoff)
            .group_by(LandingPageview.path)
            .order_by(func.count().desc())
            .limit(15)
        )
    ).all()

    top_ctas = (
        await db.execute(
            select(
                LandingEvent.cta_id,
                func.count().label("clicks"),
                func.count(func.distinct(LandingEvent.session_id)).label("sessions"),
            )
            .where(LandingEvent.event_name == "cta_click")
            .where(LandingEvent.created_at >= cutoff)
            .where(LandingEvent.cta_id.is_not(None))
            .group_by(LandingEvent.cta_id)
            .order_by(func.count().desc())
            .limit(25)
        )
    ).all()

    utm_rows = (
        await db.execute(
            select(
                func.coalesce(LandingSession.utm_source, "(none)").label("utm_source"),
                func.count().label("sessions"),
            )
            .where(LandingSession.first_seen_at >= cutoff)
            .group_by(text("1"))
            .order_by(func.count().desc())
            .limit(12)
        )
    ).all()

    # Engagement quality
    bounce_sessions = (
        await db.execute(
            text(
                """
                SELECT COUNT(*)::int FROM (
                  SELECT session_id
                  FROM "ZENK"."landing_pageviews"
                  WHERE started_at >= :cutoff
                  GROUP BY session_id
                  HAVING COUNT(*) = 1
                ) b
                """
            ),
            {"cutoff": cutoff},
        )
    ).scalar_one()
    avg_scroll = (
        await db.execute(
            select(func.avg(LandingPageview.scroll_pct)).where(
                LandingPageview.started_at >= cutoff,
                LandingPageview.scroll_pct.is_not(None),
            )
        )
    ).scalar_one()
    avg_duration = (
        await db.execute(
            select(func.avg(LandingPageview.duration_ms)).where(
                LandingPageview.started_at >= cutoff,
                LandingPageview.duration_ms.is_not(None),
            )
        )
    ).scalar_one()
    engaged_sessions = (
        await db.execute(
            select(func.count(func.distinct(LandingEvent.session_id)))
            .where(LandingEvent.event_name == "engaged")
            .where(LandingEvent.created_at >= cutoff)
        )
    ).scalar_one()
    device_rows = (
        await db.execute(
            select(
                func.coalesce(LandingSession.device_class, "unknown").label("device"),
                func.count().label("sessions"),
            )
            .where(LandingSession.first_seen_at >= cutoff)
            .group_by(text("1"))
            .order_by(func.count().desc())
        )
    ).all()

    # Register-interest funnel (unique sessions) — pageview + event based
    interest_viewed = (
        await db.execute(
            text(
                """
                SELECT COUNT(DISTINCT sid)::int FROM (
                  SELECT session_id AS sid
                  FROM "ZENK"."landing_events"
                  WHERE event_name = 'interest_view' AND created_at >= :cutoff
                  UNION
                  SELECT session_id AS sid
                  FROM "ZENK"."landing_pageviews"
                  WHERE started_at >= :cutoff
                    AND (path LIKE '/login?interest=%' OR path LIKE '/login?interest=1%')
                ) u
                """
            ),
            {"cutoff": cutoff},
        )
    ).scalar_one()
    interest_started = (
        await db.execute(
            select(func.count(func.distinct(LandingEvent.session_id)))
            .where(LandingEvent.event_name == "interest_start")
            .where(LandingEvent.created_at >= cutoff)
        )
    ).scalar_one()
    # Registered = waitlist submissions OR interest_complete events (distinct sessions)
    interest_registered_sessions = (
        await db.execute(
            text(
                """
                SELECT COUNT(DISTINCT sid)::int FROM (
                  SELECT session_id AS sid
                  FROM "ZENK"."landing_contact_inquiries"
                  WHERE source = 'waitlist_interest'
                    AND created_at >= :cutoff
                    AND session_id IS NOT NULL
                    AND BTRIM(session_id) <> ''
                  UNION
                  SELECT session_id AS sid
                  FROM "ZENK"."landing_events"
                  WHERE event_name = 'interest_complete'
                    AND created_at >= :cutoff
                ) u
                """
            ),
            {"cutoff": cutoff},
        )
    ).scalar_one()
    # Opened form in range and did NOT submit waitlist in range (same session)
    interest_abandoned = (
        await db.execute(
            text(
                """
                SELECT COUNT(DISTINCT v.sid)::int
                FROM (
                  SELECT session_id AS sid
                  FROM "ZENK"."landing_events"
                  WHERE event_name = 'interest_view' AND created_at >= :cutoff
                  UNION
                  SELECT session_id AS sid
                  FROM "ZENK"."landing_pageviews"
                  WHERE started_at >= :cutoff
                    AND (path LIKE '/login?interest=%' OR path LIKE '/login?interest=1%')
                ) v
                WHERE NOT EXISTS (
                  SELECT 1 FROM "ZENK"."landing_contact_inquiries" i
                  WHERE i.session_id = v.sid
                    AND i.source = 'waitlist_interest'
                    AND i.created_at >= :cutoff
                )
                AND NOT EXISTS (
                  SELECT 1 FROM "ZENK"."landing_events" c
                  WHERE c.session_id = v.sid
                    AND c.event_name = 'interest_complete'
                    AND c.created_at >= :cutoff
                )
                """
            ),
            {"cutoff": cutoff},
        )
    ).scalar_one()
    interest_abandoned_started = (
        await db.execute(
            text(
                """
                SELECT COUNT(DISTINCT s.session_id)::int
                FROM "ZENK"."landing_events" s
                WHERE s.event_name = 'interest_start'
                  AND s.created_at >= :cutoff
                  AND NOT EXISTS (
                    SELECT 1 FROM "ZENK"."landing_events" c
                    WHERE c.session_id = s.session_id
                      AND c.event_name = 'interest_complete'
                      AND c.created_at >= :cutoff
                  )
                  AND NOT EXISTS (
                    SELECT 1 FROM "ZENK"."landing_contact_inquiries" i
                    WHERE i.session_id = s.session_id
                      AND i.source = 'waitlist_interest'
                      AND i.created_at >= :cutoff
                  )
                """
            ),
            {"cutoff": cutoff},
        )
    ).scalar_one()
    # Viewers who also registered in the same period (conversion)
    interest_converted_from_view = (
        await db.execute(
            text(
                """
                SELECT COUNT(DISTINCT v.sid)::int
                FROM (
                  SELECT session_id AS sid
                  FROM "ZENK"."landing_events"
                  WHERE event_name = 'interest_view' AND created_at >= :cutoff
                  UNION
                  SELECT session_id AS sid
                  FROM "ZENK"."landing_pageviews"
                  WHERE started_at >= :cutoff
                    AND (path LIKE '/login?interest=%' OR path LIKE '/login?interest=1%')
                ) v
                WHERE EXISTS (
                  SELECT 1 FROM "ZENK"."landing_contact_inquiries" i
                  WHERE i.session_id = v.sid
                    AND i.source = 'waitlist_interest'
                    AND i.created_at >= :cutoff
                )
                OR EXISTS (
                  SELECT 1 FROM "ZENK"."landing_events" c
                  WHERE c.session_id = v.sid
                    AND c.event_name = 'interest_complete'
                    AND c.created_at >= :cutoff
                )
                """
            ),
            {"cutoff": cutoff},
        )
    ).scalar_one()

    viewed_n = int(interest_viewed or 0)
    started_n = int(interest_started or 0)
    completed_n = int(interest_registered_sessions or 0)
    converted_from_view_n = int(interest_converted_from_view or 0)
    abandoned_n = int(interest_abandoned or 0)
    abandoned_started_n = int(interest_abandoned_started or 0)
    sessions_n = int(sessions_total or 0)
    bounce_n = int(bounce_sessions or 0)

    return {
        "days": max(1, min(int(days or 7), 90)),
        "sessions": sessions_n,
        "sessions_today": int(sessions_today or 0),
        "pageviews": int(pageviews_total or 0),
        "unique_sessions": int(unique_sessions_pv or 0),
        "cta_clicks": int(cta_clicks or 0),
        "waitlist_submits": int(waitlist_submits or 0),
        "contact_submits": int(contact_submits or 0),
        "feedback_submits": int(feedback_submits or 0),
        "bounce_sessions": bounce_n,
        "bounce_rate": round((bounce_n / sessions_n) * 100, 1) if sessions_n else 0.0,
        "engaged_sessions": int(engaged_sessions or 0),
        "avg_scroll_pct": round(float(avg_scroll or 0), 1) if avg_scroll is not None else None,
        "avg_page_duration_ms": int(avg_duration or 0) if avg_duration is not None else None,
        "pages_per_session": round(
            (int(pageviews_total or 0) / sessions_n), 2
        )
        if sessions_n
        else 0.0,
        "devices": [
            {"device": d, "sessions": int(c or 0)} for d, c in device_rows
        ],
        "interest_funnel": {
            "viewed": viewed_n,
            "started": started_n,
            "abandoned": abandoned_n,
            "abandoned_after_start": abandoned_started_n,
            "completed": completed_n,
            "converted_from_view": converted_from_view_n,
            "view_to_start_rate": round((started_n / viewed_n) * 100, 1) if viewed_n else 0.0,
            "view_to_complete_rate": round((converted_from_view_n / viewed_n) * 100, 1)
            if viewed_n
            else 0.0,
            "abandon_rate": round((abandoned_n / viewed_n) * 100, 1) if viewed_n else 0.0,
            "start_abandon_rate": round((abandoned_started_n / started_n) * 100, 1)
            if started_n
            else 0.0,
        },
        "daily": [
            {
                "date": str(r["d"]),
                "pageviews": int(r["pageviews"] or 0),
                "sessions": int(r["sessions"] or 0),
            }
            for r in day_rows
        ],
        "top_pages": [
            {"path": p, "views": int(v or 0), "sessions": int(s or 0)}
            for p, v, s in top_pages
        ],
        "top_ctas": [
            {"cta_id": c, "clicks": int(v or 0), "sessions": int(s or 0)}
            for c, v, s in top_ctas
            if c
        ],
        "utm_sources": [
            {"utm_source": u, "sessions": int(c or 0)} for u, c in utm_rows
        ],
    }


async def cta_leaderboard(db: AsyncSession, *, days: int = 7) -> list[dict]:
    """CTA clicks with conversion to any form submit by session_id."""
    cutoff = _parse_days(days)
    top = (
        await db.execute(
            select(
                LandingEvent.cta_id,
                func.count().label("clicks"),
                func.count(func.distinct(LandingEvent.session_id)).label("sessions"),
            )
            .where(LandingEvent.event_name == "cta_click")
            .where(LandingEvent.created_at >= cutoff)
            .where(LandingEvent.cta_id.is_not(None))
            .group_by(LandingEvent.cta_id)
            .order_by(func.count().desc())
            .limit(50)
        )
    ).all()

    out: list[dict] = []
    for cta_id, clicks, sessions in top:
        if not cta_id:
            continue
        # Sessions that clicked this CTA and later submitted waitlist/contact/feedback
        converted = (
            await db.execute(
                text(
                    """
                    SELECT COUNT(DISTINCT e.session_id)::int AS n
                    FROM "ZENK"."landing_events" e
                    WHERE e.event_name = 'cta_click'
                      AND e.cta_id = :cta_id
                      AND e.created_at >= :cutoff
                      AND (
                        EXISTS (
                          SELECT 1 FROM "ZENK"."landing_contact_inquiries" c
                          WHERE c.session_id = e.session_id
                            AND c.created_at >= e.created_at
                        )
                        OR EXISTS (
                          SELECT 1 FROM "ZENK"."landing_feedback_submissions" f
                          WHERE f.session_id = e.session_id
                            AND f.created_at >= e.created_at
                        )
                      )
                    """
                ),
                {"cta_id": cta_id, "cutoff": cutoff},
            )
        ).scalar_one()
        sess_n = int(sessions or 0)
        conv_n = int(converted or 0)
        out.append(
            {
                "cta_id": cta_id,
                "clicks": int(clicks or 0),
                "sessions": sess_n,
                "converted_sessions": conv_n,
                "conversion_rate": round((conv_n / sess_n) * 100, 1) if sess_n else 0.0,
            }
        )
    return out


async def get_session_timeline(db: AsyncSession, session_id: str) -> Optional[dict]:
    sid = (session_id or "").strip()
    if not sid:
        return None
    sess = (
        await db.execute(select(LandingSession).where(LandingSession.session_id == sid))
    ).scalar_one_or_none()
    if not sess:
        return None

    pageviews = (
        await db.execute(
            select(LandingPageview)
            .where(LandingPageview.session_id == sid)
            .order_by(LandingPageview.started_at.asc())
            .limit(200)
        )
    ).scalars().all()
    events = (
        await db.execute(
            select(LandingEvent)
            .where(LandingEvent.session_id == sid)
            .order_by(LandingEvent.created_at.asc())
            .limit(200)
        )
    ).scalars().all()

    return {
        "session": {
            "session_id": sess.session_id,
            "first_seen_at": to_utc_iso(sess.first_seen_at),
            "last_seen_at": to_utc_iso(sess.last_seen_at),
            "entry_path": sess.entry_path,
            "referrer": sess.referrer,
            "utm_source": sess.utm_source,
            "utm_medium": sess.utm_medium,
            "utm_campaign": sess.utm_campaign,
            "geo_country": sess.geo_country,
            "geo_region": sess.geo_region,
            "geo_city": sess.geo_city,
            "device_class": sess.device_class,
            "pageview_count": sess.pageview_count,
            "event_count": sess.event_count,
        },
        "pageviews": [
            {
                "id": p.id,
                "path": p.path,
                "started_at": to_utc_iso(p.started_at),
                "duration_ms": p.duration_ms,
                "scroll_pct": p.scroll_pct,
            }
            for p in pageviews
        ],
        "events": [
            {
                "id": e.id,
                "event_name": e.event_name,
                "cta_id": e.cta_id,
                "path": e.path,
                "created_at": to_utc_iso(e.created_at),
            }
            for e in events
        ],
    }


async def list_recent_sessions(db: AsyncSession, *, days: int = 7, limit: int = 50) -> list[dict]:
    cutoff = _parse_days(days)
    rows = (
        await db.execute(
            select(LandingSession)
            .where(LandingSession.last_seen_at >= cutoff)
            .order_by(LandingSession.last_seen_at.desc())
            .limit(max(1, min(limit, 200)))
        )
    ).scalars().all()
    return [
        {
            "session_id": r.session_id,
            "first_seen_at": to_utc_iso(r.first_seen_at),
            "last_seen_at": to_utc_iso(r.last_seen_at),
            "entry_path": r.entry_path,
            "utm_source": r.utm_source,
            "geo_city": r.geo_city,
            "geo_country": r.geo_country,
            "device_class": r.device_class,
            "pageview_count": r.pageview_count,
            "event_count": r.event_count,
        }
        for r in rows
    ]
