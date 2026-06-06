import asyncio
import logging
from sqlalchemy import text
from app.db.session import engine

logger = logging.getLogger(__name__)


async def run_migration():
    logger.info("=== Migration 014: Circle invite tokens + student cart submissions ===")

    async with engine.begin() as conn:
        # Legacy DBs: parent tables may exist without PKs (breaks new FKs). Best-effort repair.
        for table in ("sponsor_circles", "signup_requests"):
            await conn.execute(
                text(
                    f"""
                    DO $$
                    BEGIN
                        IF EXISTS (
                            SELECT 1 FROM information_schema.tables
                            WHERE table_schema = 'ZENK' AND table_name = '{table}'
                        ) AND NOT EXISTS (
                            SELECT 1
                            FROM pg_constraint c
                            JOIN pg_class t ON c.conrelid = t.oid
                            JOIN pg_namespace n ON t.relnamespace = n.oid
                            WHERE n.nspname = 'ZENK'
                              AND t.relname = '{table}'
                              AND c.contype = 'p'
                        ) THEN
                            ALTER TABLE "ZENK".{table} ADD PRIMARY KEY (id);
                        END IF;
                    EXCEPTION
                        WHEN OTHERS THEN
                            RAISE NOTICE 'Could not add PK on {table}: %', SQLERRM;
                    END $$;
                    """
                )
            )

        # No REFERENCES — some local DBs lack PK/unique on parent ids; ORM still validates.
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "ZENK"."circle_invite_tokens" (
                id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                circle_id   UUID NOT NULL,
                token       VARCHAR(128) NOT NULL UNIQUE,
                created_by  UUID NOT NULL,
                expires_at  TIMESTAMPTZ NOT NULL,
                revoked_at  TIMESTAMPTZ,
                created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """))
        await conn.execute(text(
            'CREATE INDEX IF NOT EXISTS idx_circle_invite_token_circle '
            'ON "ZENK"."circle_invite_tokens"(circle_id, created_at DESC)'
        ))

        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "ZENK"."circle_student_cart_submissions" (
                id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                circle_id         UUID NOT NULL,
                submitted_by      UUID NOT NULL,
                status            VARCHAR(30) NOT NULL DEFAULT 'pending_leader',
                items_json        JSONB NOT NULL DEFAULT '[]'::jsonb,
                delivery_address  TEXT NOT NULL,
                phone_number      VARCHAR(20) NOT NULL,
                circle_name       VARCHAR(200),
                total_amount      INTEGER NOT NULL DEFAULT 0,
                note              TEXT,
                decided_by        UUID,
                decided_at        TIMESTAMPTZ,
                created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """))
        await conn.execute(text(
            'CREATE INDEX IF NOT EXISTS idx_cart_sub_circle_status '
            'ON "ZENK"."circle_student_cart_submissions"(circle_id, status, created_at DESC)'
        ))

    logger.info("Migration 014 complete.")


if __name__ == "__main__":
    asyncio.run(run_migration())
