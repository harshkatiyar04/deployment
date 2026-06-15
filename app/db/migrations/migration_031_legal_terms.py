"""Legal documents + acceptance audit log for signup T&C."""

import asyncio
import logging
from uuid import uuid4

from sqlalchemy import text

from app.db.session import engine

logger = logging.getLogger(__name__)

PLATFORM_VERSION = "2026.06.15"
PLATFORM_SHA256 = "cc3383ec1e2d5c7b965dc09c77cc08926fda14b601601807cea052d4f8bf9707"
PLATFORM_PDF = "/static/legal/zenk-platform-terms-2026.06.15.pdf"
LEGAL_ENTITY = "Zenk Impact India Private Limited"


async def run_migration():
    logger.info("=== Migration 031: legal documents + acceptances ===")
    doc_id = str(uuid4())

    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS "ZENK"."legal_documents" (
                    id              UUID         PRIMARY KEY,
                    doc_type        VARCHAR(40)  NOT NULL,
                    version         VARCHAR(32)  NOT NULL,
                    title           VARCHAR(300) NOT NULL,
                    legal_entity    VARCHAR(300) NOT NULL,
                    effective_date  DATE         NOT NULL,
                    pdf_path        VARCHAR(500) NOT NULL,
                    content_sha256  CHAR(64)     NOT NULL,
                    is_active       BOOLEAN      NOT NULL DEFAULT FALSE,
                    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
                )
                """
            )
        )
        await conn.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_legal_documents_type_version
                ON "ZENK"."legal_documents" (doc_type, version)
                """
            )
        )
        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS "ZENK"."legal_acceptances" (
                    id                  UUID         PRIMARY KEY,
                    signup_request_id   UUID         REFERENCES "ZENK"."signup_requests"(id) ON DELETE SET NULL,
                    document_id         UUID         NOT NULL REFERENCES "ZENK"."legal_documents"(id) ON DELETE RESTRICT,
                    doc_type            VARCHAR(40)  NOT NULL,
                    document_version    VARCHAR(32)  NOT NULL,
                    document_sha256     CHAR(64)     NOT NULL,
                    legal_entity        VARCHAR(300) NOT NULL,
                    email               VARCHAR(320) NOT NULL,
                    full_name           VARCHAR(200) NOT NULL,
                    persona             VARCHAR(50)  NOT NULL,
                    acceptance_method   VARCHAR(40)  NOT NULL DEFAULT 'signup_checkbox',
                    acceptance_channel  VARCHAR(40)  NOT NULL DEFAULT 'web_signup',
                    acceptance_role     VARCHAR(40)  NOT NULL DEFAULT 'self',
                    ip_address          VARCHAR(64),
                    forwarded_ip        VARCHAR(64),
                    user_agent          TEXT,
                    accept_locale       VARCHAR(20),
                    accepted_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
                    metadata_json       JSONB
                )
                """
            )
        )
        await conn.execute(
            text(
                'CREATE INDEX IF NOT EXISTS idx_legal_accept_signup '
                'ON "ZENK"."legal_acceptances"(signup_request_id, accepted_at DESC)'
            )
        )
        await conn.execute(
            text(
                'CREATE INDEX IF NOT EXISTS idx_legal_accept_email '
                'ON "ZENK"."legal_acceptances"(email, accepted_at DESC)'
            )
        )
        await conn.execute(
            text(
                'CREATE INDEX IF NOT EXISTS idx_legal_docs_active '
                'ON "ZENK"."legal_documents"(doc_type, is_active)'
            )
        )

        await conn.execute(
            text(
                """
                UPDATE "ZENK"."legal_documents"
                SET is_active = FALSE
                WHERE doc_type = 'platform_terms' AND version <> :version
                """
            ),
            {"version": PLATFORM_VERSION},
        )

        await conn.execute(
            text(
                """
                INSERT INTO "ZENK"."legal_documents" (
                    id, doc_type, version, title, legal_entity,
                    effective_date, pdf_path, content_sha256, is_active, created_at
                )
                VALUES (
                    :id, 'platform_terms', :version,
                    'ZenK Platform Terms & Conditions',
                    :legal_entity,
                    DATE '2026-06-15',
                    :pdf_path,
                    :sha,
                    TRUE,
                    NOW()
                )
                ON CONFLICT (doc_type, version) DO UPDATE SET
                    title = EXCLUDED.title,
                    legal_entity = EXCLUDED.legal_entity,
                    effective_date = EXCLUDED.effective_date,
                    pdf_path = EXCLUDED.pdf_path,
                    content_sha256 = EXCLUDED.content_sha256,
                    is_active = TRUE,
                    created_at = COALESCE("ZENK"."legal_documents".created_at, NOW())
                """
            ),
            {
                "id": doc_id,
                "version": PLATFORM_VERSION,
                "legal_entity": LEGAL_ENTITY,
                "pdf_path": PLATFORM_PDF,
                "sha": PLATFORM_SHA256,
            },
        )

    logger.info("Migration 031 complete.")


if __name__ == "__main__":
    asyncio.run(run_migration())
