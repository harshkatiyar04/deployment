"""Migration 050: First-party landing analytics (sessions, pageviews, events)."""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import text

from app.db.session import engine

logger = logging.getLogger(__name__)


async def run_migration():
    logger.info("=== Migration 050: Landing analytics tables ===")
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS "ZENK"."landing_sessions" (
                id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                session_id      VARCHAR(64) NOT NULL UNIQUE,
                first_seen_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                last_seen_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                entry_path      VARCHAR(500),
                referrer        TEXT,
                utm_source      VARCHAR(120),
                utm_medium      VARCHAR(120),
                utm_campaign    VARCHAR(120),
                ip_address      VARCHAR(64),
                user_agent      TEXT,
                accept_language VARCHAR(120),
                timezone        VARCHAR(80),
                screen          VARCHAR(40),
                device_class    VARCHAR(40),
                geo_country     VARCHAR(80),
                geo_region      VARCHAR(120),
                geo_city        VARCHAR(120),
                pageview_count  INTEGER NOT NULL DEFAULT 0,
                event_count     INTEGER NOT NULL DEFAULT 0
            )
            """
            )
        )
        await conn.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS "ZENK"."landing_pageviews" (
                id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                session_id      VARCHAR(64) NOT NULL,
                path            VARCHAR(500) NOT NULL,
                referrer        TEXT,
                started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                duration_ms     INTEGER,
                scroll_pct      INTEGER,
                utm_source      VARCHAR(120),
                utm_medium      VARCHAR(120),
                utm_campaign    VARCHAR(120)
            )
            """
            )
        )
        await conn.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS "ZENK"."landing_events" (
                id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                session_id      VARCHAR(64) NOT NULL,
                event_name      VARCHAR(80) NOT NULL,
                cta_id          VARCHAR(120),
                path            VARCHAR(500),
                meta_json       TEXT,
                created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
            )
        )

        for stmt in (
            'CREATE INDEX IF NOT EXISTS idx_landing_sessions_last '
            'ON "ZENK"."landing_sessions"(last_seen_at DESC)',
            'CREATE INDEX IF NOT EXISTS idx_landing_sessions_first '
            'ON "ZENK"."landing_sessions"(first_seen_at DESC)',
            'CREATE INDEX IF NOT EXISTS idx_landing_pageviews_started '
            'ON "ZENK"."landing_pageviews"(started_at DESC)',
            'CREATE INDEX IF NOT EXISTS idx_landing_pageviews_session '
            'ON "ZENK"."landing_pageviews"(session_id)',
            'CREATE INDEX IF NOT EXISTS idx_landing_pageviews_path '
            'ON "ZENK"."landing_pageviews"(path, started_at DESC)',
            'CREATE INDEX IF NOT EXISTS idx_landing_events_created '
            'ON "ZENK"."landing_events"(created_at DESC)',
            'CREATE INDEX IF NOT EXISTS idx_landing_events_session '
            'ON "ZENK"."landing_events"(session_id)',
            'CREATE INDEX IF NOT EXISTS idx_landing_events_cta '
            'ON "ZENK"."landing_events"(cta_id, created_at DESC)',
            'CREATE INDEX IF NOT EXISTS idx_landing_events_name '
            'ON "ZENK"."landing_events"(event_name, created_at DESC)',
        ):
            await conn.execute(text(stmt))

    logger.info("=== Migration 050 complete ===")


if __name__ == "__main__":
    asyncio.run(run_migration())
