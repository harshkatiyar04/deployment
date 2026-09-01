"""Parental consent log — required by student family hats and chat consent gate."""

import logging

from sqlalchemy import text

from app.db.session import engine

logger = logging.getLogger(__name__)


async def run_migration() -> None:
    logger.info("=== Migration 047: parental_consent_log ===")
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS "ZENK".parental_consent_log (
                id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                student_id            UUID NOT NULL
                    REFERENCES "ZENK".signup_requests(id) ON DELETE CASCADE,
                consent_type          VARCHAR(100) NOT NULL,
                verified_by_admin_id  UUID NOT NULL
                    REFERENCES "ZENK".signup_requests(id),
                verified_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                expires_at            TIMESTAMPTZ,
                notes                 TEXT,
                created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """
            )
        )
        await conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS ix_parental_consent_student_id
            ON "ZENK".parental_consent_log(student_id)
        """
            )
        )
    logger.info("Migration 047 complete.")
