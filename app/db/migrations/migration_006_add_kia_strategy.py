import asyncio
import logging
from app.db.session import engine
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_migration():
    """
    Alters the CorporateProfile table to add Kia Strategy fields.
    """
    async with engine.begin() as conn:
        logger.info("=== Phase 6 Kia Strategy Migration ===")

        logger.info("Adding industry_sector, corporate_goals, and strategy_brief columns...")
        await conn.execute(text('''
            ALTER TABLE "ZENK"."corporate_profiles"
            ADD COLUMN IF NOT EXISTS "industry_sector" VARCHAR(100) NOT NULL DEFAULT 'Technology sector',
            ADD COLUMN IF NOT EXISTS "corporate_goals" JSONB DEFAULT '[]'::jsonb,
            ADD COLUMN IF NOT EXISTS "strategy_brief" JSONB DEFAULT '{}'::jsonb;
        '''))

        logger.info("Kia Strategy migration complete!")

if __name__ == "__main__":
    asyncio.run(run_migration())
