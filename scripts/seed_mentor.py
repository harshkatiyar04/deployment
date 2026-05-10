"""
Seed Mentor Demo Account
========================
Creates:
  - mentor@zenk.in / mentor123  (persona=mentor, kyc=approved)
  - MentorProfile for Arvind Kumar (Tier 9, InspireIndex 84.2)
  - 8 MentorSessions across 4 circles
  - 3 MentorUpliftActions

Run once: python scripts/seed_mentor.py
"""
import asyncio
import logging
import sys
import os
import uuid
from datetime import datetime
from sqlalchemy import text

# Allow running from the project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def seed():
    from app.db.session import SessionLocal
    from app.models.signup import SignupRequest
    from app.models.enums import Persona, KycStatus
    from app.models.mentor import MentorProfile, MentorSession, MentorUpliftAction
    from app.core.security import hash_password
    from sqlalchemy import select

    async with SessionLocal() as db:
        # ── 1. Check if account already exists ────────────────────────────────
        existing = await db.execute(
            select(SignupRequest).where(SignupRequest.email == "mentor@zenk.in")
        )
        signup = existing.scalar_one_or_none()

        if not signup:
            logger.info("Creating mentor@zenk.in account via raw SQL...")
            mentor_user_id = str(uuid.uuid4())
            hashed_pw = hash_password("mentor123")
            await db.execute(
                text("""
                    INSERT INTO "ZENK".signup_requests
                        (id, persona, full_name, mobile, email, password_hash,
                         address_line1, address_line2, city, state, pincode, country,
                         kyc_status, created_at, updated_at)
                    VALUES
                        (:id, 'mentor', :full_name, :mobile, :email, :pw,
                         'ZenK Platform', 'Bengaluru', 'Bengaluru', 'Karnataka', '560001', 'India',
                         'approved', NOW(), NOW())
                """),
                {
                    "id": mentor_user_id,
                    "full_name": "Arvind Kumar",
                    "mobile": "9876543210",
                    "email": "mentor@zenk.in",
                    "pw": hashed_pw,
                }
            )
        else:
            mentor_user_id = signup.id
            logger.info(f"mentor@zenk.in already exists (id={mentor_user_id})")

        # ── 2. Check if profile already exists ────────────────────────────────
        existing_profile = await db.execute(
            select(MentorProfile).where(MentorProfile.id == mentor_user_id)
        )
        profile = existing_profile.scalar_one_or_none()

        if not profile:
            logger.info("Creating MentorProfile for Arvind Kumar...")
            profile = MentorProfile(
                id=mentor_user_id,
                mentor_id="ZNK-MEN-2024-019",
                specialty="Technology & career mentoring",
                city="Bengaluru",
                tier=9,
                tier_label="Tier 9 — Master",
                sessions_this_fy=22,
                hours_mentored=44.0,
                inspire_index=84.2,
                inspire_index_percentile=82,  # top 18%
                inspire_index_delta=3.1,
                zenq_contribution=6.1,
                community_uplift_count=3,
                inspire_breakdown={
                    "session_consistency": 36.4,
                    "student_engagement": 28.8,
                    "topic_diversity": 12.6,
                    "community_uplift": 6.0,
                    "circle_feedback_score": 0.4,
                },
                assigned_circles=[
                    "Circles Ashoka Rising",
                    "Udaan Bangalore",
                ],
                badges=[
                    "ZenK Verified",
                    "Tier 9 — Master",
                    "InspireIndex Top 20%",
                ],
                kia_insight=(
                    "Your InspireIndex is growing at +3.1 pts/month. "
                    "To reach 90+ (top 5% of mentors), Kia recommends: log the inspiration "
                    "story field in every session — you do this in 60% of sessions. "
                    "Completing the ZenK Community Guest Talk in May would add +2.4 pts immediately.\n"
                    "Kia suggests: Schedule your next guest talk this month to accelerate your tier progression."
                ),
            )
            db.add(profile)
        else:
            logger.info("MentorProfile already exists, skipping.")

        # ── 3. Sessions ───────────────────────────────────────────────────────
        existing_sessions = await db.execute(
            select(MentorSession).where(MentorSession.mentor_id == mentor_user_id)
        )
        if not existing_sessions.scalars().all():
            logger.info("Seeding 8 MentorSessions...")
            sessions_data = [
                {
                    "student_circle": "Ananya D. — Ashoka Rising",
                    "session_date": "2025-04-16",
                    "topic_area": "Career guidance",
                    "duration_hrs": 1.0,
                    "mode": "ZenK Circle Chat video call",
                    "engagement_level": "Highly engaged — asked great questions",
                    "session_notes": "Discussed career paths in technology. Student showed great curiosity about AI and data science. Shared my journey from engineering to product management. Set a reading goal: one tech article per week.",
                    "inspiration_shared": "Shared the story of APJ Abdul Kalam's journey from a small town to becoming President. Discussed how curiosity and persistence matter more than background.",
                    "zenq_impact": 0.6,
                    "inspire_pts": 0.9,
                },
                {
                    "student_circle": "Riya P. — Udaan Bangalore",
                    "session_date": "2025-04-08",
                    "topic_area": "Study strategies",
                    "duration_hrs": 0.5,
                    "mode": "ZenK Circle Chat video call",
                    "engagement_level": "Engaged",
                    "session_notes": "Helped Riya develop a revision timetable for her board exams. Introduced the Pomodoro technique. She committed to 2 hours of focused study per day.",
                    "inspiration_shared": None,
                    "zenq_impact": 0.2,
                    "inspire_pts": 0.2,
                },
                {
                    "student_circle": "Arjun K. — Ashoka Rising",
                    "session_date": "2025-03-28",
                    "topic_area": "Goal setting",
                    "duration_hrs": 1.0,
                    "mode": "ZenK Circle Chat video call",
                    "engagement_level": "Highly engaged — asked great questions",
                    "session_notes": "Set 3-month, 6-month, and 1-year goals with Arjun. Mapped out steps to reach his target of a CS engineering seat. Created an accountability checklist.",
                    "inspiration_shared": "Shared how Sundar Pichai set small, consistent goals throughout his student life. Emphasized that systems beat motivation.",
                    "zenq_impact": 0.5,
                    "inspire_pts": 0.9,
                },
                {
                    "student_circle": "Meera S. — Udaan Bangalore",
                    "session_date": "2025-03-15",
                    "topic_area": "Communication skills",
                    "duration_hrs": 0.5,
                    "mode": "Video call",
                    "engagement_level": "Moderately engaged",
                    "session_notes": "Practiced mock interview questions. Worked on structuring answers using the STAR method. Meera was nervous initially but relaxed as we progressed.",
                    "inspiration_shared": None,
                    "zenq_impact": 0.2,
                    "inspire_pts": 0.2,
                },
                {
                    "student_circle": "Ananya D. — Ashoka Rising",
                    "session_date": "2025-03-01",
                    "topic_area": "Mental wellbeing",
                    "duration_hrs": 0.5,
                    "mode": "ZenK Circle Chat video call",
                    "engagement_level": "Engaged",
                    "session_notes": "Ananya expressed stress around board exams. Discussed healthy coping mechanisms — journaling, breathing exercises, sleep hygiene. Encouraged her to speak with the school counselor.",
                    "inspiration_shared": "Shared how managing stress is a life skill that engineers, doctors, and leaders all invest in.",
                    "zenq_impact": 0.2,
                    "inspire_pts": 0.5,
                },
                {
                    "student_circle": "Kabir R. — Ashoka Rising",
                    "session_date": "2025-02-18",
                    "topic_area": "Career guidance",
                    "duration_hrs": 1.5,
                    "mode": "In-person (ZenK campus visit)",
                    "engagement_level": "Highly engaged — asked great questions",
                    "session_notes": "Long deep-dive into emerging tech careers. Covered AI, robotics, renewable energy engineering. Kabir is interested in EV tech. Shared open source projects to explore. Connected him with a startup founder I know.",
                    "inspiration_shared": "Shared Elon Musk's early interest in physics and computing as a student with no formal guidance. Talked about curiosity as the highest form of intelligence.",
                    "zenq_impact": 0.8,
                    "inspire_pts": 0.9,
                },
                {
                    "student_circle": "Riya P. — Udaan Bangalore",
                    "session_date": "2025-02-05",
                    "topic_area": "Financial literacy",
                    "duration_hrs": 0.5,
                    "mode": "ZenK Circle Chat video call",
                    "engagement_level": "Engaged",
                    "session_notes": "Introduced the basics of personal finance: savings, compound interest, budgeting. Used simple analogies. Riya said she never had anyone explain money to her before.",
                    "inspiration_shared": "Shared Warren Buffett's first investment at age 11 — emphasized it is never too early to learn about money.",
                    "zenq_impact": 0.2,
                    "inspire_pts": 0.5,
                },
                {
                    "student_circle": "Meera S. — Udaan Bangalore",
                    "session_date": "2025-01-22",
                    "topic_area": "Science & STEM",
                    "duration_hrs": 1.0,
                    "mode": "Video call",
                    "engagement_level": "Highly engaged — asked great questions",
                    "session_notes": "Explored Meera's love for biology and potential paths in biotech and healthcare. Introduced NEET vs. BSc Biology paths. Shared resources and YouTube channels for self-study.",
                    "inspiration_shared": "Shared Dr. Kiran Mazumdar-Shaw's journey — from brewing to biotech, how passion and pivot define careers.",
                    "zenq_impact": 0.5,
                    "inspire_pts": 0.9,
                },
            ]

            for s in sessions_data:
                session = MentorSession(
                    id=str(uuid.uuid4()),
                    mentor_id=mentor_user_id,
                    created_at=datetime.utcnow(),
                    **s,
                )
                db.add(session)
        else:
            logger.info("Sessions already exist, skipping.")

        # ── 4. Uplift Actions ─────────────────────────────────────────────────
        existing_uplifts = await db.execute(
            select(MentorUpliftAction).where(MentorUpliftAction.mentor_id == mentor_user_id)
        )
        if not existing_uplifts.scalars().all():
            logger.info("Seeding 3 MentorUpliftActions...")
            uplifts_data = [
                {
                    "action_type": "guest_talk",
                    "title": "ZenK Career Discovery Day — IIT Bengaluru",
                    "description": "Delivered a 45-min talk on careers in product management and AI to 60+ students from 3 sponsored circles. Q&A session lasted 20 minutes.",
                    "event_date": "2025-03-20",
                    "impact_score": 0.8,
                    "verified": True,
                },
                {
                    "action_type": "resource_sharing",
                    "title": "Published: 'How to Choose Your Engineering Stream' Guide",
                    "description": "Wrote a 1200-word guide shared across all ZenK circles in Bengaluru. Over 140 students accessed the resource within 2 weeks.",
                    "event_date": "2025-02-28",
                    "impact_score": 0.5,
                    "verified": True,
                },
                {
                    "action_type": "career_event",
                    "title": "Mock Interview Workshop — Ashoka Rising Circle",
                    "description": "Conducted 8 mock interviews with circle students over one afternoon. Provided written feedback for each participant. Two students said it was their first-ever interview practice.",
                    "event_date": "2025-01-15",
                    "impact_score": 0.8,
                    "verified": False,
                },
            ]

            for u in uplifts_data:
                action = MentorUpliftAction(
                    id=str(uuid.uuid4()),
                    mentor_id=mentor_user_id,
                    created_at=datetime.utcnow(),
                    **u,
                )
                db.add(action)
        else:
            logger.info("Uplift actions already exist, skipping.")

        await db.commit()
        logger.info("✅ Seed complete — login: mentor@zenk.in / mentor123")


if __name__ == "__main__":
    asyncio.run(seed())
