"""Migration 051: ZenQ v2 cumulative ledger tables (Tech Guide §2)."""

from __future__ import annotations

import json
import logging

from sqlalchemy import text

from app.algorithms.zenq_v2.params import ALGORITHM_VERSION, LAUNCH_PARAMS
from app.db.session import engine

logger = logging.getLogger(__name__)


async def run_migration() -> None:
    logger.info("=== Migration 051: ZenQ v2 ledger ===")
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "ZENK"."zenq_v2_weights" (
                version_id       VARCHAR(64) PRIMARY KEY,
                effective_from   DATE,
                params_json      JSONB NOT NULL DEFAULT '{}'::jsonb,
                approved_by      VARCHAR(128),
                proposal_id      UUID,
                created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """))

        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "ZENK"."zenq_v2_event_ledger" (
                id              BIGSERIAL PRIMARY KEY,
                ts              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                event_code      VARCHAR(64) NOT NULL,
                actor_id        UUID,
                circle_id       UUID REFERENCES "ZENK"."sponsor_circles"(id) ON DELETE CASCADE,
                student_id      UUID,
                quantity        FLOAT NOT NULL DEFAULT 1,
                minutes         FLOAT,
                quality_json    JSONB NOT NULL DEFAULT '{}'::jsonb,
                partner_flag    VARCHAR(16),
                session_id      UUID,
                verified_by     VARCHAR(64),
                reversal_of     BIGINT,
                created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """))
        await conn.execute(text(
            'CREATE INDEX IF NOT EXISTS idx_zenq_v2_ledger_circle_ts '
            'ON "ZENK"."zenq_v2_event_ledger"(circle_id, ts DESC)'
        ))

        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "ZENK"."zenq_v2_event_points" (
                id                  BIGSERIAL PRIMARY KEY,
                event_id            BIGINT NOT NULL REFERENCES "ZENK"."zenq_v2_event_ledger"(id) ON DELETE CASCADE,
                weights_version_id  VARCHAR(64) NOT NULL,
                class               VARCHAR(32) NOT NULL,
                ip_base             FLOAT NOT NULL DEFAULT 0,
                bracket_weight      FLOAT NOT NULL DEFAULT 1,
                streak_mult         FLOAT NOT NULL DEFAULT 1,
                ip_final            FLOAT NOT NULL DEFAULT 0,
                scored_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                superseded_at       TIMESTAMPTZ
            )
        """))

        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "ZENK"."zenq_v2_member_day" (
                member_id       UUID NOT NULL,
                circle_id       UUID NOT NULL,
                day             DATE NOT NULL,
                ip_presence     FLOAT NOT NULL DEFAULT 0,
                ip_learning     FLOAT NOT NULL DEFAULT 0,
                ip_chat         FLOAT NOT NULL DEFAULT 0,
                ip_kia          FLOAT NOT NULL DEFAULT 0,
                ip_funding      FLOAT NOT NULL DEFAULT 0,
                ip_growth       FLOAT NOT NULL DEFAULT 0,
                ip_spark        FLOAT NOT NULL DEFAULT 0,
                active          BOOLEAN NOT NULL DEFAULT FALSE,
                PRIMARY KEY (member_id, circle_id, day)
            )
        """))

        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "ZENK"."zenq_v2_member_month" (
                member_id       UUID NOT NULL,
                circle_id       UUID NOT NULL,
                month           DATE NOT NULL,
                ip_presence     FLOAT NOT NULL DEFAULT 0,
                ip_learning     FLOAT NOT NULL DEFAULT 0,
                ip_chat         FLOAT NOT NULL DEFAULT 0,
                ip_kia          FLOAT NOT NULL DEFAULT 0,
                ip_funding      FLOAT NOT NULL DEFAULT 0,
                ip_growth       FLOAT NOT NULL DEFAULT 0,
                ip_spark        FLOAT NOT NULL DEFAULT 0,
                ip_total        FLOAT NOT NULL DEFAULT 0,
                streak_weeks_end INTEGER NOT NULL DEFAULT 0,
                fade_factor     FLOAT NOT NULL DEFAULT 1,
                pcs_cumulative  FLOAT NOT NULL DEFAULT 0,
                closed_at       TIMESTAMPTZ,
                PRIMARY KEY (member_id, circle_id, month)
            )
        """))

        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "ZENK"."zenq_v2_factor_weights_month" (
                month               DATE PRIMARY KEY,
                presence            FLOAT NOT NULL,
                learning            FLOAT NOT NULL,
                chat                FLOAT NOT NULL,
                kia                 FLOAT NOT NULL,
                funding             FLOAT NOT NULL,
                growth              FLOAT NOT NULL,
                student             FLOAT NOT NULL,
                neutrality_scale    FLOAT NOT NULL DEFAULT 1,
                source              VARCHAR(32) NOT NULL DEFAULT 'BASELINE',
                proposal_id         UUID,
                approved_by         VARCHAR(128),
                closed_at           TIMESTAMPTZ
            )
        """))

        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "ZENK"."zenq_v2_circle_month" (
                circle_id           UUID NOT NULL,
                month               DATE NOT NULL,
                weights_version_id  VARCHAR(64),
                member_ip           FLOAT NOT NULL DEFAULT 0,
                partner_ip_raw      FLOAT NOT NULL DEFAULT 0,
                partner_ip_capped   FLOAT NOT NULL DEFAULT 0,
                growth_ip           FLOAT NOT NULL DEFAULT 0,
                spark_ip            FLOAT NOT NULL DEFAULT 0,
                k                   FLOAT NOT NULL DEFAULT 1,
                g                   FLOAT NOT NULL DEFAULT 1,
                growth_ratio        FLOAT,
                phase               VARCHAR(16) NOT NULL DEFAULT 'EFFORT',
                in_stretch          BOOLEAN NOT NULL DEFAULT FALSE,
                earnings            FLOAT NOT NULL DEFAULT 0,
                lifetime_zenq       FLOAT NOT NULL DEFAULT 0,
                season_zenq         FLOAT NOT NULL DEFAULT 0,
                return_pct          FLOAT,
                contribution_cum    FLOAT NOT NULL DEFAULT 0,
                yield_per_lakh      FLOAT,
                epm                 FLOAT,
                milestone           VARCHAR(32),
                sgi                 FLOAT,
                sgi_band            VARCHAR(32),
                closed_at           TIMESTAMPTZ,
                PRIMARY KEY (circle_id, month)
            )
        """))

        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "ZENK"."zenq_v2_agent_run" (
                id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                month               DATE NOT NULL,
                signals_json        JSONB NOT NULL DEFAULT '{}'::jsonb,
                rules_fired_json    JSONB NOT NULL DEFAULT '[]'::jsonb,
                proposed_json       JSONB NOT NULL DEFAULT '{}'::jsonb,
                reasoning_text      TEXT,
                status              VARCHAR(32) NOT NULL DEFAULT 'LOGGED',
                reviewed_by         VARCHAR(128),
                reviewed_at         TIMESTAMPTZ,
                created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """))

        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "ZENK"."zenq_v2_circle_profile" (
                circle_id       UUID PRIMARY KEY REFERENCES "ZENK"."sponsor_circles"(id) ON DELETE CASCADE,
                need_band       VARCHAR(32) NOT NULL DEFAULT 'Developing',
                k               FLOAT NOT NULL DEFAULT 1.0,
                activated_on    DATE,
                bracket         CHAR(1),
                updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """))

        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "ZENK"."zenq_v2_assessments" (
                id              BIGSERIAL PRIMARY KEY,
                circle_id       UUID NOT NULL REFERENCES "ZENK"."sponsor_circles"(id) ON DELETE CASCADE,
                student_id      UUID,
                assessed_on     DATE NOT NULL,
                language        FLOAT,
                maths           FLOAT,
                history         FLOAT,
                composite       FLOAT NOT NULL,
                is_baseline     BOOLEAN NOT NULL DEFAULT FALSE,
                source          VARCHAR(64) NOT NULL DEFAULT 'holistic_v2_equal_split',
                created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """))
        await conn.execute(text(
            'CREATE INDEX IF NOT EXISTS idx_zenq_v2_assessments_circle '
            'ON "ZENK"."zenq_v2_assessments"(circle_id, assessed_on)'
        ))

        # Seed launch weights version if missing
        params = json.dumps(LAUNCH_PARAMS)
        await conn.execute(
            text("""
                INSERT INTO "ZENK"."zenq_v2_weights"(version_id, effective_from, params_json, approved_by)
                VALUES (:vid, CURRENT_DATE, CAST(:pj AS jsonb), 'system-launch')
                ON CONFLICT (version_id) DO NOTHING
            """),
            {"vid": ALGORITHM_VERSION, "pj": params},
        )

    logger.info("Migration 051 complete")
