"""Migration 040: ZenQ Spark events + welfare cases (Phase 4)."""

from __future__ import annotations

import logging

from sqlalchemy import text

from app.db.session import engine

logger = logging.getLogger(__name__)


async def run_migration() -> None:
    logger.info("=== Migration 040: ZenQ spark + welfare ===")

    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "ZENK"."zenq_spark_events" (
                id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
                student_id      UUID         NOT NULL,
                circle_id       UUID         NOT NULL REFERENCES "ZENK"."sponsor_circles"(id) ON DELETE CASCADE,
                reason          TEXT,
                expires_at      TIMESTAMPTZ  NOT NULL,
                created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
            )
        """))
        await conn.execute(text(
            'CREATE INDEX IF NOT EXISTS idx_zenq_spark_active '
            'ON "ZENK"."zenq_spark_events"(circle_id, expires_at DESC)'
        ))

        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "ZENK"."zenq_welfare_cases" (
                id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
                circle_id       UUID         NOT NULL REFERENCES "ZENK"."sponsor_circles"(id) ON DELETE CASCADE,
                student_id      UUID,
                sponsor_user_id UUID,
                level           INTEGER      NOT NULL DEFAULT 1,
                status          VARCHAR(20)  NOT NULL DEFAULT 'open',
                signals_json    JSONB        NOT NULL DEFAULT '[]'::jsonb,
                notes           TEXT,
                opened_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
                resolved_at     TIMESTAMPTZ,
                resolved_by     VARCHAR(128)
            )
        """))
        await conn.execute(text(
            'CREATE INDEX IF NOT EXISTS idx_zenq_welfare_open '
            'ON "ZENK"."zenq_welfare_cases"(status, level DESC, opened_at DESC)'
        ))

        await conn.execute(text("""
            ALTER TABLE "ZENK"."zenq_circle_scores"
            ADD COLUMN IF NOT EXISTS decay_factor FLOAT NOT NULL DEFAULT 1.0
        """))
        await conn.execute(text("""
            ALTER TABLE "ZENK"."zenq_circle_scores"
            ADD COLUMN IF NOT EXISTS ziq_raw FLOAT
        """))

    logger.info("Migration 040 complete.")
