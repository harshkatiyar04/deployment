import asyncio
import logging

from sqlalchemy import text

from app.db.session import engine

logger = logging.getLogger(__name__)


async def run_migration():
    logger.info("=== Migration 042: Landing contact inquiries ===")
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "ZENK"."landing_contact_inquiries" (
                id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name            VARCHAR(120) NOT NULL,
                email           VARCHAR(320) NOT NULL,
                interest        VARCHAR(120) NOT NULL,
                message         TEXT NOT NULL DEFAULT '',
                admin_read      BOOLEAN NOT NULL DEFAULT FALSE,
                email_notified  BOOLEAN NOT NULL DEFAULT FALSE,
                created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """))
        await conn.execute(text(
            'CREATE INDEX IF NOT EXISTS idx_landing_contact_inquiries_created '
            'ON "ZENK"."landing_contact_inquiries"(created_at DESC)'
        ))
        await conn.execute(text(
            'CREATE INDEX IF NOT EXISTS idx_landing_contact_inquiries_unread '
            'ON "ZENK"."landing_contact_inquiries"(admin_read) '
            'WHERE admin_read = FALSE'
        ))
    logger.info("Migration 042 complete.")


if __name__ == "__main__":
    asyncio.run(run_migration())
