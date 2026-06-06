"""Circle payees and vendor disbursements (ICICI gateway)."""

import asyncio
import logging

from sqlalchemy import text

from app.db.session import engine

logger = logging.getLogger(__name__)


async def run_migration():
    logger.info("=== Migration 026: Circle vendor payees + disbursements ===")

    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS "ZENK".circle_payees (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                circle_id UUID NOT NULL,
                display_name VARCHAR(200) NOT NULL,
                beneficiary_name VARCHAR(200) NOT NULL,
                category VARCHAR(32) NOT NULL DEFAULT 'other',
                bank_name VARCHAR(120),
                account_number VARCHAR(32) NOT NULL,
                ifsc VARCHAR(16) NOT NULL,
                upi_id VARCHAR(64),
                notes TEXT,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_by UUID NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
            )
        )
        await conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS idx_circle_payees_circle
                ON "ZENK".circle_payees(circle_id, is_active, created_at DESC)
            """
            )
        )
        await conn.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS "ZENK".circle_disbursements (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                circle_id UUID NOT NULL,
                payee_id UUID NOT NULL REFERENCES "ZENK".circle_payees(id) ON DELETE RESTRICT,
                amount_inr INTEGER NOT NULL,
                description VARCHAR(300) NOT NULL,
                category VARCHAR(32) NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                due_date DATE,
                gateway_provider VARCHAR(20) NOT NULL DEFAULT 'icici',
                gateway_session_id VARCHAR(64),
                gateway_ref VARCHAR(120),
                created_by UUID NOT NULL,
                paid_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
            )
        )
        await conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS idx_circle_disbursements_circle
                ON "ZENK".circle_disbursements(circle_id, status, created_at DESC)
            """
            )
        )
    logger.info("Migration 026 complete.")


if __name__ == "__main__":
    asyncio.run(run_migration())
