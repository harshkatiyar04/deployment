"""Add visitor metadata + thank-you email flag to landing contact inquiries."""

import asyncio
import logging

from sqlalchemy import text

from app.db.session import engine

logger = logging.getLogger(__name__)

COLUMNS = [
    ("session_id", "VARCHAR(64)"),
    ("ip_address", "VARCHAR(64)"),
    ("user_agent", "TEXT"),
    ("accept_language", "VARCHAR(120)"),
    ("referrer", "TEXT"),
    ("landing_path", "VARCHAR(500)"),
    ("utm_source", "VARCHAR(120)"),
    ("utm_medium", "VARCHAR(120)"),
    ("utm_campaign", "VARCHAR(120)"),
    ("timezone", "VARCHAR(80)"),
    ("screen", "VARCHAR(40)"),
    ("geo_country", "VARCHAR(80)"),
    ("geo_region", "VARCHAR(120)"),
    ("geo_city", "VARCHAR(120)"),
    ("thank_you_sent", "BOOLEAN NOT NULL DEFAULT FALSE"),
]


async def run_migration():
    logger.info("=== Migration 048: Landing contact visitor meta ===")
    async with engine.begin() as conn:
        for name, col_type in COLUMNS:
            await conn.execute(
                text(
                    f'ALTER TABLE "ZENK"."landing_contact_inquiries" '
                    f"ADD COLUMN IF NOT EXISTS {name} {col_type}"
                )
            )
        await conn.execute(
            text(
                'CREATE INDEX IF NOT EXISTS idx_landing_contact_inquiries_session '
                'ON "ZENK"."landing_contact_inquiries"(session_id) '
                "WHERE session_id IS NOT NULL"
            )
        )
    logger.info("Migration 048 complete.")


if __name__ == "__main__":
    asyncio.run(run_migration())
