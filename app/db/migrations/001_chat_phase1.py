"""
Phase 1 Chat Migration — run ONCE to create all chat tables.

FIX: asyncpg does not allow multiple SQL statements in a single execute() call.
Each statement (CREATE TABLE, CREATE INDEX, DO block) is a separate execute call.

Usage:
    cd zenkimpact_BE
    python -m app.db.migrations.001_chat_phase1

Idempotent — IF NOT EXISTS on every statement.
"""
import asyncio

from sqlalchemy import text

from app.db.session import engine


async def run_migration() -> None:
    print("=== Phase 1 Chat Migration ===")
    async with engine.begin() as conn:

        # ── channel_type_enum ──────────────────────────────────────────────
        print("Creating channel_type_enum...")
        await conn.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_type t
                    JOIN pg_namespace n ON n.oid = t.typnamespace
                    WHERE t.typname = 'channel_type_enum'
                      AND n.nspname = 'ZENK'
                ) THEN
                    CREATE TYPE "ZENK".channel_type_enum AS ENUM ('persistent', 'stage');
                END IF;
            END
            $$;
        """))

        # ── sponsor_circles ───────────────────────────────────────────────
        print("Creating sponsor_circles...")
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "ZENK".sponsor_circles (
                id          UUID PRIMARY KEY,
                name        VARCHAR(255) NOT NULL,
                description TEXT,
                status      VARCHAR(50) NOT NULL DEFAULT 'active',
                created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """))

        # ── circle_members ────────────────────────────────────────────────
        print("Creating circle_members...")
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "ZENK".circle_members (
                id         UUID PRIMARY KEY,
                circle_id  UUID NOT NULL REFERENCES "ZENK".sponsor_circles(id) ON DELETE CASCADE,
                user_id    UUID NOT NULL REFERENCES "ZENK".signup_requests(id) ON DELETE CASCADE,
                role       VARCHAR(50) NOT NULL DEFAULT 'sponsor',
                joined_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_circle_members_circle_id
            ON "ZENK".circle_members(circle_id)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_circle_members_user_id
            ON "ZENK".circle_members(user_id)
        """))

        # ── enrollments ───────────────────────────────────────────────────
        print("Creating enrollments...")
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "ZENK".enrollments (
                id          UUID PRIMARY KEY,
                circle_id   UUID NOT NULL REFERENCES "ZENK".sponsor_circles(id) ON DELETE CASCADE,
                user_id     UUID NOT NULL REFERENCES "ZENK".signup_requests(id) ON DELETE CASCADE,
                enrolled_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                is_active   BOOLEAN NOT NULL DEFAULT TRUE
            )
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_enrollments_circle_id
            ON "ZENK".enrollments(circle_id)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_enrollments_user_id
            ON "ZENK".enrollments(user_id)
        """))

        # ── gamified_personas ─────────────────────────────────────────────
        print("Creating gamified_personas...")
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "ZENK".gamified_personas (
                id         UUID PRIMARY KEY,
                user_id    UUID NOT NULL UNIQUE REFERENCES "ZENK".signup_requests(id) ON DELETE CASCADE,
                nickname   VARCHAR(100) NOT NULL,
                avatar_key VARCHAR(100) NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_gamified_personas_user_id
            ON "ZENK".gamified_personas(user_id)
        """))

        # ── chat_channels ─────────────────────────────────────────────────
        print("Creating chat_channels...")
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "ZENK".chat_channels (
                id           UUID PRIMARY KEY,
                circle_id    UUID NOT NULL REFERENCES "ZENK".sponsor_circles(id) ON DELETE CASCADE,
                name         VARCHAR(100) NOT NULL,
                channel_type "ZENK".channel_type_enum NOT NULL DEFAULT 'persistent',
                created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_chat_channels_circle_id
            ON "ZENK".chat_channels(circle_id)
        """))

        # ── chat_messages (append-only) ───────────────────────────────────
        print("Creating chat_messages (append-only)...")
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "ZENK".chat_messages (
                id                  UUID PRIMARY KEY,
                channel_id          UUID NOT NULL REFERENCES "ZENK".chat_channels(id) ON DELETE CASCADE,
                gamified_persona_id UUID NOT NULL REFERENCES "ZENK".gamified_personas(id) ON DELETE CASCADE,
                content_text        TEXT,
                media_url           VARCHAR(1000),
                shield_action       VARCHAR(20) NOT NULL DEFAULT 'allow',
                shield_reason       VARCHAR(100),
                hidden_at           TIMESTAMPTZ,
                created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """))
        # NOTE: No updated_at, no deleted_at — this table is append-only.
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_chat_messages_channel_id
            ON "ZENK".chat_messages(channel_id)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_chat_messages_gamified_persona_id
            ON "ZENK".chat_messages(gamified_persona_id)
        """))

        # ── sos_reports ───────────────────────────────────────────────────
        print("Creating sos_reports...")
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "ZENK".sos_reports (
                id                   UUID PRIMARY KEY,
                message_id           UUID NOT NULL REFERENCES "ZENK".chat_messages(id) ON DELETE CASCADE,
                reporter_persona_id  UUID NOT NULL REFERENCES "ZENK".gamified_personas(id) ON DELETE CASCADE,
                hidden_at            TIMESTAMPTZ,
                admin_notified_at    TIMESTAMPTZ,
                resolved_at          TIMESTAMPTZ,
                notes                TEXT,
                created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_sos_reports_message_id
            ON "ZENK".sos_reports(message_id)
        """))

    print("=== Phase 1 Migration Complete ===")


if __name__ == "__main__":
    asyncio.run(run_migration())
