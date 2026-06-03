import asyncio
import logging
from sqlalchemy import text
from app.db.session import engine

logger = logging.getLogger(__name__)


async def run_migration():
    logger.info("=== Migration 013: School ZQA audit snapshots ===")

    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "ZENK"."school_zqa_snapshots" (
                id                  UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
                school_id           UUID         NOT NULL REFERENCES "ZENK"."school_profiles"(id) ON DELETE CASCADE,
                student_id          UUID         NOT NULL REFERENCES "ZENK"."school_students"(id) ON DELETE CASCADE,
                quarter             VARCHAR(10)  NOT NULL,
                fy                  VARCHAR(20)  NOT NULL DEFAULT '2025-26',
                zqa_composite       FLOAT        NOT NULL DEFAULT 0.0,
                zqa_band            VARCHAR(50)  NOT NULL DEFAULT '1 - Beginning',
                spd                 FLOAT        NOT NULL DEFAULT 1.0,
                baseline_zqa        FLOAT,
                baseline_quarter    VARCHAR(10),
                zqa_baseline_delta  FLOAT        NOT NULL DEFAULT 0.0,
                zenq_contribution   FLOAT        NOT NULL DEFAULT 0.0,
                confidence          FLOAT        NOT NULL DEFAULT 0.0,
                breakdown_json      JSONB,
                validation_issues   JSONB        DEFAULT '[]'::jsonb,
                computed_at         TIMESTAMP    NOT NULL DEFAULT NOW(),
                UNIQUE (student_id, quarter)
            )
        """))
        await conn.execute(text(
            'CREATE INDEX IF NOT EXISTS idx_school_zqa_snapshots_school '
            'ON "ZENK"."school_zqa_snapshots"(school_id, quarter, computed_at DESC)'
        ))

    logger.info("Migration 013 complete.")


if __name__ == "__main__":
    asyncio.run(run_migration())
