"""Circle ↔ school partner direct messaging."""

import asyncio
import logging

from sqlalchemy import text

from app.db.session import engine

logger = logging.getLogger(__name__)


async def run_migration():
    logger.info("=== Migration 025: Circle school partner messages ===")

    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS "ZENK".circle_school_partner_messages (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                circle_id UUID NOT NULL,
                school_id UUID NOT NULL REFERENCES "ZENK".school_profiles(id) ON DELETE CASCADE,
                sender_side VARCHAR(16) NOT NULL,
                sender_signup_id UUID,
                sender_name VARCHAR(200),
                body TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
            )
        )
        await conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS idx_cspm_circle_school
                ON "ZENK".circle_school_partner_messages(circle_id, school_id, created_at)
            """
            )
        )
    logger.info("Migration 025 complete.")


if __name__ == "__main__":
    asyncio.run(run_migration())
