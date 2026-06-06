"""Gate student-fund marketplace actions until a school student is linked to the circle."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import HTTPException

from app.models.school import SchoolStudent


async def circle_enrolled_student_count(db: AsyncSession, circle_id: str) -> int:
    res = await db.execute(
        select(func.count())
        .select_from(SchoolStudent)
        .where(SchoolStudent.circle_id == circle_id)
    )
    return int(res.scalar_one() or 0)


async def assert_circle_has_enrolled_student(db: AsyncSession, circle_id: str) -> None:
    if await circle_enrolled_student_count(db, circle_id) < 1:
        raise HTTPException(
            status_code=403,
            detail=(
                "No sponsored student enrolled in this circle yet. "
                "Approve a school enrollment before placing student fund orders."
            ),
        )
