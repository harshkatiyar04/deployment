-- Migration 030: KYC "info_required" status (additional documents flow)
-- Run on Neon / production after restore from dump dated before 2026-06.
--
-- NOTE: KYC reupload does NOT use a new table. Applicants upload into the
-- existing ZENK.kyc_documents table; signup_requests.kyc_status becomes
-- info_required until they resubmit, then returns to pending.
--
-- Safe to run multiple times (IF NOT EXISTS).

BEGIN;

-- 1) New KYC status value (required for admin "Additional info required" action)
ALTER TYPE "ZENK".kyc_status_enum
    ADD VALUE IF NOT EXISTS 'info_required';

-- 2) Reference: kyc_documents already exists in older dumps — create only if missing
CREATE TABLE IF NOT EXISTS "ZENK".kyc_documents (
    id              UUID PRIMARY KEY,
    signup_id       UUID NOT NULL
                        REFERENCES "ZENK".signup_requests(id) ON DELETE CASCADE,
    original_filename VARCHAR(512) NOT NULL,
    stored_filename VARCHAR(512) NOT NULL,
    stored_path     TEXT NOT NULL,
    content_type    VARCHAR(128),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc')
);

CREATE INDEX IF NOT EXISTS ix_kyc_documents_signup_id
    ON "ZENK".kyc_documents (signup_id);

COMMIT;
