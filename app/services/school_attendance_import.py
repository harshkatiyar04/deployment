"""CSV import for monthly school attendance records."""

from __future__ import annotations

import csv
import io
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.school import SchoolAttendance, SchoolProfile, SchoolStudent
from app.models.signup import SignupRequest

ATTENDANCE_CSV_HEADERS = [
    "student_id",
    "student_name",
    "month",
    "year",
    "attendance_pct",
    "working_days",
    "days_present",
]


def attendance_csv_template(students: list[SchoolStudent]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(ATTENDANCE_CSV_HEADERS)
    if students:
        s = students[0]
        writer.writerow([s.id, s.full_name, 4, 2025, 95, 22, 21])
        writer.writerow([s.id, s.full_name, 5, 2025, 92, 23, 21])
    return buf.getvalue()


def _norm(row: dict[str, str]) -> dict[str, str]:
    return {(k or "").strip().lower().replace(" ", "_"): (v or "").strip() for k, v in row.items()}


def calc_attendance_pct(working_days: int, days_present: int) -> float:
    if working_days < 1:
        raise ValueError("working_days must be at least 1")
    if days_present < 0 or days_present > working_days:
        raise ValueError("days_present must be between 0 and working_days")
    return round((days_present / working_days) * 100, 1)


async def upsert_monthly_attendance(
    db: AsyncSession,
    *,
    student: SchoolStudent,
    month: int,
    year: int,
    working_days: int,
    days_present: int,
) -> SchoolAttendance:
    if month < 1 or month > 12:
        raise ValueError("month must be 1–12")
    if year < 2020 or year > 2035:
        raise ValueError("year out of range")

    pct = calc_attendance_pct(working_days, days_present)

    res = await db.execute(
        select(SchoolAttendance).where(
            SchoolAttendance.student_id == student.id,
            SchoolAttendance.month == month,
            SchoolAttendance.year == year,
        )
    )
    existing = res.scalar_one_or_none()
    if existing:
        existing.attendance_pct = pct
        existing.working_days = working_days
        existing.days_present = days_present
        return existing

    record = SchoolAttendance(
        id=str(uuid.uuid4()),
        student_id=student.id,
        month=month,
        year=year,
        attendance_pct=pct,
        working_days=working_days,
        days_present=days_present,
    )
    db.add(record)
    return record


async def save_attendance_entry(
    db: AsyncSession,
    *,
    school_id: str,
    student_id: str,
    month: int,
    year: int,
    working_days: int,
    days_present: int,
) -> SchoolAttendance:
    st_res = await db.execute(
        select(SchoolStudent).where(
            SchoolStudent.id == student_id,
            SchoolStudent.school_id == school_id,
        )
    )
    student = st_res.scalar_one_or_none()
    if not student:
        raise ValueError("Student not found for this school")

    record = await upsert_monthly_attendance(
        db,
        student=student,
        month=month,
        year=year,
        working_days=working_days,
        days_present=days_present,
    )
    await _recalc_student_annual(db, student)
    await _recalc_school_profile(db, school_id)
    await db.commit()
    await db.refresh(record)
    return record


def _resolve_student(row: dict[str, str], by_id: dict, by_name: dict) -> SchoolStudent:
    sid = row.get("student_id", "")
    if sid:
        st = by_id.get(sid)
        if st:
            return st
        raise ValueError(f"student_id not found: {sid}")
    name = row.get("student_name", "")
    if name:
        st = by_name.get(name.lower())
        if st:
            return st
        raise ValueError(f"student_name not found: {name}")
    raise ValueError("student_id or student_name is required")


async def _recalc_student_annual(db: AsyncSession, student: SchoolStudent) -> None:
    res = await db.execute(
        select(SchoolAttendance).where(SchoolAttendance.student_id == student.id)
    )
    rows = res.scalars().all()
    if not rows:
        return
    total_wd = sum(r.working_days for r in rows)
    total_dp = sum(r.days_present for r in rows)
    if total_wd > 0:
        student.attendance_pct = round((total_dp / total_wd) * 100, 1)
    else:
        student.attendance_pct = round(
            sum(r.attendance_pct for r in rows) / len(rows), 1
        )


async def _recalc_school_profile(db: AsyncSession, school_id: str) -> None:
    res = await db.execute(select(SchoolStudent).where(SchoolStudent.school_id == school_id))
    students = res.scalars().all()
    profile_res = await db.execute(select(SchoolProfile).where(SchoolProfile.id == school_id))
    profile = profile_res.scalar_one_or_none()
    if not profile or not students:
        return
    profile.avg_attendance = sum(s.attendance_pct for s in students) / len(students)


async def import_attendance_csv(
    db: AsyncSession,
    *,
    school_id: str,
    user: SignupRequest,
    file_bytes: bytes,
) -> dict[str, Any]:
    try:
        decoded = file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise ValueError("CSV must be UTF-8 encoded") from e

    reader = csv.DictReader(io.StringIO(decoded))
    students_res = await db.execute(
        select(SchoolStudent).where(SchoolStudent.school_id == school_id)
    )
    students = students_res.scalars().all()
    by_id = {s.id: s for s in students}
    by_name = {s.full_name.strip().lower(): s for s in students}

    success_count = 0
    errors: list[str] = []
    touched_students: set[str] = set()

    for row_idx, raw in enumerate(reader, start=2):
        row = _norm(raw)
        if not any(row.values()):
            continue
        try:
            async with db.begin_nested():
                student = _resolve_student(row, by_id, by_name)
                month = int(row.get("month") or "")
                year = int(row.get("year") or "")
                if month < 1 or month > 12:
                    raise ValueError("month must be 1–12")
                if year < 2020 or year > 2035:
                    raise ValueError("year out of range")

                working_days = int(row.get("working_days") or 0)
                days_present_raw = row.get("days_present", "")
                pct_raw = row.get("attendance_pct", "")

                if working_days >= 1 and days_present_raw != "":
                    days_present = int(days_present_raw)
                    if working_days > 31:
                        raise ValueError("working_days must be 1–31")
                    await upsert_monthly_attendance(
                        db,
                        student=student,
                        month=month,
                        year=year,
                        working_days=working_days,
                        days_present=days_present,
                    )
                elif pct_raw != "":
                    pct = float(pct_raw)
                    if pct < 0 or pct > 100:
                        raise ValueError("attendance_pct must be 0–100")
                    wd = working_days if working_days >= 1 else 22
                    if wd > 31:
                        raise ValueError("working_days must be 1–31")
                    dp = int(days_present_raw) if days_present_raw else int(round((pct / 100.0) * wd))
                    await upsert_monthly_attendance(
                        db,
                        student=student,
                        month=month,
                        year=year,
                        working_days=wd,
                        days_present=dp,
                    )
                else:
                    raise ValueError(
                        "Provide working_days and days_present, or attendance_pct"
                    )

            touched_students.add(student.id)
            success_count += 1
        except Exception as e:
            errors.append(f"Row {row_idx}: {e}")

    for sid in touched_students:
        st = by_id[sid]
        await _recalc_student_annual(db, st)

    if success_count > 0:
        await _recalc_school_profile(db, school_id)
        await db.commit()
    else:
        await db.rollback()

    return {
        "status": "success" if success_count else "failed",
        "message": (
            f"Imported {success_count} monthly attendance row(s)."
            if success_count
            else "No rows imported."
        ),
        "success_count": success_count,
        "errors": errors,
        "imported_by": user.full_name or "School staff",
    }
