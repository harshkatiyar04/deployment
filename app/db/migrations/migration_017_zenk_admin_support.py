import asyncio
import logging
from sqlalchemy import text
from app.db.session import engine

logger = logging.getLogger(__name__)


async def run_migration():
    logger.info("=== Migration 017: Zenk Admin support threads ===")
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "ZENK"."zenk_admin_threads" (
                id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id             UUID NOT NULL UNIQUE REFERENCES "ZENK"."signup_requests"(id) ON DELETE CASCADE,
                admin_unread_count  INTEGER NOT NULL DEFAULT 0,
                user_unread_count   INTEGER NOT NULL DEFAULT 0,
                last_message_text   TEXT,
                last_message_at     TIMESTAMPTZ,
                created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "ZENK"."zenk_admin_messages" (
                id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                thread_id   UUID NOT NULL REFERENCES "ZENK"."zenk_admin_threads"(id) ON DELETE CASCADE,
                sender_role VARCHAR(10) NOT NULL,
                text        TEXT NOT NULL,
                created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """))
        await conn.execute(text(
            'CREATE INDEX IF NOT EXISTS idx_zenk_admin_messages_thread '
            'ON "ZENK"."zenk_admin_messages"(thread_id, created_at)'
        ))
    logger.info("Migration 017 complete.")


if __name__ == "__main__":
    asyncio.run(run_migration())
