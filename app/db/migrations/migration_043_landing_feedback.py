import asyncio
import logging

from sqlalchemy import text

from app.db.session import engine

logger = logging.getLogger(__name__)


async def run_migration():
    logger.info("=== Migration 043: Landing feedback + visits ===")
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "ZENK"."landing_feedback_submissions" (
                id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name                 VARCHAR(120) NOT NULL,
                email                VARCHAR(320) NOT NULL,
                interest             VARCHAR(120) NOT NULL,
                found_via            VARCHAR(120),
                rating               INTEGER,
                suggestion           TEXT NOT NULL DEFAULT '',
                mailing_list_opt_in  BOOLEAN NOT NULL DEFAULT TRUE,
                session_id           VARCHAR(64),
                ip_address           VARCHAR(64),
                user_agent           TEXT,
                accept_language      VARCHAR(120),
                referrer             TEXT,
                landing_path         VARCHAR(500),
                utm_source           VARCHAR(120),
                utm_medium           VARCHAR(120),
                utm_campaign         VARCHAR(120),
                timezone             VARCHAR(80),
                screen               VARCHAR(40),
                geo_country          VARCHAR(80),
                geo_region           VARCHAR(120),
                geo_city             VARCHAR(120),
                source               VARCHAR(40) NOT NULL DEFAULT 'landing_popup',
                admin_read           BOOLEAN NOT NULL DEFAULT FALSE,
                created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """))
        await conn.execute(text(
            'CREATE INDEX IF NOT EXISTS idx_landing_feedback_created '
            'ON "ZENK"."landing_feedback_submissions"(created_at DESC)'
        ))
        await conn.execute(text(
            'CREATE INDEX IF NOT EXISTS idx_landing_feedback_unread '
            'ON "ZENK"."landing_feedback_submissions"(admin_read) '
            'WHERE admin_read = FALSE'
        ))
        await conn.execute(text(
            'CREATE INDEX IF NOT EXISTS idx_landing_feedback_email '
            'ON "ZENK"."landing_feedback_submissions"(email)'
        ))
        await conn.execute(text(
            'CREATE INDEX IF NOT EXISTS idx_landing_feedback_session '
            'ON "ZENK"."landing_feedback_submissions"(session_id)'
        ))

        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "ZENK"."landing_visits" (
                id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                session_id       VARCHAR(64) NOT NULL,
                ip_address       VARCHAR(64),
                user_agent       TEXT,
                accept_language  VARCHAR(120),
                referrer         TEXT,
                landing_path     VARCHAR(500),
                utm_source       VARCHAR(120),
                utm_medium       VARCHAR(120),
                utm_campaign     VARCHAR(120),
                timezone         VARCHAR(80),
                screen           VARCHAR(40),
                geo_country      VARCHAR(80),
                geo_region       VARCHAR(120),
                geo_city         VARCHAR(120),
                created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """))
        await conn.execute(text(
            'CREATE INDEX IF NOT EXISTS idx_landing_visits_created '
            'ON "ZENK"."landing_visits"(created_at DESC)'
        ))
        await conn.execute(text(
            'CREATE INDEX IF NOT EXISTS idx_landing_visits_session '
            'ON "ZENK"."landing_visits"(session_id)'
        ))
    logger.info("Migration 043 complete.")


if __name__ == "__main__":
    asyncio.run(run_migration())
