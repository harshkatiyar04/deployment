import asyncio
import logging
from app.db.session import engine
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_migration():
    """
    Creates the Phase 3 schema:
    1. 'audit' schema
    2. 'admin_access_log' table
    3. PostgreSQL trigger function for audit logging
    4. 'chat_bans' table in 'ZENK' schema
    """
    async with engine.begin() as conn:
        logger.info("=== Phase 3 Chat Migration ===")

        # 1. Ensure audit schema exists
        logger.info("Creating audit schema...")
        await conn.execute(text('CREATE SCHEMA IF NOT EXISTS "audit";'))

        # 2. Extract into separate statements to avoid asyncpg multiple commands error
        logger.info("Creating admin_access_log...")
        await conn.execute(text('''
            CREATE TABLE IF NOT EXISTS "audit"."admin_access_log" (
                "id" VARCHAR(36) PRIMARY KEY,
                "admin_id" VARCHAR(36) NOT NULL,
                "action" VARCHAR(100) NOT NULL,
                "target_table" VARCHAR(100) NOT NULL,
                "target_id" VARCHAR(36) NOT NULL,
                "changes_json" JSONB,
                "created_at" TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now()) NOT NULL
            );
        '''))

        await conn.execute(text('CREATE INDEX IF NOT EXISTS ix_admin_access_log_admin_id ON "audit"."admin_access_log" ("admin_id");'))

        # 3. Create Audit Trigger Function
        logger.info("Creating audit trigger function...")
        await conn.execute(text('''
            CREATE OR REPLACE FUNCTION audit.log_admin_action()
            RETURNS TRIGGER AS $$
            BEGIN
                INSERT INTO audit.admin_access_log (
                    id, admin_id, action, target_table, target_id, changes_json, created_at
                ) VALUES (
                    gen_random_uuid()::varchar,
                    current_setting('zenk.current_admin_id', true), -- Uses session config
                    TG_OP,
                    TG_TABLE_NAME,
                    COALESCE(NEW.id, OLD.id),
                    row_to_json(NEW)::jsonb,
                    timezone('utc', now())
                );
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        '''))

        # 4. Create chat_bans table
        logger.info("Creating chat_bans...")
        await conn.execute(text('''
            CREATE TABLE IF NOT EXISTS "ZENK"."chat_bans" (
                "id" UUID PRIMARY KEY,
                "circle_id" UUID NOT NULL REFERENCES "ZENK"."sponsor_circles"("id") ON DELETE CASCADE,
                "user_id" UUID NOT NULL REFERENCES "ZENK"."signup_requests"("id") ON DELETE CASCADE,
                "banned_by_admin_id" UUID REFERENCES "ZENK"."signup_requests"("id") ON DELETE SET NULL,
                "reason" TEXT NOT NULL,
                "created_at" TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now()) NOT NULL
            );
        '''))

        await conn.execute(text('CREATE INDEX IF NOT EXISTS ix_chat_bans_circle_id ON "ZENK"."chat_bans" ("circle_id");'))
        await conn.execute(text('CREATE INDEX IF NOT EXISTS ix_chat_bans_user_id ON "ZENK"."chat_bans" ("user_id");'))
        
        # Attach the trigger to chat_bans table to demonstrate Audit Vault
        logger.info("Attaching audit trigger to chat_bans...")
        await conn.execute(text('DROP TRIGGER IF EXISTS trg_audit_chat_bans ON "ZENK"."chat_bans";'))
        await conn.execute(text('''
            CREATE TRIGGER trg_audit_chat_bans
            AFTER INSERT OR UPDATE OR DELETE ON "ZENK"."chat_bans"
            FOR EACH ROW EXECUTE FUNCTION audit.log_admin_action();
        '''))

        logger.info("Phase 3 migration complete!")

if __name__ == "__main__":
    asyncio.run(run_migration())
