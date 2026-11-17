"""Migration 053: months_silent on zenq_v2_member_month for Phase 2 close."""

from __future__ import annotations

import logging

from sqlalchemy import text

from app.db.session import engine

logger = logging.getLogger(__name__)


async def run_migration() -> None:
    logger.info("=== Migration 053: zenq_v2 member months_silent ===")
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                ALTER TABLE "ZENK"."zenq_v2_member_month"
                ADD COLUMN IF NOT EXISTS months_silent INTEGER NOT NULL DEFAULT 0
                """
            )
        )
    logger.info("Migration 053 complete")
