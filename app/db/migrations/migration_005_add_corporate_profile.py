import asyncio
import logging
from app.db.session import engine
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_migration():
    """
    Creates the CorporateProfile table in the 'ZENK' schema.
    """
    async with engine.begin() as conn:
        logger.info("=== Phase 5 Corporate Profile Migration ===")

        logger.info("Creating corporate_profiles table...")
        await conn.execute(text('''
            CREATE TABLE IF NOT EXISTS "ZENK"."corporate_profiles" (
                "id" UUID PRIMARY KEY REFERENCES "ZENK"."signup_requests"("id") ON DELETE CASCADE,
                "company_name" VARCHAR(200) NOT NULL,
                "company_initials" VARCHAR(50) NOT NULL,
                "hq_city" VARCHAR(100) NOT NULL,
                "partner_since" VARCHAR(50) NOT NULL DEFAULT 'Apr 2024',
                "csr_schedule" VARCHAR(255) NOT NULL DEFAULT 'CSR Schedule VII — Item (ii): Education',
                "corporate_zenq" FLOAT NOT NULL DEFAULT 78.4,
                "total_csr_deployed" INTEGER NOT NULL DEFAULT 100000,
                "circles_funded" INTEGER NOT NULL DEFAULT 3,
                "employees_engaged" INTEGER NOT NULL DEFAULT 12,
                "unallocated" INTEGER NOT NULL DEFAULT 20000,
                "fy_label" VARCHAR(50) NOT NULL DEFAULT 'FY 2025-26',
                "badges" JSONB DEFAULT '[]'::jsonb,
                "zenq_trend" JSONB DEFAULT '[]'::jsonb,
                "circle_allocations" JSONB DEFAULT '[]'::jsonb,
                "circle_performance" JSONB DEFAULT '[]'::jsonb,
                "engagement_metrics" JSONB DEFAULT '[]'::jsonb,
                "top_contributors" JSONB DEFAULT '[]'::jsonb,
                "spend_by_category" JSONB DEFAULT '[]'::jsonb,
                "transactions" JSONB DEFAULT '[]'::jsonb
            );
        '''))

        logger.info("Corporate profile migration complete!")

if __name__ == "__main__":
    asyncio.run(run_migration())
