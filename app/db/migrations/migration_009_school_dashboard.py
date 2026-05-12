import asyncio
import logging
from sqlalchemy import text
from app.db.session import engine

logger = logging.getLogger(__name__)


async def run_migration():
    logger.info("=== Migration 009: School Dashboard ===")

    async with engine.connect() as conn:
        await conn.execute(text("COMMIT"))
        try:
            await conn.execute(text(
                "ALTER TYPE \"ZENK\".persona_enum ADD VALUE IF NOT EXISTS 'school'"
            ))
            logger.info("  -> 'school' added to persona_enum.")
        except Exception as e:
            logger.warning(f"  -> persona_enum alter skipped: {e}")

    async with engine.begin() as conn:
        logger.info("Creating school_profiles...")
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "ZENK"."school_profiles" (
                id               UUID         PRIMARY KEY REFERENCES "ZENK"."signup_requests"(id) ON DELETE CASCADE,
                school_name      VARCHAR(300) NOT NULL,
                school_code      VARCHAR(50)  NOT NULL DEFAULT 'ZNK-SCH-0000-000',
                affiliation      VARCHAR(100) NOT NULL DEFAULT 'CBSE',
                city             VARCHAR(120) NOT NULL,
                district         VARCHAR(120) NOT NULL,
                principal_name   VARCHAR(200) NOT NULL,
                partner_since    VARCHAR(20),
                is_partner       BOOLEAN      NOT NULL DEFAULT TRUE,
                fy_current       VARCHAR(20)  NOT NULL DEFAULT '2025-26',
                total_enrolled   INTEGER      NOT NULL DEFAULT 0,
                avg_attendance   FLOAT        NOT NULL DEFAULT 0.0,
                avg_academic_score FLOAT      NOT NULL DEFAULT 0.0,
                next_zqa_date    VARCHAR(20),
                reports_pending  INTEGER      NOT NULL DEFAULT 0,
                created_at       TIMESTAMP    NOT NULL DEFAULT NOW(),
                updated_at       TIMESTAMP    NOT NULL DEFAULT NOW()
            )
        """))

        logger.info("Creating school_students...")
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "ZENK"."school_students" (
                id                           UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
                school_id                    UUID         NOT NULL REFERENCES "ZENK"."school_profiles"(id) ON DELETE CASCADE,
                full_name                    VARCHAR(200) NOT NULL,
                grade                        VARCHAR(50)  NOT NULL,
                circle_id                    UUID         REFERENCES "ZENK"."sponsor_circles"(id) ON DELETE SET NULL,
                circle_name                  VARCHAR(200),
                attendance_pct               FLOAT        NOT NULL DEFAULT 0.0,
                avg_score                    FLOAT        NOT NULL DEFAULT 0.0,
                zqa_score                    FLOAT        NOT NULL DEFAULT 0.0,
                risk_level                   VARCHAR(20)  NOT NULL DEFAULT 'Low',
                q_report_status              VARCHAR(20)  NOT NULL DEFAULT 'Pending',
                tutor_recommendation         TEXT,
                tutor_recommendation_status  VARCHAR(20)  NOT NULL DEFAULT 'none',
                created_at                   TIMESTAMP    NOT NULL DEFAULT NOW()
            )
        """))

        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_school_students_school_id ON \"ZENK\".\"school_students\"(school_id)"
        ))

        logger.info("Creating school_reports...")
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "ZENK"."school_reports" (
                id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
                school_id    UUID        NOT NULL REFERENCES "ZENK"."school_profiles"(id) ON DELETE CASCADE,
                student_id   UUID        NOT NULL REFERENCES "ZENK"."school_students"(id) ON DELETE CASCADE,
                quarter      VARCHAR(10) NOT NULL,
                fy           VARCHAR(20) NOT NULL DEFAULT '2025-26',
                submitted_at TIMESTAMP,
                kia_draft    TEXT,
                status       VARCHAR(20) NOT NULL DEFAULT 'Pending',
                created_at   TIMESTAMP   NOT NULL DEFAULT NOW()
            )
        """))

        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_school_reports_school_id ON \"ZENK\".\"school_reports\"(school_id)"
        ))

        logger.info("Creating school_attendance...")
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "ZENK"."school_attendance" (
                id             UUID     PRIMARY KEY DEFAULT gen_random_uuid(),
                student_id     UUID     NOT NULL REFERENCES "ZENK"."school_students"(id) ON DELETE CASCADE,
                month          INTEGER  NOT NULL,
                year           INTEGER  NOT NULL,
                attendance_pct FLOAT    NOT NULL DEFAULT 0.0,
                working_days   INTEGER  NOT NULL DEFAULT 25,
                days_present   INTEGER  NOT NULL DEFAULT 0
            )
        """))

        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_school_attendance_student_id ON \"ZENK\".\"school_attendance\"(student_id)"
        ))

        logger.info("Creating school_kia_messages...")
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "ZENK"."school_kia_messages" (
                id         UUID      PRIMARY KEY DEFAULT gen_random_uuid(),
                school_id  UUID      NOT NULL REFERENCES "ZENK"."school_profiles"(id) ON DELETE CASCADE,
                role       VARCHAR(20) NOT NULL,
                text       TEXT      NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))

        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_school_kia_messages_school_id ON \"ZENK\".\"school_kia_messages\"(school_id)"
        ))

        logger.info("Creating school_kia_welcome...")
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "ZENK"."school_kia_welcome" (
                id              UUID      PRIMARY KEY REFERENCES "ZENK"."school_profiles"(id) ON DELETE CASCADE,
                welcome_sent    BOOLEAN   NOT NULL DEFAULT FALSE,
                welcome_message TEXT,
                task_list       JSONB     DEFAULT '[]'::jsonb,
                created_at      TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))

    logger.info("=== Migration 009 complete ===")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_migration())
