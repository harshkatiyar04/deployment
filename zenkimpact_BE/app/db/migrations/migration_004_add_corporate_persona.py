"""Migration 004: Add 'corporate' value to the persona_enum type."""
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = logging.getLogger(__name__)


async def run_migration(session: AsyncSession) -> None:
    """Add 'corporate' to the persona_enum Postgres enum type if it doesn't exist."""
    try:
        # Check if the value already exists
        result = await session.execute(
            text("SELECT 1 FROM pg_enum WHERE enumlabel = 'corporate' AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'persona_enum' AND typnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'ZENK'))")
        )
        exists = result.scalar_one_or_none()

        if not exists:
            # ALTER TYPE must be run outside a transaction block in some Postgres versions,
            # but asyncpg handles this fine via COMMIT + re-open
            await session.execute(text("COMMIT"))
            await session.execute(text('ALTER TYPE "ZENK".persona_enum ADD VALUE IF NOT EXISTS \'corporate\''))
            logger.info("[Migration 004] Added 'corporate' to persona_enum.")
        else:
            logger.info("[Migration 004] 'corporate' already exists in persona_enum. Skipping.")
    except Exception as e:
        logger.warning(f"[Migration 004] Could not alter persona_enum: {e}")
