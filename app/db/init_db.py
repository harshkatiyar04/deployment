from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base
from app.db.config import db_settings
from app.db.session import engine

from app.models import notification, signup  # noqa: F401
import app.chat.models  # noqa: F401
import app.microservices.vendor.models  # noqa: F401
import app.models.mentor  # noqa: F401
import app.models.school  # noqa: F401


async def init_db() -> None:
    """
    Bootstrap DB objects for local dev:
    - Ensure schema ZENK exists
    - Create tables (and enums) if missing
    """
    async with engine.begin() as conn:
        await conn.execute(text('CREATE SCHEMA IF NOT EXISTS "ZENK";'))
        await conn.execute(text('CREATE SCHEMA IF NOT EXISTS "audit";'))
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'))
        await conn.run_sync(Base.metadata.create_all)

        # ── Trigger Logic for Admin Audit Trail ───────────────────────────────
        function_sql = """
        CREATE OR REPLACE FUNCTION "ZENK".log_chat_ban_activity()
        RETURNS TRIGGER AS $$
        DECLARE
            admin_id_val TEXT;
        BEGIN
            admin_id_val := current_setting('zenk.current_admin_id', true);
            
            IF admin_id_val IS NULL OR admin_id_val = '' THEN
                admin_id_val := '00000000-0000-0000-0000-000000000000'; -- System/Unknown
            END IF;

            IF (TG_OP = 'INSERT') THEN
                INSERT INTO audit.admin_access_log (id, admin_id, action, target_table, target_id, changes_json, created_at)
                VALUES (uuid_generate_v4()::text, admin_id_val, 'CREATE_BAN', 'chat_bans', NEW.id::text, 
                        jsonb_build_object('circle_id', NEW.circle_id, 'user_id', NEW.user_id, 'reason', NEW.reason), 
                        now());
                RETURN NEW;
            ELSIF (TG_OP = 'DELETE') THEN
                INSERT INTO audit.admin_access_log (id, admin_id, action, target_table, target_id, changes_json, created_at)
                VALUES (uuid_generate_v4()::text, admin_id_val, 'REVOKE_BAN', 'chat_bans', OLD.id::text, 
                        jsonb_build_object('circle_id', OLD.circle_id, 'user_id', OLD.user_id), 
                        now());
                RETURN OLD;
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
        """
        
        drop_trigger_sql = 'DROP TRIGGER IF EXISTS trg_log_chat_ban_activity ON "ZENK".chat_bans;'
        
        create_trigger_sql = """
        CREATE TRIGGER trg_log_chat_ban_activity
        AFTER INSERT OR DELETE ON "ZENK".chat_bans
        FOR EACH ROW EXECUTE FUNCTION "ZENK".log_chat_ban_activity();
        """
        
        await conn.execute(text(function_sql))
        await conn.execute(text(drop_trigger_sql))
        await conn.execute(text(create_trigger_sql))

    from app.db.migrations.migration_004_add_corporate_persona import run_migration as migration_004
    from app.db.migrations.migration_007_mentor_dashboard import run_migration as migration_007
    from app.db.migrations.migration_009_school_dashboard import run_migration as migration_009
    from app.db.session import SessionLocal
    async with SessionLocal() as session:
        await migration_004(session)
    await migration_007()
    await migration_009()

