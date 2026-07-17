"""Add algorithm feedback fields to landing survey submissions."""

from __future__ import annotations

import logging

from sqlalchemy import text

from app.db.session import engine

logger = logging.getLogger(__name__)


async def run_migration() -> None:
    logger.info("=== Migration 044: Landing feedback algorithm fields ===")
    async with engine.begin() as conn:
        for col, coltype in (
            ("algorithm_clarity", "VARCHAR(80)"),
            ("most_useful_signal", "VARCHAR(120)"),
            ("trust_for_decisions", "VARCHAR(120)"),
        ):
            await conn.execute(
                text(
                    f'ALTER TABLE "ZENK"."landing_feedback_submissions" '
                    f"ADD COLUMN IF NOT EXISTS {col} {coltype}"
                )
            )
    logger.info("=== Migration 044 complete ===")
