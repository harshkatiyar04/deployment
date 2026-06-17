"""Point privacy_policy legal document at the official ZENK Privacy Policy PDF."""

import asyncio
import logging

from sqlalchemy import text

from app.db.session import engine

logger = logging.getLogger(__name__)

PRIVACY_VERSION = "2026.06.15"
PRIVACY_PDF = "/static/legal/zenk-privacy-policy-2026.06.15.pdf"
PRIVACY_SHA256 = "ed2657ee136ae7a566ff5842e1f33ba9f5376baa726769966690e28c1e3f2bfa"


async def run_migration():
    logger.info("=== Migration 034: privacy policy PDF ===")
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                UPDATE "ZENK"."legal_documents"
                SET pdf_path = :pdf_path,
                    content_sha256 = :sha,
                    title = 'ZENK Privacy Policy',
                    is_active = TRUE
                WHERE doc_type = 'privacy_policy' AND version = :version
                """
            ),
            {
                "pdf_path": PRIVACY_PDF,
                "sha": PRIVACY_SHA256,
                "version": PRIVACY_VERSION,
            },
        )
    logger.info("Migration 034 complete.")


if __name__ == "__main__":
    asyncio.run(run_migration())
