"""Migration 052: ZenQ v2 ledger idempotency index on quality_json key."""

from __future__ import annotations

import logging

from sqlalchemy import text

from app.db.session import engine

logger = logging.getLogger(__name__)


async def run_migration() -> None:
    logger.info("=== Migration 052: ZenQ v2 idempotency index ===")
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_zenq_v2_ledger_idempotency
                ON "ZENK"."zenq_v2_event_ledger" ((quality_json->>'idempotency_key'))
                WHERE quality_json->>'idempotency_key' IS NOT NULL
                """
            )
        )
    logger.info("Migration 052 complete")
