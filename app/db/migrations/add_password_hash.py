"""
Migration script to add password_hash column to signup_requests table.

Run this script once to add the password_hash column to existing tables.
"""
import asyncio
from sqlalchemy import text

from app.db.session import engine


async def add_password_hash_column():
    """Add password_hash column to signup_requests table if it doesn't exist."""
    async with engine.begin() as conn:
        # Check if column exists
        check_query = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'ZENK' 
            AND table_name = 'signup_requests' 
            AND column_name = 'password_hash'
        """)
        result = await conn.execute(check_query)
        column_exists = result.scalar_one_or_none() is not None

        if not column_exists:
            print("Adding password_hash column to signup_requests table...")
            
            # Add column as nullable first
            await conn.execute(text("""
                ALTER TABLE "ZENK".signup_requests 
                ADD COLUMN password_hash VARCHAR(255)
            """))
            
            # Set a placeholder hash for existing rows
            # This is a bcrypt hash of "TEMP_PASSWORD_RESET_REQUIRED"
            placeholder_hash = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqBWVHxkd0"
            await conn.execute(
                text("""
                    UPDATE "ZENK".signup_requests 
                    SET password_hash = :placeholder 
                    WHERE password_hash IS NULL
                """),
                {"placeholder": placeholder_hash}
            )
            
            # Now make it NOT NULL
            await conn.execute(text("""
                ALTER TABLE "ZENK".signup_requests 
                ALTER COLUMN password_hash SET NOT NULL
            """))
            
            print("✓ password_hash column added successfully!")
            print("⚠️  Note: Existing signups have a temporary password hash.")
            print("   They will need to reset their password or re-signup.")
        else:
            print("✓ password_hash column already exists. Skipping migration.")


if __name__ == "__main__":
    asyncio.run(add_password_hash_column())

