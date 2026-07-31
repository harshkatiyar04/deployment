from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.db.config import db_settings

# Neon + pgBouncer / schema restores invalidate asyncpg prepared plans.
# Disable statement cache so InvalidCachedStatementError cannot loop 503s after sync.
_CONNECT_ARGS = {"statement_cache_size": 0}

engine: AsyncEngine = create_async_engine(
    db_settings.database_url,
    pool_pre_ping=True,
    pool_size=db_settings.db_pool_size,
    max_overflow=db_settings.db_max_overflow,
    pool_recycle=db_settings.db_pool_recycle_seconds,
    pool_timeout=db_settings.db_pool_timeout_seconds,
    connect_args=_CONNECT_ARGS,
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def reset_db_pool() -> None:
    """Drop pooled connections (needed after Neon schema restores / migrations)."""
    await engine.dispose()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
