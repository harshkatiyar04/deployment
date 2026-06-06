"""Clear demo seed budgets on circles that were never explicitly set by a leader."""

import asyncio
import logging

from sqlalchemy import text

from app.db.session import engine

logger = logging.getLogger(__name__)


async def run_migration():
    logger.info("=== Migration 027: Zero unset circle budgets ===")

    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
            UPDATE "ZENK".sponsor_circles
            SET annual_budget = 0,
                budget_spent = 0,
                budget_collected = 0
            WHERE budget_set_at IS NULL
            """
            )
        )
    logger.info("Migration 027 complete.")


if __name__ == "__main__":
    asyncio.run(run_migration())
