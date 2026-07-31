from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.db.config import db_settings


def _use_null_pool() -> bool:
    url = (db_settings.database_url_override or db_settings.database_url or "").lower()
    return bool(
        os.getenv("RAILWAY_ENVIRONMENT")
        or os.getenv("RAILWAY_PROJECT_ID")
        or "neon.tech" in url
    )


# Neon pooler + schema changes break asyncpg prepared statements.
# Unique names + cache size 0 is the supported Neon/SQLAlchemy pattern.
_CONNECT_ARGS = {
    "statement_cache_size": 0,
    "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4().hex}__",
}

_engine_kwargs: dict = {
    "pool_pre_ping": True,
    "connect_args": _CONNECT_ARGS,
}

if _use_null_pool():
    # No long-lived pooled prepared plans across Neon restores.
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
    """Drop pooled connections (no-op-ish with NullPool; safe after migrations)."""
    await engine.dispose()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
