"""Month-end auto-seal — previous calendar month at ~02:00 IST (no Admin required)."""

from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import settings
from app.services.zenq_v2.close import close_month

logger = logging.getLogger(__name__)

# IST = UTC+5:30 (avoid ZoneInfo/tzdata dependency on Windows)
IST = timezone(timedelta(hours=5, minutes=30))


def previous_calendar_month(as_of: Optional[date] = None) -> date:
    """Month to close on day-1 02:00 IST = prior calendar month."""
    today = as_of or datetime.now(IST).date()
    first = date(today.year, today.month, 1)
    prev_last = first - timedelta(days=1)
    return date(prev_last.year, prev_last.month, 1)


async def run_scheduled_close(db: AsyncSession, *, as_of: Optional[date] = None) -> dict[str, Any]:
    """Seal previous month for ladder/awards history. Live walls do not wait for this."""
    if not (
        settings.zenq_v2_close
        or settings.zenq_v2_product
        or settings.zenq_v2_ledger
    ):
        return {"ok": False, "skipped": True, "reason": "zenq_v2 flags off"}
    from app.algorithms.zenq_v2.params import LAUNCH_PARAMS

    if bool(LAUNCH_PARAMS.get("pilot_no_seal", True)):
        return {
            "ok": False,
            "skipped": True,
            "reason": "pilot_no_seal",
            "hint": "Month-end auto-seal disabled during pilot",
        }
    month = previous_calendar_month(as_of)
    logger.info("[zenq_v2] auto-seal starting for %s", month.isoformat())
    # admin_trigger=True so seal runs even if CLOSE flag briefly off when PRODUCT is on
    return await close_month(db, month, admin_trigger=True)


async def _month_end_seal_loop() -> None:
    """Background loop: on 1st of month after 02:00 IST, seal previous month once per day."""
    from app.db.session import SessionLocal

    last_ran: Optional[str] = None
    while True:
        try:
            now = datetime.now(IST)
            key = now.date().isoformat()
            if (
                now.day == 1
                and now.hour >= 2
                and last_ran != key
                and (
                    settings.zenq_v2_close
                    or settings.zenq_v2_product
                    or settings.zenq_v2_ledger
                )
            ):
                async with SessionLocal() as db:
                    result = await run_scheduled_close(db, as_of=now.date())
                logger.info("[zenq_v2] auto-seal result: %s", result)
                last_ran = key
        except Exception:
            logger.exception("[zenq_v2] auto-seal loop error")
        await asyncio.sleep(30 * 60)


def start_month_end_seal_task() -> None:
    from app.algorithms.zenq_v2.params import LAUNCH_PARAMS

    if bool(LAUNCH_PARAMS.get("pilot_no_seal", True)):
        logger.info("[zenq_v2] month-end auto-seal skipped (pilot_no_seal)")
        return
    asyncio.create_task(_month_end_seal_loop())
    logger.info("[zenq_v2] month-end auto-seal task started")
