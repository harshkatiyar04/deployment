"""Student school referral invites (school not listed during student signup)."""

import asyncio
import logging

from sqlalchemy import text

from app.db.session import engine

logger = logging.getLogger(__name__)


async def run_migration():
    logger.info("=== Migration 033: Student school referrals ===")

    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS "ZENK".student_school_referrals (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                token VARCHAR(64) NOT NULL UNIQUE,
                student_signup_id UUID NOT NULL,
                proposed_school_name VARCHAR(300) NOT NULL,
                proposed_city VARCHAR(120) NOT NULL,
                proposed_state VARCHAR(120),
                proposed_contact_email VARCHAR(320),
                status VARCHAR(30) NOT NULL DEFAULT 'pending',
                school_signup_id UUID,
                school_profile_id UUID,
                expires_at TIMESTAMPTZ NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
            )
        )
        await conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS ix_student_school_referral_student
            ON "ZENK".student_school_referrals(student_signup_id)
            """
            )
        )
        await conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS ix_student_school_referral_school_signup
            ON "ZENK".student_school_referrals(school_signup_id)
            """
            )
        )

    logger.info("Migration 033 complete.")


if __name__ == "__main__":
    asyncio.run(run_migration())
