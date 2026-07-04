"""Daily welfare scan for ZenQ circles (Phase 4)."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.algorithms.zenq.welfare import evaluate_welfare_level, welfare_level_label
from app.chat.models import ChatChannel, ChatMessage, SponsorCircle
from app.models.school import SchoolStudent
from app.models.zenq import ZenqSponsorMetrics, ZenqWelfareCase
from app.chat.models import SOSReport

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def _max_sponsor_silence_days(db: AsyncSession, circle_id: str) -> int:
    metrics_res = await db.execute(
        select(ZenqSponsorMetrics.updated_at).where(
            ZenqSponsorMetrics.circle_id == circle_id,
            ZenqSponsorMetrics.window_key == "30d",
            ZenqSponsorMetrics.message_count > 0,
        )
    )
    timestamps = [r[0] for r in metrics_res.all() if r[0]]
    if timestamps:
        latest = max(timestamps)
        if latest.tzinfo is None:
            latest = latest.replace(tzinfo=timezone.utc)
        return (_utcnow() - latest).days

    since = _utcnow() - timedelta(days=60)
    since_naive = since.replace(tzinfo=None)
    msg_res = await db.execute(
        select(func.max(ChatMessage.created_at))
        .select_from(ChatMessage)
        .join(ChatChannel, ChatChannel.id == ChatMessage.channel_id)
        .where(ChatChannel.circle_id == circle_id, ChatMessage.created_at >= since_naive)
    )
    last_msg = msg_res.scalar_one_or_none()
    if not last_msg:
        return 60
    if last_msg.tzinfo is None:
        last_msg = last_msg.replace(tzinfo=timezone.utc)
    return (_utcnow() - last_msg).days


async def _circle_welfare_signals(db: AsyncSession, circle_id: str) -> dict[str, Any]:
    student_res = await db.execute(
        select(SchoolStudent).where(SchoolStudent.circle_id == circle_id)
    )
    students = student_res.scalars().all()
    critical_need = any((s.risk_level or "").lower() == "high" for s in students)
    attendance_below_80 = any(float(s.attendance_pct or 0) < 80 for s in students)
    no_zqa = all(float(s.zqa_score or 0) <= 0 for s in students) if students else False

    sos_res = await db.execute(
        select(func.count(SOSReport.id))
        .select_from(SOSReport)
        .join(ChatMessage, ChatMessage.id == SOSReport.message_id)
        .join(ChatChannel, ChatChannel.id == ChatMessage.channel_id)
        .where(
            ChatChannel.circle_id == circle_id,
            SOSReport.resolved_at.is_(None),
        )
    )
    sos_open = int(sos_res.scalar() or 0) > 0

    return {
        "max_sponsor_silence_days": await _max_sponsor_silence_days(db, circle_id),
        "critical_need": critical_need,
        "attendance_below_80": attendance_below_80,
        "no_student_zqa_2q": no_zqa and len(students) > 0,
        "sos_open": sos_open,
        "student_count": len(students),
    }


async def scan_circle_welfare(db: AsyncSession, circle_id: str) -> Optional[dict[str, Any]]:
    signals = await _circle_welfare_signals(db, circle_id)
    level, issues = evaluate_welfare_level(signals)
    if level <= 0:
        return None

    existing_res = await db.execute(
        select(ZenqWelfareCase)
        .where(
            ZenqWelfareCase.circle_id == circle_id,
            ZenqWelfareCase.status == "open",
        )
        .order_by(ZenqWelfareCase.opened_at.desc())
        .limit(1)
    )
    existing = existing_res.scalar_one_or_none()
    if existing and existing.level >= level:
        existing.signals_json = issues
        await db.commit()
        return {
            "id": existing.id,
            "circle_id": circle_id,
            "level": existing.level,
            "status": existing.status,
            "updated": True,
        }

    row = ZenqWelfareCase(
        circle_id=circle_id,
        level=level,
        status="open",
        signals_json=issues,
        notes=f"Auto-detected: {', '.join(issues)}",
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return {
        "id": row.id,
        "circle_id": circle_id,
        "level": level,
        "label": welfare_level_label(level),
        "signals": issues,
        "created": True,
    }


async def run_welfare_scan_all_circles(db: AsyncSession) -> dict[str, Any]:
    res = await db.execute(
        select(SponsorCircle.id).where(SponsorCircle.status == "active")
    )
    circle_ids = [r[0] for r in res.all()]
    created = 0
    updated = 0
    for cid in circle_ids:
        try:
            result = await scan_circle_welfare(db, cid)
            if result:
                if result.get("created"):
                    created += 1
                else:
                    updated += 1
        except Exception:
            logger.exception("[ZenQ welfare] scan failed for %s", cid)
            await db.rollback()
    return {
        "circles_scanned": len(circle_ids),
        "cases_created": created,
        "cases_updated": updated,
    }


async def list_open_welfare_cases(
    db: AsyncSession,
    *,
    limit: int = 100,
) -> list[dict[str, Any]]:
    res = await db.execute(
        select(ZenqWelfareCase, SponsorCircle.name)
        .join(SponsorCircle, SponsorCircle.id == ZenqWelfareCase.circle_id)
        .where(ZenqWelfareCase.status == "open")
        .order_by(ZenqWelfareCase.level.desc(), ZenqWelfareCase.opened_at.desc())
        .limit(limit)
    )
    out: list[dict[str, Any]] = []
    for case, circle_name in res.all():
        out.append(
            {
                "id": case.id,
                "circle_id": case.circle_id,
                "circle_name": circle_name,
                "level": case.level,
                "label": welfare_level_label(case.level),
                "signals": case.signals_json or [],
                "notes": case.notes,
                "opened_at": case.opened_at.isoformat() if case.opened_at else None,
            }
        )
    return out


async def resolve_welfare_case(
    db: AsyncSession,
    case_id: str,
    *,
    resolved_by: str,
    notes: Optional[str] = None,
) -> bool:
    res = await db.execute(select(ZenqWelfareCase).where(ZenqWelfareCase.id == case_id))
    case = res.scalar_one_or_none()
    if not case or case.status != "open":
        return False
    case.status = "resolved"
    case.resolved_at = _utcnow()
    case.resolved_by = resolved_by
    if notes:
        case.notes = notes
    await db.commit()
    return True
