"""Add info_required value to kyc_status_enum."""

import asyncio
import logging

from sqlalchemy import text

from app.db.session import engine

logger = logging.getLogger(__name__)


async def run_migration():
    logger.info("=== Migration 030: kyc_status info_required ===")
    async with engine.begin() as conn:
        await conn.execute(
            text(
                'ALTER TYPE "ZENK".kyc_status_enum ADD VALUE IF NOT EXISTS \'info_required\''
            )
        )
    logger.info("Migration 030 complete.")


if __name__ == "__main__":
    asyncio.run(run_migration())
