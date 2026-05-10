"""
Migration 008 — Mentor Kia Chat
=================================
Adds the `mentor_kia_messages` table for persisting Kia chat history.
"""
import asyncio
import logging
from app.db.session import engine
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_migration():
    logger.info("=== Migration 008: Mentor Kia Chat ===")

    async with engine.begin() as conn:
        logger.info("Step 1: Creating mentor_kia_messages table...")
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "ZENK"."mentor_kia_messages" (
                id          UUID PRIMARY KEY,
                mentor_id   UUID NOT NULL REFERENCES "ZENK"."mentor_profiles"(id) ON DELETE CASCADE,
                role        VARCHAR(50) NOT NULL,
                text        TEXT NOT NULL,
                created_at  TIMESTAMP NOT NULL DEFAULT NOW()
            );
        """))
        logger.info("  -> Table created.")

        logger.info("Step 2: Creating index on mentor_id...")
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_mentor_kia_messages_mentor_id 
            ON "ZENK"."mentor_kia_messages" (mentor_id);
        """))
        logger.info("  -> Index created.")

    logger.info("=== Migration 008 Complete ===")


if __name__ == "__main__":
    asyncio.run(run_migration())
