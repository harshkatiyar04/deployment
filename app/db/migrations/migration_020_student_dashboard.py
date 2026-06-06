"""Student dashboard: Kia messages, text mentoring, school student link."""

import asyncio
import logging

from sqlalchemy import text

from app.db.session import engine

logger = logging.getLogger(__name__)


async def run_migration():
    logger.info("=== Migration 020: Student dashboard ===")
    async with engine.begin() as conn:
        await conn.execute(text("""
            ALTER TABLE "ZENK".school_students
            ADD COLUMN IF NOT EXISTS signup_request_id UUID
                REFERENCES "ZENK".signup_requests(id) ON DELETE SET NULL
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_school_students_signup_request
            ON "ZENK".school_students(signup_request_id)
        """))

        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "ZENK".student_kia_messages (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                student_signup_id UUID NOT NULL
                    REFERENCES "ZENK".signup_requests(id) ON DELETE CASCADE,
                role VARCHAR(20) NOT NULL,
                text TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_student_kia_student
            ON "ZENK".student_kia_messages(student_signup_id)
        """))

        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "ZENK".student_mentoring_threads (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                student_signup_id UUID NOT NULL
                    REFERENCES "ZENK".signup_requests(id) ON DELETE CASCADE,
                circle_id UUID
                    REFERENCES "ZENK".sponsor_circles(id) ON DELETE SET NULL,
                title VARCHAR(200) NOT NULL DEFAULT 'Circle mentoring',
                status VARCHAR(30) NOT NULL DEFAULT 'open',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_student_mentoring_student
            ON "ZENK".student_mentoring_threads(student_signup_id)
        """))

        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "ZENK".student_mentoring_messages (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                thread_id UUID NOT NULL
                    REFERENCES "ZENK".student_mentoring_threads(id) ON DELETE CASCADE,
                sender_signup_id UUID NOT NULL
                    REFERENCES "ZENK".signup_requests(id) ON DELETE CASCADE,
                sender_role VARCHAR(30) NOT NULL,
                body TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_student_mentoring_msg_thread
            ON "ZENK".student_mentoring_messages(thread_id)
        """))
    logger.info("Migration 020 complete.")


if __name__ == "__main__":
    asyncio.run(run_migration())
