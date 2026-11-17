"""Migration 055: ZenQ v2 csr_allocation_run (Phase 6 Sponsor/CSR)."""

from __future__ import annotations

import logging

from sqlalchemy import text

from app.db.session import engine

logger = logging.getLogger(__name__)


async def run_migration() -> None:
    logger.info("=== Migration 055: zenq_v2_csr_allocation_run ===")
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS "ZENK"."zenq_v2_csr_allocation_run" (
                    run_id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    sponsor_id          UUID,
                    budget              FLOAT NOT NULL,
                    weights_json        JSONB NOT NULL DEFAULT '[0.5, 0.3, 0.2]'::jsonb,
                    as_of_month         DATE,
                    allocations_json    JSONB NOT NULL DEFAULT '[]'::jsonb,
                    expected_impact     FLOAT,
                    equal_split_impact  FLOAT,
                    notes               TEXT,
                    status              VARCHAR(32) NOT NULL DEFAULT 'DRY_RUN',
                    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
        )
        await conn.execute(
            text(
                'CREATE INDEX IF NOT EXISTS idx_zenq_v2_csr_run_created '
                'ON "ZENK"."zenq_v2_csr_allocation_run"(created_at DESC)'
            )
        )
        await conn.execute(
            text(
                'CREATE INDEX IF NOT EXISTS idx_zenq_v2_csr_run_sponsor '
                'ON "ZENK"."zenq_v2_csr_allocation_run"(sponsor_id)'
            )
        )
    logger.info("Migration 055 complete")
