"""Migration 054: ZenQ v2 partner_profile + partner_month (Phase 4 EPR)."""

from __future__ import annotations

import logging

from sqlalchemy import text

from app.db.session import engine

logger = logging.getLogger(__name__)


async def run_migration() -> None:
    logger.info("=== Migration 054: zenq_v2 partners / EPR ===")
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS "ZENK"."zenq_v2_partner_profile" (
                    partner_id      UUID PRIMARY KEY,
                    track           VARCHAR(16) NOT NULL DEFAULT 'MENTOR',
                    home_circle_id  UUID,
                    display_name    VARCHAR(256),
                    fee_per_hour    FLOAT NOT NULL DEFAULT 0,
                    availability    VARCHAR(64) NOT NULL DEFAULT 'available',
                    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
        )
        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS "ZENK"."zenq_v2_partner_month" (
                    partner_id                  UUID NOT NULL REFERENCES "ZENK"."zenq_v2_partner_profile"(partner_id) ON DELETE CASCADE,
                    month                       DATE NOT NULL,
                    students_served             INTEGER NOT NULL DEFAULT 0,
                    months_active               INTEGER NOT NULL DEFAULT 0,
                    mean_growth_ratio           FLOAT,
                    mean_attendance             FLOAT,
                    sparks_per_student_year     FLOAT NOT NULL DEFAULT 0,
                    delivered_ratio             FLOAT NOT NULL DEFAULT 1,
                    feedback                    FLOAT NOT NULL DEFAULT 4,
                    responsiveness              FLOAT NOT NULL DEFAULT 0.8,
                    shrunk_outcome              FLOAT,
                    reliability                 FLOAT,
                    epr                         FLOAT,
                    confidence_label            VARCHAR(16),
                    sessions_count              INTEGER NOT NULL DEFAULT 0,
                    closed_at                   TIMESTAMPTZ,
                    PRIMARY KEY (partner_id, month)
                )
                """
            )
        )
        await conn.execute(
            text(
                'CREATE INDEX IF NOT EXISTS idx_zenq_v2_partner_month_epr '
                'ON "ZENK"."zenq_v2_partner_month"(epr DESC NULLS LAST)'
            )
        )
    logger.info("Migration 054 complete")
