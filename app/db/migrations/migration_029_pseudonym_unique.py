"""Case-insensitive unique index on gamified_personas.nickname."""

import asyncio
import logging
from sqlalchemy import text
from app.db.session import engine

logger = logging.getLogger(__name__)


async def run_migration():
    logger.info("=== Migration 029: pseudonym unique index ===")
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS ix_gamified_personas_nickname_lower
            ON "ZENK".gamified_personas (LOWER(nickname))
        """))
    logger.info("Migration 029 complete.")


if __name__ == "__main__":
    asyncio.run(run_migration())
