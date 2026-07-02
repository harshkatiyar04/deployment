"""Parent hat access password on student_family_links (separate from student login)."""

import asyncio
import logging

from sqlalchemy import text

from app.db.session import engine

logger = logging.getLogger(__name__)


async def run_migration():
    logger.info("=== Migration 036: Guardian hat password ===")
    async with engine.begin() as conn:
        await conn.execute(text("""
            ALTER TABLE "ZENK".student_family_links
            ADD COLUMN IF NOT EXISTS guardian_hat_password_hash VARCHAR(255)
        """))
    logger.info("Migration 036 complete.")


if __name__ == "__main__":
    asyncio.run(run_migration())
