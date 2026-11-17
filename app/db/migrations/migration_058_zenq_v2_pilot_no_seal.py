"""Migration 058: ZenQ v2 pilot — ladder min 1, no seals."""

from __future__ import annotations

import json
import logging

from sqlalchemy import text

from app.algorithms.zenq_v2.params import ALGORITHM_VERSION, LAUNCH_PARAMS
from app.db.session import engine

logger = logging.getLogger(__name__)


async def run_migration() -> None:
    logger.info("=== Migration 058: zenq_v2 pilot no-seal params %s ===", ALGORITHM_VERSION)
    params = json.dumps(LAUNCH_PARAMS)
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                INSERT INTO "ZENK"."zenq_v2_weights"(
                    version_id, effective_from, params_json, approved_by
                ) VALUES (
                    :vid, CURRENT_DATE, CAST(:pj AS jsonb), 'system-pilot-no-seal'
                )
                ON CONFLICT (version_id) DO UPDATE SET
                    params_json = EXCLUDED.params_json,
                    effective_from = EXCLUDED.effective_from,
                    approved_by = EXCLUDED.approved_by
                """
            ),
            {"vid": ALGORITHM_VERSION, "pj": params},
        )
        await conn.execute(
            text(
                """
                UPDATE "ZENK"."zenq_v2_weights"
                SET params_json = CAST(:pj AS jsonb),
                    approved_by = 'system-pilot-no-seal-sync'
                WHERE version_id IN ('2.0.0-launch', '2.0.0', '2.1.0-launch', '2.1.0-design')
                """
            ),
            {"pj": params},
        )
    logger.info("Migration 058 complete")
