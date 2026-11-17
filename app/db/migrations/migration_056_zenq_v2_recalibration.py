"""Migration 056: ZenQ v2 recalibration runs + sealed predictions (Phase 7)."""

from __future__ import annotations

import logging

from sqlalchemy import text

from app.db.session import engine

logger = logging.getLogger(__name__)


async def run_migration() -> None:
    logger.info("=== Migration 056: zenq_v2 recalibration + sealed predictions ===")
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS "ZENK"."zenq_v2_recalibration_run" (
                    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    month                   DATE NOT NULL,
                    pairs                   INTEGER NOT NULL DEFAULT 0,
                    min_pairs               INTEGER NOT NULL DEFAULT 200,
                    proposed_shift_json     JSONB NOT NULL DEFAULT '{}'::jsonb,
                    equalisation_json       JSONB NOT NULL DEFAULT '{}'::jsonb,
                    evidence_json           JSONB NOT NULL DEFAULT '{}'::jsonb,
                    status                  VARCHAR(32) NOT NULL DEFAULT 'LOGGED',
                    reasoning_text          TEXT,
                    reviewed_by             VARCHAR(128),
                    reviewed_at             TIMESTAMPTZ,
                    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
        )
        await conn.execute(
            text(
                'CREATE INDEX IF NOT EXISTS idx_zenq_v2_recal_created '
                'ON "ZENK"."zenq_v2_recalibration_run"(created_at DESC)'
            )
        )
        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS "ZENK"."zenq_v2_sealed_prediction" (
                    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    label               VARCHAR(256) NOT NULL,
                    value_json          JSONB NOT NULL DEFAULT 'null'::jsonb,
                    content_hash        VARCHAR(64) NOT NULL,
                    engine              VARCHAR(32) NOT NULL DEFAULT 'FOUNDERS',
                    open_at_month_6     BOOLEAN NOT NULL DEFAULT TRUE,
                    sealed_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    opened_at           TIMESTAMPTZ
                )
                """
            )
        )
        await conn.execute(
            text(
                'CREATE INDEX IF NOT EXISTS idx_zenq_v2_sealed_sealed_at '
                'ON "ZENK"."zenq_v2_sealed_prediction"(sealed_at DESC)'
            )
        )
    logger.info("Migration 056 complete")
