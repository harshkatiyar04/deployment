import asyncio
import logging
from sqlalchemy import text
from app.db.session import engine

logger = logging.getLogger(__name__)


async def run_migration():
    logger.info("=== Migration 010: School RBAC + action audit log ===")

    async with engine.begin() as conn:
        logger.info("Adding portal_role to school_profiles...")
        await conn.execute(text("""
            ALTER TABLE "ZENK"."school_profiles"
            ADD COLUMN IF NOT EXISTS portal_role VARCHAR(20) NOT NULL DEFAULT 'principal'
        """))

        logger.info("Creating school_action_audit_log...")
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "ZENK"."school_action_audit_log" (
                id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
                school_id       UUID         NOT NULL REFERENCES "ZENK"."school_profiles"(id) ON DELETE CASCADE,
                actor_user_id   UUID         NOT NULL,
                actor_email     VARCHAR(320),
                action          VARCHAR(80)  NOT NULL,
                student_id      UUID,
                outcome         VARCHAR(20)  NOT NULL DEFAULT 'success',
                detail          JSONB,
                created_at      TIMESTAMP    NOT NULL DEFAULT NOW()
            )
        """))
        await conn.execute(text(
            'CREATE INDEX IF NOT EXISTS idx_school_audit_school_id '
            'ON "ZENK"."school_action_audit_log"(school_id, created_at DESC)'
        ))
        await conn.execute(text(
            'CREATE INDEX IF NOT EXISTS idx_school_audit_actor '
            'ON "ZENK"."school_action_audit_log"(actor_user_id)'
        ))

    logger.info("Migration 010 complete.")


if __name__ == "__main__":
    asyncio.run(run_migration())
