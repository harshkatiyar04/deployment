import asyncio
import logging
from sqlalchemy import text
from app.db.session import engine

logger = logging.getLogger(__name__)


async def run_migration():
    logger.info("=== Migration 012: School portal invites ===")

    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "ZENK"."school_portal_invites" (
                id                  UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
                school_id           UUID         NOT NULL REFERENCES "ZENK"."school_profiles"(id) ON DELETE CASCADE,
                member_id           UUID         REFERENCES "ZENK"."school_portal_members"(id) ON DELETE SET NULL,
                email               VARCHAR(320) NOT NULL,
                display_name        VARCHAR(200) NOT NULL,
                portal_role         VARCHAR(20)  NOT NULL DEFAULT 'staff',
                token               VARCHAR(128) NOT NULL UNIQUE,
                expires_at          TIMESTAMP    NOT NULL,
                accepted_at         TIMESTAMP,
                revoked_at          TIMESTAMP,
                invited_by_user_id  UUID         REFERENCES "ZENK"."signup_requests"(id) ON DELETE SET NULL,
                created_at          TIMESTAMP    NOT NULL DEFAULT NOW()
            )
        """))
        await conn.execute(text(
            'CREATE INDEX IF NOT EXISTS idx_school_invite_school '
            'ON "ZENK"."school_portal_invites"(school_id, created_at DESC)'
        ))
        await conn.execute(text(
            'CREATE UNIQUE INDEX IF NOT EXISTS idx_school_invite_email_active '
            'ON "ZENK"."school_portal_invites"(school_id, lower(email)) '
            'WHERE accepted_at IS NULL AND revoked_at IS NULL'
        ))

    logger.info("Migration 012 complete.")


if __name__ == "__main__":
    asyncio.run(run_migration())
