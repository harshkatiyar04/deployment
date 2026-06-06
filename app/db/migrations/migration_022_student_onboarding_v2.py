"""Student onboarding v2: school interest, circle interest, probe chat."""

import asyncio
import logging

from sqlalchemy import text

from app.db.session import engine

logger = logging.getLogger(__name__)


async def run_migration():
    logger.info("=== Migration 022: Student onboarding v2 ===")

    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
            ALTER TABLE "ZENK".signup_requests
            ADD COLUMN IF NOT EXISTS selected_school_id UUID
            """
            )
        )
        await conn.execute(
            text(
                """
            ALTER TABLE "ZENK".signup_requests
            ADD COLUMN IF NOT EXISTS onboarding_version VARCHAR(10) DEFAULT 'v1'
            """
            )
        )

        await conn.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS "ZENK".student_school_interests (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                student_signup_id UUID NOT NULL,
                school_id UUID NOT NULL,
                status VARCHAR(30) NOT NULL DEFAULT 'pending_principal',
                principal_note TEXT,
                reviewed_by UUID,
                reviewed_at TIMESTAMPTZ,
                school_student_id UUID,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
            )
        )
        await conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS ix_student_school_interest_school
            ON "ZENK".student_school_interests(school_id, status)
            """
            )
        )
        await conn.execute(
            text(
                """
            CREATE UNIQUE INDEX IF NOT EXISTS ux_student_school_interest_student
            ON "ZENK".student_school_interests(student_signup_id)
            """
            )
        )

        await conn.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS "ZENK".student_circle_interest_requests (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                student_signup_id UUID NOT NULL,
                circle_id UUID NOT NULL,
                help_comment TEXT NOT NULL,
                status VARCHAR(30) NOT NULL DEFAULT 'pending_leader',
                leader_signup_id UUID,
                leader_note TEXT,
                pseudonym VARCHAR(120),
                probe_expires_at TIMESTAMPTZ,
                reviewed_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
            )
        )
        await conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS ix_student_circle_interest_circle
            ON "ZENK".student_circle_interest_requests(circle_id, status)
            """
            )
        )
        await conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS ix_student_circle_interest_student
            ON "ZENK".student_circle_interest_requests(student_signup_id, status)
            """
            )
        )

        await conn.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS "ZENK".student_probe_messages (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                interest_request_id UUID NOT NULL,
                sender_role VARCHAR(20) NOT NULL,
                sender_signup_id UUID NOT NULL,
                body TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
            )
        )
        await conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS ix_student_probe_messages_request
            ON "ZENK".student_probe_messages(interest_request_id, created_at)
            """
            )
        )

    logger.info("Migration 022 complete.")


if __name__ == "__main__":
    asyncio.run(run_migration())
