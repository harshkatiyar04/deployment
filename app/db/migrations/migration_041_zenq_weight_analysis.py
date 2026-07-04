"""Migration 041: ZenQ weight proposal analysis metadata (Phase 5)."""

from __future__ import annotations

import logging

from sqlalchemy import text

from app.db.session import engine

logger = logging.getLogger(__name__)


async def run_migration() -> None:
    logger.info("=== Migration 041: zenq_weight_config analysis_json ===")

    async with engine.begin() as conn:
        await conn.execute(text("""
            ALTER TABLE "ZENK"."zenq_weight_config"
            ADD COLUMN IF NOT EXISTS analysis_json JSONB NOT NULL DEFAULT '{}'::jsonb
        """))

    logger.info("Migration 041 complete.")
