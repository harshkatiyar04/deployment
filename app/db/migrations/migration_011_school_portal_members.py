import asyncio
import logging
from sqlalchemy import text
from app.db.session import engine

logger = logging.getLogger(__name__)


async def run_migration():
    logger.info("=== Migration 011: School portal members ===")

    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "ZENK"."school_portal_members" (
                id                  UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
                school_id           UUID         NOT NULL REFERENCES "ZENK"."school_profiles"(id) ON DELETE CASCADE,
                email               VARCHAR(320) NOT NULL,
                display_name        VARCHAR(200) NOT NULL,
                portal_role         VARCHAR(20)  NOT NULL DEFAULT 'staff',
                user_id             UUID         REFERENCES "ZENK"."signup_requests"(id) ON DELETE SET NULL,
                invited_by_user_id  UUID         REFERENCES "ZENK"."signup_requests"(id) ON DELETE SET NULL,
                created_at          TIMESTAMP    NOT NULL DEFAULT NOW(),
                updated_at          TIMESTAMP    NOT NULL DEFAULT NOW()
            )
        """))
        await conn.execute(text(
            'CREATE UNIQUE INDEX IF NOT EXISTS idx_school_portal_member_email '
            'ON "ZENK"."school_portal_members"(school_id, lower(email))'
        ))
        await conn.execute(text(
            'CREATE INDEX IF NOT EXISTS idx_school_portal_member_user '
            'ON "ZENK"."school_portal_members"(user_id)'
        ))

    logger.info("Migration 011 complete.")


if __name__ == "__main__":
    asyncio.run(run_migration())
