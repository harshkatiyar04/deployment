"""Migration 039: leader target-achievement logs for ZenQ Phase 2."""

from __future__ import annotations

import logging

from sqlalchemy import text

from app.db.session import engine

logger = logging.getLogger(__name__)


async def run_migration() -> None:
    logger.info("=== Migration 039: zenq_target_logs ===")

    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "ZENK"."zenq_target_logs" (
                id                UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
                circle_id         UUID         NOT NULL REFERENCES "ZENK"."sponsor_circles"(id) ON DELETE CASCADE,
                sponsor_user_id   UUID         NOT NULL,
                quarter           VARCHAR(10)  NOT NULL DEFAULT 'Q1',
                fy                VARCHAR(20)  NOT NULL DEFAULT '2025-26',
                target_status     VARCHAR(16)  NOT NULL,
                notes             TEXT,
                logged_by_user_id UUID         NOT NULL,
                created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW()
            )
        """))
        await conn.execute(text(
            'CREATE INDEX IF NOT EXISTS idx_zenq_target_logs_circle_sponsor '
            'ON "ZENK"."zenq_target_logs"(circle_id, sponsor_user_id, created_at DESC)'
        ))

    logger.info("Migration 039 complete.")
