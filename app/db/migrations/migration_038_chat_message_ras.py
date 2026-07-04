"""Migration 038: chat message RAS + substantive flags for ZenQ Phase 1.

Fast path: metadata-only ADD COLUMN (no table scan). Index omitted here —
chat_messages already has ix_chat_messages_channel_id; a partial index on the
full history can take minutes and block startup on Neon.
"""

from __future__ import annotations

import logging

from sqlalchemy import text

from app.db.session import engine

logger = logging.getLogger(__name__)


async def _ras_columns_present(conn) -> bool:
    res = await conn.execute(text("""
        SELECT COUNT(*)::int
        FROM information_schema.columns
        WHERE table_schema = 'ZENK'
          AND table_name = 'chat_messages'
          AND column_name IN ('ras_score', 'zenq_substantive')
    """))
    return int(res.scalar() or 0) >= 2


async def run_migration() -> None:
    logger.info("=== Migration 038: chat_messages RAS columns ===")

    async with engine.connect() as conn:
        if await _ras_columns_present(conn):
            logger.info("Migration 038: ras_score + zenq_substantive already present — skip")
            return

    # Short DDL transactions; avoid NOT NULL + index build on large tables.
    statements = (
        """
        ALTER TABLE "ZENK"."chat_messages"
        ADD COLUMN IF NOT EXISTS ras_score DOUBLE PRECISION
        """,
        """
        ALTER TABLE "ZENK"."chat_messages"
        ADD COLUMN IF NOT EXISTS zenq_substantive BOOLEAN DEFAULT FALSE
        """,
    )
    for sql in statements:
        async with engine.begin() as conn:
            await conn.execute(text("SET LOCAL lock_timeout = '15s'"))
            await conn.execute(text("SET LOCAL statement_timeout = '90s'"))
            await conn.execute(text(sql))

    logger.info("Migration 038 complete (columns only; no index — use channel_id index).")
