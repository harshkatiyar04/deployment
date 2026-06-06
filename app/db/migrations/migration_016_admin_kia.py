import asyncio
import logging
from sqlalchemy import text
from app.db.session import engine

logger = logging.getLogger(__name__)


async def run_migration():
    logger.info("=== Migration 016: Admin Kia messages ===")
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "ZENK"."admin_kia_messages" (
                id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                role        VARCHAR(20) NOT NULL,
                text        TEXT NOT NULL,
                event_type  VARCHAR(40),
                action_path VARCHAR(200),
                created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """))
        await conn.execute(text(
            'CREATE INDEX IF NOT EXISTS idx_admin_kia_messages_created '
            'ON "ZENK"."admin_kia_messages"(created_at DESC)'
        ))
    logger.info("Migration 016 complete.")


if __name__ == "__main__":
    asyncio.run(run_migration())
