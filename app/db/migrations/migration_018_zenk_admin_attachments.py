import asyncio
import logging
from sqlalchemy import text
from app.db.session import engine

logger = logging.getLogger(__name__)


async def run_migration():
    logger.info("=== Migration 018: Zenk Admin message attachments ===")
    async with engine.begin() as conn:
        await conn.execute(text("""
            ALTER TABLE "ZENK"."zenk_admin_messages"
            ADD COLUMN IF NOT EXISTS attachment_url TEXT
        """))
        await conn.execute(text("""
            ALTER TABLE "ZENK"."zenk_admin_messages"
            ADD COLUMN IF NOT EXISTS attachment_type VARCHAR(20)
        """))
    logger.info("Migration 018 complete.")


if __name__ == "__main__":
    asyncio.run(run_migration())
