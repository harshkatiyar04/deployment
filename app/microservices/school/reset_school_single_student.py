"""
Reset school@zenk to a single empty student — no seeded scores, narratives, or reports.
Run: python -m app.microservices.school.reset_school_single_student
"""
from __future__ import annotations

import asyncio
import sys
import os
import uuid

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from sqlalchemy import text
from app.db.session import engine


async def reset_school_data():
    print("=== Reset school data: one empty student ===")

    async with engine.begin() as conn:
        res = await conn.execute(
            text(
                'SELECT id FROM "ZENK".signup_requests WHERE email = :email'
            ),
            {"email": "school@zenk"},
        )
        row = res.fetchone()
        if not row:
            print("ERROR: school@zenk not found. Start the API once to auto-seed accounts.")
            return

        school_id = str(row[0])
        print(f"School ID: {school_id}")

        await conn.execute(
            text('DELETE FROM "ZENK".school_form_submissions WHERE school_id = :sid'),
            {"sid": school_id},
        )
        await conn.execute(
            text('DELETE FROM "ZENK".school_kia_messages WHERE school_id = :sid'),
            {"sid": school_id},
        )
        await conn.execute(
            text('DELETE FROM "ZENK".school_students WHERE school_id = :sid'),
            {"sid": school_id},
        )

        student_id = str(uuid.uuid4())
        await conn.execute(
            text("""
                INSERT INTO "ZENK".school_students (
                    id, school_id, full_name, grade,
                    attendance_pct, avg_score, zqa_score,
                    risk_level, q_report_status,
                    tutor_recommendation_status,
                    created_at
                ) VALUES (
                    :id, :school_id, :name, :grade,
                    0, 0, 0,
                    'Low', 'Pending',
                    'none',
                    NOW()
                )
            """),
            {
                "id": student_id,
                "school_id": school_id,
                "name": "Ravi Mehta",
                "grade": "Grade 10",
            },
        )

        await conn.execute(
            text("""
                UPDATE "ZENK".school_profiles
                SET total_enrolled = 1,
                    avg_attendance = 0,
                    avg_academic_score = 0,
                    reports_pending = 1,
                    updated_at = NOW()
                WHERE id = :sid
            """),
            {"sid": school_id},
        )

        await conn.execute(
            text('DELETE FROM "ZENK".school_kia_welcome WHERE id = :sid'),
            {"sid": school_id},
        )
        await conn.execute(
            text("""
                INSERT INTO "ZENK".school_kia_welcome (
                    id, welcome_sent, welcome_message, task_list, created_at
                ) VALUES (
                    :sid, FALSE,
                    'Welcome to your ZenK School Dashboard. Submit reports and attendance to see live metrics.',
                    '["Review students","Submit quarterly report","Enter monthly attendance"]'::jsonb,
                    NOW()
                )
            """),
            {"sid": school_id},
        )

        print(f"Created student: Ravi Mehta ({student_id})")
        print("Profile metrics reset to zeros. Submit the quarterly form to populate live data.")


if __name__ == "__main__":
    asyncio.run(reset_school_data())
