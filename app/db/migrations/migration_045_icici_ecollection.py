"""ICICI eCollection MH7 tables (VAN registry, transactions, webhook events).

Runtime models live in app.banking.models.icici_ecollection — keep this migration
in app/db/migrations for numbered history.
"""

from __future__ import annotations

import logging

from sqlalchemy import text

from app.db.session import engine

logger = logging.getLogger(__name__)


async def run_migration() -> None:
    logger.info("=== Migration 045: ICICI eCollection ===")
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS "ZENK".ecollection_vans (
                    id UUID PRIMARY KEY,
                    client_code VARCHAR(6) NOT NULL,
                    van_suffix VARCHAR(30) NOT NULL,
                    van VARCHAR(35) NOT NULL,
                    circle_id UUID NOT NULL,
                    member_user_id UUID NULL,
                    purpose VARCHAR(120) NULL,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
        )
        await conn.execute(
            text(
                'CREATE UNIQUE INDEX IF NOT EXISTS uq_ecollection_van '
                'ON "ZENK".ecollection_vans (van)'
            )
        )
        await conn.execute(
            text(
                'CREATE INDEX IF NOT EXISTS ix_ecollection_vans_circle '
                'ON "ZENK".ecollection_vans (circle_id)'
            )
        )

        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS "ZENK".ecollection_transactions (
                    id UUID PRIMARY KEY,
                    utr VARCHAR(40) NOT NULL,
                    amount_paise INTEGER NOT NULL,
                    amount_inr VARCHAR(20) NOT NULL,
                    currency_code VARCHAR(10) NOT NULL DEFAULT 'INR',
                    van VARCHAR(35) NOT NULL,
                    client_code VARCHAR(6) NOT NULL,
                    payment_mode VARCHAR(16) NULL,
                    remitter_name VARCHAR(80) NULL,
                    remitter_account VARCHAR(40) NULL,
                    remitter_ifsc VARCHAR(16) NULL,
                    circle_id UUID NULL,
                    status VARCHAR(24) NOT NULL DEFAULT 'pending_validate',
                    reject_reason VARCHAR(80) NULL,
                    reject_code VARCHAR(20) NULL,
                    bank_tran_date VARCHAR(20) NULL,
                    credited_at TIMESTAMPTZ NULL,
                    ledger_posted BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
        )
        await conn.execute(
            text(
                'CREATE UNIQUE INDEX IF NOT EXISTS uq_ecollection_utr_amount '
                'ON "ZENK".ecollection_transactions (utr, amount_paise)'
            )
        )
        await conn.execute(
            text(
                'CREATE INDEX IF NOT EXISTS ix_ecollection_txn_van '
                'ON "ZENK".ecollection_transactions (van)'
            )
        )

        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS "ZENK".ecollection_events (
                    id UUID PRIMARY KEY,
                    event_type VARCHAR(24) NOT NULL,
                    transaction_id UUID NULL,
                    utr VARCHAR(40) NULL,
                    request_payload JSONB NULL,
                    response_payload JSONB NULL,
                    http_status INTEGER NOT NULL DEFAULT 200,
                    client_ip VARCHAR(64) NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
        )
        await conn.execute(
            text(
                'CREATE INDEX IF NOT EXISTS ix_ecollection_events_type '
                'ON "ZENK".ecollection_events (event_type)'
            )
        )
    logger.info("=== Migration 045 complete ===")
