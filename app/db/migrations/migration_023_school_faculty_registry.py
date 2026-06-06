"""School faculty registry + student faculty link columns."""

import asyncio
import logging

from sqlalchemy import text

from app.db.session import engine

logger = logging.getLogger(__name__)


async def run_migration():
    logger.info("=== Migration 023: School faculty registry ===")

    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'ZENK' AND table_name = 'school_profiles'
                ) AND NOT EXISTS (
                    SELECT 1 FROM pg_constraint c
                    JOIN pg_class t ON c.conrelid = t.oid
                    JOIN pg_namespace n ON t.relnamespace = n.oid
                    WHERE n.nspname = 'ZENK'
                      AND t.relname = 'school_profiles'
                      AND c.contype = 'p'
                ) THEN
                    ALTER TABLE "ZENK".school_profiles ADD PRIMARY KEY (id);
                END IF;
            EXCEPTION
                WHEN invalid_table_definition THEN
                    RAISE NOTICE 'school_profiles PK repair skipped: %', SQLERRM;
            END $$;
            """
            )
        )
        await conn.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS "ZENK".school_faculty (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                school_id UUID NOT NULL,
                display_name VARCHAR(200) NOT NULL,
                faculty_role VARCHAR(30) NOT NULL,
                subject VARCHAR(100),
                email VARCHAR(320),
                portal_member_id UUID,
                notes TEXT,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
            )
        )
        await conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS ix_school_faculty_school_role
            ON "ZENK".school_faculty(school_id, faculty_role)
            WHERE is_active = TRUE
            """
            )
        )
        await conn.execute(
            text(
                """
            ALTER TABLE "ZENK".school_students
            ADD COLUMN IF NOT EXISTS class_teacher_faculty_id UUID
            """
            )
        )
        await conn.execute(
            text(
                """
            ALTER TABLE "ZENK".school_students
            ADD COLUMN IF NOT EXISTS mentor_faculty_id UUID
            """
            )
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_migration())
