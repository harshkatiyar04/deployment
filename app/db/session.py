from __future__ import annotations

import logging
import os
from collections.abc import AsyncGenerator
from typing import Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.db.config import db_settings

logger = logging.getLogger(__name__)


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


def is_stale_prepared_plan_error(exc: BaseException) -> bool:
    msg = str(exc).lower()
    name = type(exc).__name__.lower()
    return (
        "invalidcachedstatementerror" in name
        or "invalidcachedstatementerror" in msg
        or "cached statement plan is invalid" in msg
    )


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


class RetryingAsyncSession(AsyncSession):
    """
    Neon/pgBouncer can raise InvalidCachedStatementError mid-request even with
    statement_cache_size=0. SQLAlchemy invalidates its caches after that error —
    one retry is enough for the same session.
    """

    async def execute(self, statement: Any, *args: Any, **kwargs: Any):
        try:
            return await super().execute(statement, *args, **kwargs)
        except Exception as exc:
            if not is_stale_prepared_plan_error(exc):
                raise
            logger.warning("[DB] Stale prepared plan on execute — retrying once")
            return await super().execute(statement, *args, **kwargs)


SessionLocal = async_sessionmaker(
    bind=engine,
    class_=RetryingAsyncSession,
    expire_on_commit=False,
)


async def reset_db_pool() -> None:
    """Dispose engine connections after DDL / migrations."""
    await engine.dispose()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
