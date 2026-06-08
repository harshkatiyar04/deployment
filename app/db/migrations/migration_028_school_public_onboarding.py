"""School public onboarding: signup fields + profile completion columns."""

import asyncio
import logging
from sqlalchemy import text
from app.db.session import engine

logger = logging.getLogger(__name__)


async def run_migration():
    logger.info("=== Migration 028: School public onboarding ===")
    async with engine.begin() as conn:
        for col, ddl in (
            ("school_name", "VARCHAR(300)"),
            ("school_principal_name", "VARCHAR(200)"),
            ("school_affiliation", "VARCHAR(100)"),
            ("school_affiliation_number", "VARCHAR(64)"),
            ("school_enrollment_year", "VARCHAR(10)"),
        ):
            try:
                await conn.execute(text(
                    f'ALTER TABLE "ZENK"."signup_requests" ADD COLUMN IF NOT EXISTS {col} {ddl}'
                ))
            except Exception as exc:
                logger.warning("signup_requests.%s: %s", col, exc)

        for col, ddl in (
            ("affiliation_number", "VARCHAR(64)"),
            ("enrollment_year", "VARCHAR(10)"),
            ("profile_completed_at", "TIMESTAMP"),
            ("onboarding_source", "VARCHAR(32) DEFAULT 'zenk_ops'"),
        ):
            try:
                await conn.execute(text(
                    f'ALTER TABLE "ZENK"."school_profiles" ADD COLUMN IF NOT EXISTS {col} {ddl}'
                ))
            except Exception as exc:
                logger.warning("school_profiles.%s: %s", col, exc)

        await conn.execute(text("""
            UPDATE "ZENK"."school_profiles"
            SET profile_completed_at = COALESCE(profile_completed_at, updated_at, NOW()),
                onboarding_source = COALESCE(onboarding_source, 'zenk_ops')
            WHERE profile_completed_at IS NULL
        """))
    logger.info("Migration 028 complete.")


if __name__ == "__main__":
    asyncio.run(run_migration())
