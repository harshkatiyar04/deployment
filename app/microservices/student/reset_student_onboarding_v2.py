"""
Flush legacy student onboarding data so v2 signups start clean.

Run from zenkimpact_BE:
  python -m app.microservices.student.reset_student_onboarding_v2

Does NOT delete school@zenk, sponsors, vendors, or circle definitions.
"""
from __future__ import annotations

import asyncio
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from sqlalchemy import text

from app.db.session import engine


async def flush_student_data() -> None:
    print("=== Flush student onboarding data (v2 reset) ===")

    async with engine.begin() as conn:
        student_ids_res = await conn.execute(
            text(
                """
                SELECT id FROM "ZENK".signup_requests
                WHERE persona::text = 'student'
                """
            )
        )
        student_ids = [str(r[0]) for r in student_ids_res.fetchall()]

        parent_ids_res = await conn.execute(
            text(
                """
                SELECT parent_signup_id FROM "ZENK".student_family_links
                UNION
                SELECT id FROM "ZENK".signup_requests
                WHERE member_kind = 'parent_guardian'
                """
            )
        )
        parent_ids = list({str(r[0]) for r in parent_ids_res.fetchall() if r[0]})

        all_ids = list({*student_ids, *parent_ids})
        print(f"Student signups: {len(student_ids)}, parent/guardian: {len(parent_ids)}")

        await conn.execute(text('DELETE FROM "ZENK".student_probe_messages'))
        await conn.execute(text('DELETE FROM "ZENK".student_circle_interest_requests'))
        await conn.execute(text('DELETE FROM "ZENK".student_school_interests'))

        if student_ids:
            await conn.execute(
                text('DELETE FROM "ZENK".student_mentoring_messages WHERE thread_id IN (SELECT id FROM "ZENK".student_mentoring_threads WHERE student_signup_id = ANY(:ids))'),
                {"ids": student_ids},
            )
            await conn.execute(
                text('DELETE FROM "ZENK".student_mentoring_threads WHERE student_signup_id = ANY(:ids)'),
                {"ids": student_ids},
            )
            await conn.execute(
                text('DELETE FROM "ZENK".student_kia_messages WHERE student_signup_id = ANY(:ids)'),
                {"ids": student_ids},
            )
            await conn.execute(
                text('DELETE FROM "ZENK".parent_academic_submissions WHERE student_signup_id = ANY(:ids)'),
                {"ids": student_ids},
            )
            await conn.execute(
                text('DELETE FROM "ZENK".circle_members WHERE user_id = ANY(:ids)'),
                {"ids": student_ids},
            )
            await conn.execute(
                text('DELETE FROM "ZENK".school_students WHERE zenk_id = ANY(:ids)'),
                {"ids": student_ids},
            )

        await conn.execute(text('DELETE FROM "ZENK".student_family_links'))

        if all_ids:
            await conn.execute(
                text('DELETE FROM "ZENK".kyc_documents WHERE signup_id = ANY(:ids)'),
                {"ids": all_ids},
            )
            await conn.execute(
                text('DELETE FROM "ZENK".signup_requests WHERE id = ANY(:ids)'),
                {"ids": all_ids},
            )

        await conn.execute(
            text(
                """
                UPDATE "ZENK".school_profiles
                SET total_enrolled = (
                    SELECT COUNT(*) FROM "ZENK".school_students ss WHERE ss.school_id = school_profiles.id
                ),
                updated_at = NOW()
                """
            )
        )

    print("Done. New students should sign up with school dropdown + parent KYC (v2).")


if __name__ == "__main__":
    asyncio.run(flush_student_data())
