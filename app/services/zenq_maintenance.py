"""Scheduled ZenQ maintenance tasks (Phase 4–5)."""

from __future__ import annotations

import asyncio
import logging

from app.core.settings import settings
from app.db.session import SessionLocal
from app.services.zenq_welfare_scan import run_welfare_scan_all_circles
from app.services.zenq_weight_recalibration import run_scheduled_recalibration_proposal

logger = logging.getLogger(__name__)

WELFARE_SCAN_INTERVAL_SEC = 24 * 60 * 60
RECALIBRATION_INTERVAL_SEC = 7 * 24 * 60 * 60


async def zenq_maintenance_loop() -> None:
    """Daily welfare scan + weekly weight proposal while the server is up."""
    await asyncio.sleep(120)
    welfare_due = 0.0
    recalibration_due = RECALIBRATION_INTERVAL_SEC

    while True:
        try:
            async with SessionLocal() as session:
                if welfare_due <= 0:
                    result = await run_welfare_scan_all_circles(session)
                    logger.info("[ZenQ maintenance] welfare scan complete: %s", result)
                    welfare_due = float(WELFARE_SCAN_INTERVAL_SEC)

                if settings.zenq_recalibration_enabled and recalibration_due <= 0:
                    proposal = await run_scheduled_recalibration_proposal()
                    logger.info("[ZenQ maintenance] recalibration proposal: %s", proposal)
                    recalibration_due = float(RECALIBRATION_INTERVAL_SEC)
        except Exception:
            logger.exception("[ZenQ maintenance] loop iteration failed")

        sleep_sec = min(welfare_due, recalibration_due if settings.zenq_recalibration_enabled else welfare_due)
        await asyncio.sleep(max(60.0, sleep_sec))
        welfare_due -= sleep_sec
        if settings.zenq_recalibration_enabled:
            recalibration_due -= sleep_sec
