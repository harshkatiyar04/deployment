"""
Phase 2 Chat Migration — parental_consent_log table.

Run AFTER 001_chat_phase1 has been applied.

Usage:
    cd zenkimpact_BE
    python -m app.db.migrations.002_chat_phase2
"""
import asyncio

from sqlalchemy import text

from app.db.session import engine


async def run_migration() -> None:
    print("=== Phase 2 Chat Migration ===")
    async with engine.begin() as conn:

        print("Creating parental_consent_log...")
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "ZENK".parental_consent_log (
                id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                student_id            UUID NOT NULL REFERENCES "ZENK".signup_requests(id) ON DELETE CASCADE,
                consent_type          VARCHAR(100) NOT NULL,
                verified_by_admin_id  UUID NOT NULL REFERENCES "ZENK".signup_requests(id),
                verified_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                expires_at            TIMESTAMPTZ,
                notes                 TEXT,
                created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_parental_consent_student_id
            ON "ZENK".parental_consent_log(student_id)
        """))

    print("=== Phase 2 Migration Complete ===")


if __name__ == "__main__":
    asyncio.run(run_migration())
