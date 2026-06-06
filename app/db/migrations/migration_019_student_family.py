"""Student–parent family links, member_kind, login_access_tier."""

import asyncio
import logging

from sqlalchemy import text

from app.db.session import engine

logger = logging.getLogger(__name__)


async def run_migration():
    logger.info("=== Migration 019: Student family links ===")
    async with engine.begin() as conn:
        await conn.execute(text("""
            ALTER TABLE "ZENK".signup_requests
            ADD COLUMN IF NOT EXISTS member_kind VARCHAR(30)
        """))
        await conn.execute(text("""
            ALTER TABLE "ZENK".signup_requests
            ADD COLUMN IF NOT EXISTS guardian_relationship VARCHAR(50)
        """))
        await conn.execute(text("""
            ALTER TABLE "ZENK".signup_requests
            ADD COLUMN IF NOT EXISTS login_access_tier VARCHAR(30)
        """))
        await conn.execute(text("""
            ALTER TABLE "ZENK".signup_requests
            ADD COLUMN IF NOT EXISTS linked_student_signup_id UUID
        """))

        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "ZENK".student_family_links (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                student_signup_id UUID NOT NULL
                    REFERENCES "ZENK".signup_requests(id) ON DELETE CASCADE,
                parent_signup_id UUID NOT NULL
                    REFERENCES "ZENK".signup_requests(id) ON DELETE CASCADE,
                relationship VARCHAR(50) NOT NULL DEFAULT 'parent',
                circle_id UUID
                    REFERENCES "ZENK".sponsor_circles(id) ON DELETE SET NULL,
                school_student_id UUID,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                CONSTRAINT uq_student_family_pair UNIQUE (student_signup_id, parent_signup_id)
            )
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_student_family_student
            ON "ZENK".student_family_links(student_signup_id)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_student_family_parent
            ON "ZENK".student_family_links(parent_signup_id)
        """))

        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "ZENK".parent_academic_submissions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                parent_signup_id UUID NOT NULL
                    REFERENCES "ZENK".signup_requests(id) ON DELETE CASCADE,
                student_signup_id UUID NOT NULL
                    REFERENCES "ZENK".signup_requests(id) ON DELETE CASCADE,
                school_student_id UUID,
                document_type VARCHAR(40) NOT NULL DEFAULT 'marksheet',
                file_url TEXT NOT NULL,
                original_filename VARCHAR(512),
                status VARCHAR(30) NOT NULL DEFAULT 'pending_principal',
                principal_note TEXT,
                reviewed_by UUID
                    REFERENCES "ZENK".signup_requests(id) ON DELETE SET NULL,
                reviewed_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_parent_academic_parent
            ON "ZENK".parent_academic_submissions(parent_signup_id)
        """))
    logger.info("Migration 019 complete.")


if __name__ == "__main__":
    asyncio.run(run_migration())
