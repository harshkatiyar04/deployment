"""
Migration 008 — Mentor Circle Chat
====================================
1. Adds `circle_id` UUID column to mentor_profiles (nullable FK → sponsor_circles)
2. Adds `dm_channel_prefix` column to chat_channels for private DM channels
3. Seeds Arvind Kumar (mentor@zenk.in) as a CircleMember in the "Ashoka Rising" circle
   so he can connect to the real WebSocket.

Run once: python app/db/migrations/migration_008_mentor_circle_chat.py
"""
import asyncio
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from app.db.session import engine, SessionLocal
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_migration():
    logger.info("=== Migration 008: Mentor Circle Chat ===")

    async with engine.begin() as conn:
        logger.info("Step 1: Adding circle_id to mentor_profiles...")
        await conn.execute(text("""
            ALTER TABLE "ZENK"."mentor_profiles"
            ADD COLUMN IF NOT EXISTS circle_id UUID
            REFERENCES "ZENK"."sponsor_circles"(id) ON DELETE SET NULL
        """))

        logger.info("Step 2: Adding dm_for column to chat_channels (for private DMs)...")
        await conn.execute(text("""
            ALTER TABLE "ZENK"."chat_channels"
            ADD COLUMN IF NOT EXISTS dm_for TEXT DEFAULT NULL
        """))
        # dm_for holds a JSON string like '["user_a_id", "user_b_id"]' for private DM channels

        logger.info("Step 3: Index on dm_for for fast lookups...")
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_chat_channels_dm_for
            ON "ZENK"."chat_channels"(circle_id, dm_for)
            WHERE dm_for IS NOT NULL
        """))

    logger.info("Step 4: Enrolling mentor@zenk.in as CircleMember in their assigned circle...")
    async with SessionLocal() as db:
        from sqlalchemy import select
        from app.chat.models import SponsorCircle, CircleMember, ChatChannel
        from app.models.signup import SignupRequest

        # Get the mentor user
        mentor_res = await db.execute(
            select(SignupRequest).where(SignupRequest.email == "mentor@zenk.in")
        )
        mentor = mentor_res.scalar_one_or_none()
        if not mentor:
            logger.warning("mentor@zenk.in not found — run seed_mentor.py first!")
            return

        # Get the "leader@zenk.in" sponsor circle (Ashoka Rising)
        # We'll look for any circle with "Ashoka" in the name, or take the first circle
        circle_res = await db.execute(
            select(SponsorCircle).where(
                SponsorCircle.name.ilike("%ashoka%")
            ).limit(1)
        )
        circle = circle_res.scalar_one_or_none()

        if not circle:
            # Fall back to first available circle
            circle_res = await db.execute(select(SponsorCircle).limit(1))
            circle = circle_res.scalar_one_or_none()

        if not circle:
            logger.warning("No sponsor circle found. Create one first via the sponsor dashboard.")
            logger.warning("Skipping CircleMember enrollment — run migration again after a circle exists.")
            return

        logger.info(f"Using circle: {circle.name} ({circle.id})")

        # Check if already enrolled
        existing = await db.execute(
            select(CircleMember).where(
                CircleMember.circle_id == circle.id,
                CircleMember.user_id == mentor.id,
            )
        )
        if not existing.scalar_one_or_none():
            db.add(CircleMember(
                circle_id=circle.id,
                user_id=mentor.id,
                role="mentor",
            ))
            logger.info(f"✅ Enrolled mentor@zenk.in as CircleMember(role='mentor') in '{circle.name}'")
        else:
            logger.info("mentor@zenk.in already enrolled in this circle — skipping.")

        # Update mentor_profiles.circle_id to point to this circle
        await db.execute(
            text("""
                UPDATE "ZENK"."mentor_profiles"
                SET circle_id = :cid
                WHERE id = :uid
            """),
            {"cid": circle.id, "uid": mentor.id},
        )
        logger.info(f"✅ mentor_profiles.circle_id set to {circle.id}")

        # Ensure a #mentor-lounge channel exists in this circle
        lounge_res = await db.execute(
            select(ChatChannel).where(
                ChatChannel.circle_id == circle.id,
                ChatChannel.name == "mentor-lounge",
            )
        )
        if not lounge_res.scalar_one_or_none():
            lounge = ChatChannel(
                circle_id=circle.id,
                name="mentor-lounge",
                channel_type="persistent",
            )
            db.add(lounge)
            logger.info("✅ Created #mentor-lounge channel")
        else:
            logger.info("#mentor-lounge already exists — skipping.")

        await db.commit()

    logger.info("=== Migration 008 complete ===")


if __name__ == "__main__":
    asyncio.run(run_migration())
