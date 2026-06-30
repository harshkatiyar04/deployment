"""Circle name at leader signup + admin-approved rename (90-day cooldown)."""

import asyncio
import logging

from sqlalchemy import text

from app.db.session import engine

logger = logging.getLogger(__name__)


async def run_migration():
    logger.info("=== Migration 035: Circle rename requests ===")

    async with engine.begin() as conn:
        await conn.execute(
            text(
                'ALTER TABLE "ZENK".signup_requests '
                "ADD COLUMN IF NOT EXISTS requested_circle_name VARCHAR(255)"
            )
        )
        await conn.execute(
            text(
                'ALTER TABLE "ZENK".sponsor_circles '
                "ADD COLUMN IF NOT EXISTS name_changed_at TIMESTAMPTZ"
            )
        )
        await conn.execute(
            text(
                'UPDATE "ZENK".sponsor_circles '
                "SET name_changed_at = created_at "
                "WHERE name_changed_at IS NULL"
            )
        )
        await conn.execute(
            text(
                'ALTER TABLE "ZENK".circle_admin_requests '
                "ADD COLUMN IF NOT EXISTS current_circle_name VARCHAR(255)"
            )
        )
        await conn.execute(
            text(
                'ALTER TABLE "ZENK".circle_admin_requests '
                "ADD COLUMN IF NOT EXISTS requested_circle_name VARCHAR(255)"
            )
        )

    logger.info("Migration 035 complete.")


if __name__ == "__main__":
    asyncio.run(run_migration())
