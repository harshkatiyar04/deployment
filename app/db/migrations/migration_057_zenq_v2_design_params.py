"""Migration 057: ZenQ v2 full-design product params (2.1.0-design)."""

from __future__ import annotations

import json
import logging

from sqlalchemy import text

from app.algorithms.zenq_v2.params import ALGORITHM_VERSION, LAUNCH_PARAMS
from app.db.session import engine

logger = logging.getLogger(__name__)


async def run_migration() -> None:
    logger.info("=== Migration 057: zenq_v2 design params %s ===", ALGORITHM_VERSION)
    params = json.dumps(LAUNCH_PARAMS)
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                INSERT INTO "ZENK"."zenq_v2_weights"(
                    version_id, effective_from, params_json, approved_by
                ) VALUES (
                    :vid, CURRENT_DATE, CAST(:pj AS jsonb), 'system-design-live'
                )
                ON CONFLICT (version_id) DO UPDATE SET
                    params_json = EXCLUDED.params_json,
                    effective_from = EXCLUDED.effective_from,
                    approved_by = EXCLUDED.approved_by
                """
            ),
            {"vid": ALGORITHM_VERSION, "pj": params},
        )
        # Keep prior launch row aligned so any stale load still sees design dials.
        await conn.execute(
            text(
                """
                UPDATE "ZENK"."zenq_v2_weights"
                SET params_json = CAST(:pj AS jsonb),
                    approved_by = 'system-design-live-sync'
                WHERE version_id IN ('2.0.0-launch', '2.0.0', '2.1.0-launch')
                """
            ),
            {"pj": params},
        )
    logger.info("Migration 057 complete")
