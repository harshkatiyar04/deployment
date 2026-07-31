from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.db.config import db_settings


def _is_neon_or_railway() -> bool:
    url = (
        db_settings.database_url_override
        or getattr(db_settings, "database_url", "")
        or os.getenv("DATABASE_URL")
        or ""
    ).lower()
    return bool(
        os.getenv("RAILWAY_ENVIRONMENT")
        or os.getenv("RAILWAY_PROJECT_ID")
        or "neon.tech" in url
    )


def _connect_args() -> dict:
    """
    Neon pooler (PgBouncer) + DDL/migrations invalidate prepared statements.
    Always disable asyncpg statement cache; unique names avoid cross-connection clashes.
    """
    return {
        "statement_cache_size": 0,
        "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4().hex}__",
    }


_engine_kwargs: dict = {
    "pool_pre_ping": True,
    "connect_args": _connect_args(),
}

# Prefer NullPool on Railway/Neon so connections never reuse stale server plans.
if _is_neon_or_railway():
    _engine_kwargs["poolclass"] = NullPool
else:
    _engine_kwargs.update(
        pool_size=db_settings.db_pool_size,
        max_overflow=db_settings.db_max_overflow,
        pool_recycle=db_settings.db_pool_recycle_seconds,
        pool_timeout=db_settings.db_pool_timeout_seconds,
    )

engine: AsyncEngine = create_async_engine(db_settings.database_url, **_engine_kwargs)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def reset_db_pool() -> None:
    """Dispose engine connections after DDL / migrations."""
    await engine.dispose()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
