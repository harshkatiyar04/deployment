"""Additional legal document types (privacy, parent/member, student declaration)."""

import asyncio
import hashlib
import logging
from uuid import uuid4

from sqlalchemy import text

from app.db.session import engine

logger = logging.getLogger(__name__)

LEGAL_ENTITY = "Zenk Impact India Private Limited"
VERSION = "2026.06.15"


def _sha(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


DOCUMENTS = [
    {
        "doc_type": "privacy_policy",
        "version": VERSION,
        "title": "ZENK Privacy Policy",
        "pdf_path": "/static/legal/zenk-privacy-policy-2026.06.15.pdf",
        "sha": "ed2657ee136ae7a566ff5842e1f33ba9f5376baa726769966690e28c1e3f2bfa",
        "effective_date": "2026-06-15",
    },
    {
        "doc_type": "parent_member_terms",
        "version": VERSION,
        "title": "ZenK Parent & Circle Member Terms",
        "pdf_path": "/static/legal/zenk-parent-member-terms-2026.06.15.pdf",
        "sha": _sha("zenk-parent-member-terms-v2026.06.15"),
        "effective_date": "2026-06-15",
    },
    {
        "doc_type": "student_declaration",
        "version": VERSION,
        "title": "ZenK Student Participation Declaration",
        "pdf_path": "/static/legal/zenk-student-declaration-2026.06.15.pdf",
        "sha": _sha("zenk-student-declaration-v2026.06.15"),
        "effective_date": "2026-06-15",
    },
]


async def run_migration():
    logger.info("=== Migration 032: extended legal documents ===")
    async with engine.begin() as conn:
        for doc in DOCUMENTS:
            doc_id = str(uuid4())
            await conn.execute(
                text(
                    """
                    UPDATE "ZENK"."legal_documents"
                    SET is_active = FALSE
                    WHERE doc_type = :doc_type AND version <> :version
                    """
                ),
                {"doc_type": doc["doc_type"], "version": doc["version"]},
            )
            await conn.execute(
                text(
                    """
                    INSERT INTO "ZENK"."legal_documents" (
                        id, doc_type, version, title, legal_entity,
                        effective_date, pdf_path, content_sha256, is_active, created_at
                    )
                    VALUES (
                        :id, :doc_type, :version, :title, :legal_entity,
                        DATE '2026-06-15', :pdf_path, :sha, TRUE, NOW()
                    )
                    ON CONFLICT (doc_type, version) DO UPDATE SET
                        title = EXCLUDED.title,
                        legal_entity = EXCLUDED.legal_entity,
                        effective_date = EXCLUDED.effective_date,
                        pdf_path = EXCLUDED.pdf_path,
                        content_sha256 = EXCLUDED.content_sha256,
                        is_active = TRUE
                    """
                ),
                {
                    "id": doc_id,
                    "doc_type": doc["doc_type"],
                    "version": doc["version"],
                    "title": doc["title"],
                    "legal_entity": LEGAL_ENTITY,
                    "effective_date": "2026-06-15",
                    "pdf_path": doc["pdf_path"],
                    "sha": doc["sha"],
                },
            )
    logger.info("Migration 032 complete.")


if __name__ == "__main__":
    asyncio.run(run_migration())
