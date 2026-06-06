"""Circle member limit + admin-approved removal / limit-increase requests."""

import asyncio
import logging

from sqlalchemy import text

from app.db.session import engine

logger = logging.getLogger(__name__)


async def run_migration():
    logger.info("=== Migration 015: Circle membership admin requests ===")

    async with engine.begin() as conn:
        await conn.execute(
            text(
                'ALTER TABLE "ZENK".sponsor_circles '
                "ADD COLUMN IF NOT EXISTS member_limit INTEGER NOT NULL DEFAULT 5"
            )
        )

        await conn.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS "ZENK"."circle_admin_requests" (
                id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                circle_id           UUID NOT NULL,
                request_type        VARCHAR(40) NOT NULL,
                status              VARCHAR(20) NOT NULL DEFAULT 'pending',
                requested_by_user_id UUID NOT NULL,
                requested_by_name   VARCHAR(200),
                target_user_id      UUID,
                target_user_name    VARCHAR(200),
                current_member_count INTEGER,
                current_member_limit INTEGER,
                requested_limit     INTEGER,
                leader_comment      TEXT NOT NULL,
                admin_comment       TEXT,
                reviewed_by_admin   VARCHAR(120),
                reviewed_at         TIMESTAMPTZ,
                created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
            )
        )
        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_circle_admin_req_status "
                'ON "ZENK"."circle_admin_requests"(status, created_at DESC)'
            )
        )
        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_circle_admin_req_circle "
                'ON "ZENK"."circle_admin_requests"(circle_id, request_type, status)'
            )
        )

    logger.info("Migration 015 complete.")


if __name__ == "__main__":
    asyncio.run(run_migration())
