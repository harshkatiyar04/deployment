"""Ensure school_students.id is a primary key (fixes FK drift from create_all)."""

import asyncio
import logging

from sqlalchemy import text

from app.db.session import engine

logger = logging.getLogger(__name__)


async def run_migration():
    logger.info("=== Migration 021: school_students PK repair ===")
    async with engine.begin() as conn:
        # Table may exist without PK if created via SQLAlchemy create_all before migration 009.
        await conn.execute(text("""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'ZENK' AND table_name = 'school_students'
                ) AND NOT EXISTS (
                    SELECT 1 FROM pg_constraint c
                    JOIN pg_class t ON c.conrelid = t.oid
                    JOIN pg_namespace n ON t.relnamespace = n.oid
                    WHERE n.nspname = 'ZENK'
                      AND t.relname = 'school_students'
                      AND c.contype = 'p'
                ) THEN
                    ALTER TABLE "ZENK".school_students ADD PRIMARY KEY (id);
                END IF;
            EXCEPTION
                WHEN duplicate_table THEN NULL;
                WHEN invalid_table_definition THEN
                    RAISE NOTICE 'school_students PK repair skipped: %', SQLERRM;
            END $$;
        """))
    logger.info("Migration 021 complete.")


if __name__ == "__main__":
    asyncio.run(run_migration())
