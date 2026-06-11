"""Run idempotent SQL migrations for school portal (010–013) and circle ops (014)."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def apply_all_migrations() -> None:
    from app.db.migrations.migration_008_mentor_circle_chat import run_migration as m008
    from app.db.migrations.migration_010_school_rbac_audit import run_migration as m010
    from app.db.migrations.migration_011_school_portal_members import run_migration as m011
    from app.db.migrations.migration_012_school_portal_invites import run_migration as m012
    from app.db.migrations.migration_013_school_zqa_snapshots import run_migration as m013
    from app.db.migrations.migration_014_circle_ops import run_migration as m014
    from app.db.migrations.migration_015_circle_membership_requests import run_migration as m015
    from app.db.migrations.migration_016_admin_kia import run_migration as m016
    from app.db.migrations.migration_017_zenk_admin_support import run_migration as m017
    from app.db.migrations.migration_018_zenk_admin_attachments import run_migration as m018
    from app.db.migrations.migration_019_student_family import run_migration as m019
    from app.db.migrations.migration_020_student_dashboard import run_migration as m020
    from app.db.migrations.migration_021_school_students_pk import run_migration as m021
    from app.db.migrations.migration_022_student_onboarding_v2 import run_migration as m022
    from app.db.migrations.migration_023_school_faculty_registry import run_migration as m023
    from app.db.migrations.migration_024_parent_upload_v2 import run_migration as m024
    from app.db.migrations.migration_025_circle_school_partner import run_migration as m025
    from app.db.migrations.migration_026_circle_vendor_disbursements import run_migration as m026
    from app.db.migrations.migration_027_zero_unset_budgets import run_migration as m027
    from app.db.migrations.migration_028_school_public_onboarding import run_migration as m028
    from app.db.migrations.migration_029_pseudonym_unique import run_migration as m029
    from app.db.migrations.migration_030_kyc_info_required import run_migration as m030

    for label, fn in (
        ("008", m008),
        ("010", m010),
        ("011", m011),
        ("012", m012),
        ("013", m013),
        ("014", m014),
        ("015", m015),
        ("016", m016),
        ("017", m017),
        ("018", m018),
        ("019", m019),
        ("020", m020),
        ("021", m021),
        ("022", m022),
        ("023", m023),
        ("024", m024),
        ("025", m025),
        ("026", m026),
        ("027", m027),
        ("028", m028),
        ("029", m029),
        ("030", m030),
    ):
        try:
            await fn()
            logger.info("[Migrations] %s applied.", label)
        except Exception as exc:
            logger.warning("[Migrations] %s skipped or failed: %s", label, exc)
