"""Circle finance event log for Kia updates (credits + disbursements)."""

import asyncio
import logging

from sqlalchemy import text

from app.db.session import engine

logger = logging.getLogger(__name__)


async def run_migration():
    logger.info("=== Migration 046: Circle finance events ===")

    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS "ZENK".circle_finance_events (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                circle_id UUID NOT NULL,
                event_type VARCHAR(40) NOT NULL,
                status VARCHAR(20) NOT NULL,
                source VARCHAR(30) NOT NULL DEFAULT 'banking',
                text TEXT NOT NULL,
                amount_inr INTEGER,
                amount_paise INTEGER,
                remitter_name VARCHAR(120),
                payment_mode VARCHAR(20),
                utr VARCHAR(80),
                disbursement_id UUID,
                payee_name VARCHAR(200),
                gateway_ref VARCHAR(120),
                idempotency_key VARCHAR(180) NOT NULL UNIQUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
            )
        )
        await conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS idx_circle_finance_events_circle
                ON "ZENK".circle_finance_events(circle_id, created_at DESC)
            """
            )
        )
        await conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS idx_circle_finance_events_type
                ON "ZENK".circle_finance_events(event_type, status, created_at DESC)
            """
            )
        )
        await conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS idx_circle_finance_events_disbursement
                ON "ZENK".circle_finance_events(disbursement_id)
            """
            )
        )
    logger.info("Migration 046 complete.")


if __name__ == "__main__":
    asyncio.run(run_migration())
