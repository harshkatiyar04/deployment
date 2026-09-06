"""Tag landing contact inquiries with source (waitlist vs landing contact)."""

import asyncio
import logging

from sqlalchemy import text

from app.db.session import engine

logger = logging.getLogger(__name__)


async def run_migration():
    logger.info("=== Migration 049: Landing contact source ===")
    async with engine.begin() as conn:
        await conn.execute(
            text(
                'ALTER TABLE "ZENK"."landing_contact_inquiries" '
                "ADD COLUMN IF NOT EXISTS source VARCHAR(40) NOT NULL DEFAULT 'landing_contact'"
            )
        )
        # Backfill waitlist rows from message fingerprint
        await conn.execute(
            text(
                """
                UPDATE "ZENK"."landing_contact_inquiries"
                SET source = 'waitlist_interest'
                WHERE source = 'landing_contact'
                  AND (
                    message ILIKE '%waitlist interest form%'
                    OR landing_path ILIKE '%/login%'
                    OR interest ILIKE '%Founding Circles%'
                  )
                """
            )
        )
        await conn.execute(
            text(
                'CREATE INDEX IF NOT EXISTS idx_landing_contact_inquiries_source '
                'ON "ZENK"."landing_contact_inquiries"(source, created_at DESC)'
            )
        )
    logger.info("Migration 049 complete.")


if __name__ == "__main__":
    asyncio.run(run_migration())
