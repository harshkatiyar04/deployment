"""
Migration 007 — Mentor Dashboard
=================================
Adds the `mentor` value to the Persona enum and creates the three
mentor tables: mentor_profiles, mentor_sessions, mentor_uplift_actions.
"""
import asyncio
import logging
from app.db.session import engine
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_migration():
    logger.info("=== Migration 007: Mentor Dashboard ===")

    # ── Step 1: ALTER TYPE must run OUTSIDE a transaction ──────────────────
    logger.info("Step 1: Adding 'mentor' to persona_enum...")
    async with engine.connect() as conn:
        await conn.execute(text("COMMIT"))
        try:
            await conn.execute(text(
                "ALTER TYPE \"ZENK\".persona_enum ADD VALUE IF NOT EXISTS 'mentor'"
            ))
            logger.info("  -> 'mentor' added.")
        except Exception as e:
            logger.warning(f"  -> Could not alter enum (may already exist): {e}")

    # ── Steps 2-5: DDL in separate single-statement executions ─────────────
    async with engine.begin() as conn:
        logger.info("Step 2: Creating mentor_profiles table...")
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "ZENK"."mentor_profiles" (
                id                      UUID PRIMARY KEY REFERENCES "ZENK"."signup_requests"(id) ON DELETE CASCADE,
                mentor_id               VARCHAR(50)  NOT NULL DEFAULT 'ZNK-MEN-0000-000',
                specialty               VARCHAR(200) NOT NULL DEFAULT 'Technology & career mentoring',
                city                    VARCHAR(100) NOT NULL DEFAULT 'Bengaluru',
                tier                    INTEGER      NOT NULL DEFAULT 1,
                tier_label              VARCHAR(50)  NOT NULL DEFAULT 'Tier 1 — Rising',
                sessions_this_fy        INTEGER      NOT NULL DEFAULT 0,
                hours_mentored          FLOAT        NOT NULL DEFAULT 0.0,
                inspire_index           FLOAT        NOT NULL DEFAULT 0.0,
                inspire_index_percentile INTEGER     NOT NULL DEFAULT 0,
                inspire_index_delta     FLOAT        NOT NULL DEFAULT 0.0,
                zenq_contribution       FLOAT        NOT NULL DEFAULT 0.0,
                community_uplift_count  INTEGER      NOT NULL DEFAULT 0,
                inspire_breakdown       JSONB                 DEFAULT '{}'::jsonb,
                assigned_circles        JSONB                 DEFAULT '[]'::jsonb,
                badges                  JSONB                 DEFAULT '[]'::jsonb,
                kia_insight             TEXT,
                created_at              TIMESTAMP    NOT NULL DEFAULT NOW(),
                updated_at              TIMESTAMP    NOT NULL DEFAULT NOW()
            )
        """))

        logger.info("Step 3: Creating mentor_sessions table...")
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "ZENK"."mentor_sessions" (
                id                  UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
                mentor_id           UUID         NOT NULL REFERENCES "ZENK"."mentor_profiles"(id) ON DELETE CASCADE,
                student_circle      VARCHAR(200) NOT NULL,
                session_date        VARCHAR(20)  NOT NULL,
                topic_area          VARCHAR(200) NOT NULL,
                duration_hrs        FLOAT        NOT NULL DEFAULT 0.5,
                mode                VARCHAR(100) NOT NULL DEFAULT 'ZenK Circle Chat video call',
                engagement_level    VARCHAR(100) NOT NULL DEFAULT 'Engaged',
                session_notes       TEXT,
                inspiration_shared  TEXT,
                zenq_impact         FLOAT        NOT NULL DEFAULT 0.0,
                inspire_pts         FLOAT        NOT NULL DEFAULT 0.0,
                created_at          TIMESTAMP    NOT NULL DEFAULT NOW()
            )
        """))

        logger.info("Step 4: Index on mentor_sessions...")
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_mentor_sessions_mentor_id ON \"ZENK\".\"mentor_sessions\"(mentor_id)"
        ))

        logger.info("Step 5: Creating mentor_uplift_actions table...")
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "ZENK"."mentor_uplift_actions" (
                id           UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
                mentor_id    UUID         NOT NULL REFERENCES "ZENK"."mentor_profiles"(id) ON DELETE CASCADE,
                action_type  VARCHAR(100) NOT NULL,
                title        VARCHAR(300) NOT NULL,
                description  TEXT,
                event_date   VARCHAR(20)  NOT NULL,
                impact_score FLOAT        NOT NULL DEFAULT 0.8,
                verified     BOOLEAN      NOT NULL DEFAULT FALSE,
                created_at   TIMESTAMP    NOT NULL DEFAULT NOW()
            )
        """))

        logger.info("Step 6: Index on mentor_uplift_actions...")
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_mentor_uplift_mentor_id ON \"ZENK\".\"mentor_uplift_actions\"(mentor_id)"
        ))

    logger.info("=== Migration 007 complete ===")


if __name__ == "__main__":
    asyncio.run(run_migration())
