"""Run idempotent SQL migrations for school portal (010–013)."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def apply_all_migrations() -> None:
    from app.db.migrations.migration_010_school_rbac_audit import run_migration as m010
    from app.db.migrations.migration_011_school_portal_members import run_migration as m011
    from app.db.migrations.migration_012_school_portal_invites import run_migration as m012
    from app.db.migrations.migration_013_school_zqa_snapshots import run_migration as m013

    for label, fn in (
        ("010", m010),
        ("011", m011),
        ("012", m012),
        ("013", m013),
    ):
        try:
            await fn()
            logger.info("[Migrations] %s applied.", label)
        except Exception as exc:
            logger.warning("[Migrations] %s skipped or failed: %s", label, exc)
