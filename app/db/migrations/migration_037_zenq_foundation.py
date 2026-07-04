"""Migration 037: ZenQ engine foundation tables (Phase 0 — admin observatory only)."""

from __future__ import annotations

import json
import logging

from sqlalchemy import text

from app.algorithms.zenq.constants import DEFAULT_WEIGHTS
from app.db.session import engine

logger = logging.getLogger(__name__)


async def run_migration() -> None:
    logger.info("=== Migration 037: ZenQ foundation tables ===")

    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "ZENK"."zenq_events" (
                id                UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
                event_type        VARCHAR(64)  NOT NULL,
                circle_id         UUID         REFERENCES "ZENK"."sponsor_circles"(id) ON DELETE CASCADE,
                actor_id          UUID,
                idempotency_key   VARCHAR(128),
                payload_json      JSONB        NOT NULL DEFAULT '{}'::jsonb,
                processed_at      TIMESTAMPTZ,
                created_at        TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
                UNIQUE (idempotency_key)
            )
        """))
        await conn.execute(text(
            'CREATE INDEX IF NOT EXISTS idx_zenq_events_circle_created '
            'ON "ZENK"."zenq_events"(circle_id, created_at DESC)'
        ))

        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "ZENK"."zenq_sponsor_metrics" (
                id                          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
                circle_id                   UUID         NOT NULL REFERENCES "ZENK"."sponsor_circles"(id) ON DELETE CASCADE,
                user_id                     UUID         NOT NULL,
                window_key                  VARCHAR(16)  NOT NULL DEFAULT '30d',
                session_mins                FLOAT        NOT NULL DEFAULT 0.0,
                message_count               INTEGER      NOT NULL DEFAULT 0,
                substantive_message_count   INTEGER      NOT NULL DEFAULT 0,
                active_inspire              INTEGER      NOT NULL DEFAULT 0,
                passive_inspire             INTEGER      NOT NULL DEFAULT 0,
                avg_ras                     FLOAT        NOT NULL DEFAULT 1.0,
                streak_days                 INTEGER      NOT NULL DEFAULT 0,
                target_status               VARCHAR(16)  NOT NULL DEFAULT 'none',
                effort_weight               FLOAT        NOT NULL DEFAULT 0.0,
                commitment_factor           FLOAT        NOT NULL DEFAULT 1.0,
                spark_active                BOOLEAN      NOT NULL DEFAULT FALSE,
                metrics_json                JSONB        NOT NULL DEFAULT '{}'::jsonb,
                updated_at                  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
                UNIQUE (circle_id, user_id, window_key)
            )
        """))

        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "ZENK"."zenq_student_context" (
                id                  UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
                student_id          UUID         NOT NULL REFERENCES "ZENK"."school_students"(id) ON DELETE CASCADE,
                circle_id           UUID         REFERENCES "ZENK"."sponsor_circles"(id) ON DELETE SET NULL,
                zqa_composite       FLOAT        NOT NULL DEFAULT 0.0,
                zqa_band            VARCHAR(50)  NOT NULL DEFAULT '1 - Beginning',
                baseline_zqa        FLOAT,
                spd                 FLOAT        NOT NULL DEFAULT 1.0,
                need_band           VARCHAR(20)  NOT NULL DEFAULT 'developing',
                attendance_30d      FLOAT        NOT NULL DEFAULT 0.0,
                spark_active        BOOLEAN      NOT NULL DEFAULT FALSE,
                context_json        JSONB        NOT NULL DEFAULT '{}'::jsonb,
                updated_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
                UNIQUE (student_id)
            )
        """))
        await conn.execute(text(
            'CREATE INDEX IF NOT EXISTS idx_zenq_student_context_circle '
            'ON "ZENK"."zenq_student_context"(circle_id)'
        ))

        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "ZENK"."zenq_sponsor_scores" (
                id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
                circle_id       UUID         NOT NULL REFERENCES "ZENK"."sponsor_circles"(id) ON DELETE CASCADE,
                user_id         UUID         NOT NULL,
                zeq             FLOAT        NOT NULL DEFAULT 0.0,
                components_json JSONB        NOT NULL DEFAULT '{}'::jsonb,
                updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
                UNIQUE (circle_id, user_id)
            )
        """))

        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "ZENK"."zenq_circle_scores" (
                circle_id         UUID         PRIMARY KEY REFERENCES "ZENK"."sponsor_circles"(id) ON DELETE CASCADE,
                circle_name       VARCHAR(255),
                zeq_avg           FLOAT        NOT NULL DEFAULT 0.0,
                zcq               FLOAT        NOT NULL DEFAULT 0.0,
                spd_avg           FLOAT        NOT NULL DEFAULT 1.0,
                ziq               FLOAT        NOT NULL DEFAULT 0.0,
                ziq_per_member    FLOAT        NOT NULL DEFAULT 0.0,
                sponsor_count     INTEGER      NOT NULL DEFAULT 0,
                student_count     INTEGER      NOT NULL DEFAULT 0,
                algorithm_version VARCHAR(32)  NOT NULL DEFAULT '1.0.0-phase0',
                summary_json      JSONB        NOT NULL DEFAULT '{}'::jsonb,
                updated_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW()
            )
        """))

        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "ZENK"."zenq_computation_snapshots" (
                id                UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
                scope_type        VARCHAR(32)  NOT NULL,
                scope_id          UUID         NOT NULL,
                circle_id         UUID         REFERENCES "ZENK"."sponsor_circles"(id) ON DELETE CASCADE,
                algorithm_version VARCHAR(32)  NOT NULL,
                trigger_source    VARCHAR(64)  NOT NULL DEFAULT 'materializer',
                inputs_json       JSONB        NOT NULL DEFAULT '{}'::jsonb,
                outputs_json      JSONB        NOT NULL DEFAULT '{}'::jsonb,
                created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW()
            )
        """))
        await conn.execute(text(
            'CREATE INDEX IF NOT EXISTS idx_zenq_snapshots_circle_created '
            'ON "ZENK"."zenq_computation_snapshots"(circle_id, created_at DESC)'
        ))

        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "ZENK"."zenq_weight_config" (
                id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
                status          VARCHAR(20)  NOT NULL DEFAULT 'active',
                weights_json    JSONB        NOT NULL DEFAULT '{}'::jsonb,
                proposed_by     VARCHAR(64)  NOT NULL DEFAULT 'system',
                approved_by     VARCHAR(128),
                notes           TEXT,
                created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
                approved_at     TIMESTAMPTZ
            )
        """))

        # Seed active default weights if none exist.
        # Use a bind param — literal JSON like :0.25 is parsed as SQLAlchemy bind tokens.
        await conn.execute(
            text("""
            INSERT INTO "ZENK"."zenq_weight_config"
                (id, status, weights_json, proposed_by, notes, created_at)
            SELECT gen_random_uuid(),
                   'active',
                   CAST(:weights_json AS jsonb),
                   'system',
                   'Default PDF weights (Phase 0 seed)',
                   NOW()
            WHERE NOT EXISTS (
                SELECT 1 FROM "ZENK"."zenq_weight_config" WHERE status = 'active'
            )
        """),
            {"weights_json": json.dumps(DEFAULT_WEIGHTS)},
        )

        # Repair tables created earlier by SQLAlchemy create_all (Python-only defaults).
        for table in (
            "zenq_events",
            "zenq_sponsor_metrics",
            "zenq_student_context",
            "zenq_sponsor_scores",
            "zenq_computation_snapshots",
            "zenq_weight_config",
        ):
            await conn.execute(text(f"""
                ALTER TABLE "ZENK"."{table}"
                ALTER COLUMN id SET DEFAULT gen_random_uuid()
            """))
        await conn.execute(text("""
            ALTER TABLE "ZENK"."zenq_events"
            ALTER COLUMN created_at SET DEFAULT NOW()
        """))
        await conn.execute(text("""
            ALTER TABLE "ZENK"."zenq_sponsor_metrics"
            ALTER COLUMN updated_at SET DEFAULT NOW()
        """))
        await conn.execute(text("""
            ALTER TABLE "ZENK"."zenq_student_context"
            ALTER COLUMN updated_at SET DEFAULT NOW()
        """))
        await conn.execute(text("""
            ALTER TABLE "ZENK"."zenq_sponsor_scores"
            ALTER COLUMN updated_at SET DEFAULT NOW()
        """))
        await conn.execute(text("""
            ALTER TABLE "ZENK"."zenq_circle_scores"
            ALTER COLUMN updated_at SET DEFAULT NOW()
        """))
        await conn.execute(text("""
            ALTER TABLE "ZENK"."zenq_computation_snapshots"
            ALTER COLUMN created_at SET DEFAULT NOW()
        """))
        await conn.execute(text("""
            ALTER TABLE "ZENK"."zenq_weight_config"
            ALTER COLUMN created_at SET DEFAULT NOW()
        """))

    logger.info("Migration 037 complete.")
