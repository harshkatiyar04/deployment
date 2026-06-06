"""Parent academic upload v2 — optional file, manual term grades, parent note."""

import asyncio
import logging

from sqlalchemy import text

from app.db.session import engine

logger = logging.getLogger(__name__)


async def run_migration():
    logger.info("=== Migration 024: Parent upload v2 ===")

    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
            ALTER TABLE "ZENK".parent_academic_submissions
                ADD COLUMN IF NOT EXISTS parent_note TEXT,
                ADD COLUMN IF NOT EXISTS grade_payload JSONB,
                ADD COLUMN IF NOT EXISTS submission_kind VARCHAR(20) NOT NULL DEFAULT 'file'
            """
            )
        )
        await conn.execute(
            text(
                """
            ALTER TABLE "ZENK".parent_academic_submissions
                ALTER COLUMN file_url DROP NOT NULL
            """
            )
        )
    logger.info("Migration 024 complete.")


if __name__ == "__main__":
    asyncio.run(run_migration())
