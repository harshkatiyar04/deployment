"""DB transient-error detection and safe client-facing messages."""

from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable, TypeVar

from sqlalchemy.exc import DBAPIError, OperationalError

logger = logging.getLogger(__name__)

T = TypeVar("T")

SAFE_UNAVAILABLE_DETAIL = "Service temporarily unavailable. Please try again shortly."


def is_transient_db_error(exc: BaseException) -> bool:
    """True when the failure is likely a dropped remote Postgres connection."""
    if isinstance(exc, (OperationalError, DBAPIError)):
        return True
    msg = str(exc).lower()
    needles = (
        "connectiondoesnotexisterror",
        "connection was closed",
        "connection reset",
        "server closed the connection",
        "cannot call prepared_stmt",
        "connection refused",
    )
    return any(n in msg for n in needles)


def safe_service_unavailable_detail() -> str:
    """Generic API detail — never exposes SQL, hosts, or driver internals."""
    return SAFE_UNAVAILABLE_DETAIL


def sanitize_client_error_detail(detail: str | None) -> str:
    """Strip internal error fragments before returning to the browser."""
    if not detail:
        return SAFE_UNAVAILABLE_DETAIL
    lowered = detail.lower()
    if any(
        token in lowered
        for token in (
            "asyncpg",
            "sqlalchemy",
            "postgresql",
            "connection",
            "operationalerror",
            "dbapi",
            "select ",
            "insert ",
            "traceback",
        )
    ):
        return SAFE_UNAVAILABLE_DETAIL
    if len(detail) > 200:
        return SAFE_UNAVAILABLE_DETAIL
    return detail


async def with_db_retry(
    operation: Callable[[], Awaitable[T]],
    *,
    attempts: int = 2,
    delay_seconds: float = 0.35,
) -> T:
    """Run an async DB operation once; retry once on transient connection loss."""
    last_exc: BaseException | None = None
    for attempt in range(attempts):
        try:
            return await operation()
        except Exception as exc:
            last_exc = exc
            if attempt < attempts - 1 and is_transient_db_error(exc):
                logger.warning(
                    "db_transient_retry attempt=%s error_type=%s",
                    attempt + 1,
                    type(exc).__name__,
                )
                await asyncio.sleep(delay_seconds)
                continue
            raise
    assert last_exc is not None
    raise last_exc
