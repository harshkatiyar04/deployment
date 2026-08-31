"""Unified admin omni-search — aggregates signups, users, circles, and ops records."""

from __future__ import annotations

import time
from typing import Any, Optional

from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.chat.models import ChatMessage, CircleMember, GamifiedPersona, SOSReport, SponsorCircle
from app.models.enums import KycStatus, MemberKind, Persona
from app.models.signup import SignupRequest
from app.services.admin_circle_overview import LEADER_ROLES
from app.services.admin_legal_registry import list_legal_acceptances
from app.services.admin_suppliers_registry import build_admin_suppliers_registry
from app.services.admin_support_chat import list_support_contacts
from app.services.landing_contact_store import list_landing_contact_inquiries

PERSONA_LABELS = {
    Persona.sponsor: "Sponsor",
    Persona.sponsor_leader: "Sponsor Leader",
    Persona.sponsor_member: "Sponsor Member",
    Persona.vendor: "Vendor",
    Persona.student: "Student",
    Persona.corporate: "Corporate",
    Persona.mentor: "Mentor",
    Persona.school: "School",
}

KYC_STATUS_LABELS = {
    KycStatus.pending: "Pending",
    KycStatus.approved: "Approved",
    KycStatus.rejected: "Rejected",
    KycStatus.info_required: "Info requested",
}

DOC_TYPE_LABELS = {
    "platform_terms": "Platform terms",
    "privacy_policy": "Privacy policy",
    "parent_member_terms": "Parent / member terms",
    "student_declaration": "Student declaration",
}

_CACHE: dict[tuple[str, int], tuple[float, dict[str, Any]]] = {}
_CACHE_TTL_SEC = 30.0
_CACHE_MAX = 128


def _display_role(signup: SignupRequest) -> str:
    if signup.persona == Persona.student:
        return "Student"
    if signup.persona == Persona.sponsor_member and signup.member_kind == MemberKind.parent_guardian.value:
        return "Parent / guardian"
    if signup.persona == Persona.sponsor_member:
        return "Circle member"
    return PERSONA_LABELS.get(signup.persona, signup.persona.value)


def _kyc_status_value(status: KycStatus) -> str:
    return status.value if hasattr(status, "value") else str(status)


def _signup_search_filter(q, needle: str):
    pattern = f"%{needle}%"
    return q.where(
        or_(
            SignupRequest.full_name.ilike(pattern),
            SignupRequest.email.ilike(pattern),
            SignupRequest.mobile.ilike(pattern),
            cast(SignupRequest.id, String).ilike(pattern),
            SignupRequest.school_name.ilike(pattern),
            SignupRequest.company_name.ilike(pattern),
            SignupRequest.business_name.ilike(pattern),
            SignupRequest.requested_circle_name.ilike(pattern),
            SignupRequest.school_or_college_name.ilike(pattern),
        )
    )


def _rank_score(needle: str, *fields: Optional[str]) -> int:
    n = needle.lower()
    best = 0
    for field in fields:
        if not field:
            continue
        value = field.lower()
        if value == n:
            best = max(best, 100)
        elif value.startswith(n):
            best = max(best, 80)
        elif n in value:
            best = max(best, 50)
    return best


def _sort_records(items: list[dict[str, Any]], needle: str) -> list[dict[str, Any]]:
    return sorted(
        items,
        key=lambda item: -_rank_score(
            needle,
            item.get("title"),
            item.get("subtitle"),
            item.get("id"),
        ),
    )


def _record(
    *,
    id: str,
    title: str,
    subtitle: str,
    href: str,
    group: str,
    group_label: str,
) -> dict[str, Any]:
    return {
        "id": id,
        "title": title,
        "subtitle": subtitle,
        "href": href,
        "group": group,
        "group_label": group_label,
    }


def _signup_review_href(signup_id: str, kyc_status: KycStatus) -> str:
    status = _kyc_status_value(kyc_status)
    return f"/dashboard/signup-review?signup={signup_id}&status={status}"


async def _search_kyc_signups(db: AsyncSession, needle: str, limit: int) -> list[dict[str, Any]]:
    q = (
        select(SignupRequest)
        .where(SignupRequest.email != "admin@zenk")
        .order_by(SignupRequest.created_at.desc())
        .limit(limit)
    )
    q = _signup_search_filter(q, needle)
    rows = list((await db.execute(q)).scalars().all())
    out: list[dict[str, Any]] = []
    for row in rows:
        status = KYC_STATUS_LABELS.get(row.kyc_status, row.kyc_status.value)
        out.append(
            _record(
                id=row.id,
                title=row.full_name,
                subtitle=f"{_display_role(row)} · {status} · {row.email}",
                href=_signup_review_href(row.id, row.kyc_status),
                group="kyc_signups",
                group_label="Signups",
            )
        )
    return _sort_records(out, needle)


async def _search_users(db: AsyncSession, needle: str, limit: int) -> list[dict[str, Any]]:
    q = (
        select(SignupRequest)
        .where(SignupRequest.email != "admin@zenk", SignupRequest.email != "kia@zenk.ai")
        .order_by(SignupRequest.created_at.desc())
        .limit(limit)
    )
    q = _signup_search_filter(q, needle)
    rows = list((await db.execute(q)).scalars().all())
    out: list[dict[str, Any]] = []
    for row in rows:
        persona = PERSONA_LABELS.get(row.persona, row.persona.value)
        out.append(
            _record(
                id=row.id,
                title=row.full_name,
                subtitle=f"{persona} · {row.email}",
                href=f"/dashboard/users?user={row.id}",
                group="users",
                group_label="Users",
            )
        )
    return _sort_records(out, needle)


async def _search_students(db: AsyncSession, needle: str, limit: int) -> list[dict[str, Any]]:
    q = (
        select(SignupRequest)
        .where(SignupRequest.persona == Persona.student)
        .order_by(SignupRequest.created_at.desc())
        .limit(limit)
    )
    q = _signup_search_filter(q, needle)
    rows = list((await db.execute(q)).scalars().all())
    out: list[dict[str, Any]] = []
    for row in rows:
        school = row.school_or_college_name or "School not set"
        status = KYC_STATUS_LABELS.get(row.kyc_status, row.kyc_status.value)
        out.append(
            _record(
                id=row.id,
                title=row.full_name,
                subtitle=f"{school} · {status}",
                href=f"/dashboard/student-progress?student={row.id}",
                group="students",
                group_label="Students",
            )
        )
    return _sort_records(out, needle)


async def _search_circles(db: AsyncSession, needle: str, limit: int) -> list[dict[str, Any]]:
    pattern = f"%{needle}%"
    name_q = (
        select(SponsorCircle)
        .where(SponsorCircle.name.ilike(pattern))
        .order_by(SponsorCircle.created_at.desc())
        .limit(limit)
    )
    name_rows = list((await db.execute(name_q)).scalars().all())

    leader_q = (
        select(SponsorCircle)
        .join(CircleMember, CircleMember.circle_id == SponsorCircle.id)
        .join(SignupRequest, SignupRequest.id == CircleMember.user_id)
        .where(
            CircleMember.role.in_(list(LEADER_ROLES)),
            SignupRequest.full_name.ilike(pattern),
        )
        .order_by(SponsorCircle.created_at.desc())
        .limit(limit)
    )
    leader_rows = list((await db.execute(leader_q)).scalars().all())

    seen: set[str] = set()
    circles: list[SponsorCircle] = []
    for row in name_rows + leader_rows:
        if row.id in seen:
            continue
        seen.add(row.id)
        circles.append(row)
        if len(circles) >= limit:
            break

    if not circles:
        return []

    circle_ids = [c.id for c in circles]
    leader_res = await db.execute(
        select(CircleMember.circle_id, SignupRequest.full_name)
        .join(SignupRequest, SignupRequest.id == CircleMember.user_id)
        .where(
            CircleMember.circle_id.in_(circle_ids),
            CircleMember.role.in_(list(LEADER_ROLES)),
        )
        .order_by(CircleMember.joined_at.asc())
    )
    leader_names: dict[str, str] = {}
    for cid, name in leader_res.all():
        leader_names.setdefault(cid, name)

    count_res = await db.execute(
        select(CircleMember.circle_id, func.count())
        .where(CircleMember.circle_id.in_(circle_ids))
        .group_by(CircleMember.circle_id)
    )
    member_counts = {cid: int(n) for cid, n in count_res.all()}

    out: list[dict[str, Any]] = []
    for circle in circles:
        leader = leader_names.get(circle.id) or "No leader"
        members = member_counts.get(circle.id, 0)
        status = (circle.status or "active").replace("_", " ").title()
        out.append(
            _record(
                id=circle.id,
                title=circle.name,
                subtitle=f"{leader} · {members} members · {status}",
                href=f"/dashboard/circle-ops?circle={circle.id}",
                group="circles",
                group_label="Circles",
            )
        )
    return _sort_records(out, needle)


async def _search_support(db: AsyncSession, needle: str, limit: int) -> list[dict[str, Any]]:
    rows = await list_support_contacts(db, search=needle, limit=limit)
    out: list[dict[str, Any]] = []
    for row in rows:
        preview = (row.get("last_message_text") or "No messages yet").strip()
        if len(preview) > 72:
            preview = preview[:69] + "…"
        out.append(
            _record(
                id=row["user_id"],
                title=row.get("user_name") or row.get("user_email") or "User",
                subtitle=f"{row.get('persona_label') or row.get('persona') or 'User'} · {preview}",
                href=f"/dashboard/support?user={row['user_id']}",
                group="support",
                group_label="Support inbox",
            )
        )
    return _sort_records(out, needle)


async def _search_website(db: AsyncSession, needle: str, limit: int) -> list[dict[str, Any]]:
    rows = await list_landing_contact_inquiries(db, search=needle, limit=limit)
    out: list[dict[str, Any]] = []
    for row in rows:
        interest = row.get("interest") or "General"
        out.append(
            _record(
                id=row["id"],
                title=row.get("name") or row.get("email") or "Website inquiry",
                subtitle=f"{row.get('email') or '—'} · {interest}",
                href=f"/dashboard/website-inquiries?id={row['id']}",
                group="website",
                group_label="Website queries",
            )
        )
    return _sort_records(out, needle)


async def _search_suppliers(db: AsyncSession, needle: str, limit: int) -> list[dict[str, Any]]:
    data = await build_admin_suppliers_registry(db, search=needle)
    out: list[dict[str, Any]] = []
    for row in (data.get("suppliers") or [])[:limit]:
        kind = "Vendor" if row.get("supplier_kind") == "vendor" else "School"
        out.append(
            _record(
                id=row["id"],
                title=row.get("name") or row.get("email") or kind,
                subtitle=f"{kind} · {row.get('status') or '—'} · {row.get('email') or '—'}",
                href=f"/dashboard/suppliers?supplier={row['id']}",
                group="suppliers",
                group_label="Suppliers",
            )
        )
    return _sort_records(out, needle)


async def _search_legal(db: AsyncSession, needle: str, limit: int) -> list[dict[str, Any]]:
    data = await list_legal_acceptances(db, search=needle, limit=limit, offset=0)
    out: list[dict[str, Any]] = []
    for row in (data.get("acceptances") or [])[:limit]:
        doc_label = DOC_TYPE_LABELS.get(row.get("doc_type"), row.get("doc_type") or "Legal")
        out.append(
            _record(
                id=row["id"],
                title=row.get("full_name") or row.get("email") or "Legal acceptance",
                subtitle=f"{doc_label} · {row.get('email') or '—'}",
                href=f"/dashboard/legal?acceptance={row['id']}",
                group="legal",
                group_label="Legal acceptances",
            )
        )
    return _sort_records(out, needle)


async def _search_sos(db: AsyncSession, needle: str, limit: int) -> list[dict[str, Any]]:
    pattern = f"%{needle}%"
    Reporter = aliased(GamifiedPersona)
    Sender = aliased(GamifiedPersona)
    stmt = (
        select(SOSReport, ChatMessage, Reporter, Sender)
        .join(ChatMessage, SOSReport.message_id == ChatMessage.id)
        .outerjoin(Reporter, SOSReport.reporter_persona_id == Reporter.id)
        .outerjoin(Sender, ChatMessage.gamified_persona_id == Sender.id)
        .where(
            or_(
                cast(SOSReport.id, String).ilike(pattern),
                ChatMessage.content_text.ilike(pattern),
                Reporter.nickname.ilike(pattern),
                Sender.nickname.ilike(pattern),
            )
        )
        .order_by(SOSReport.created_at.desc())
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()
    out: list[dict[str, Any]] = []
    for sos, msg, reporter, sender in rows:
        reporter_name = reporter.nickname if reporter else "Unknown reporter"
        preview = (msg.content_text or "").strip()
        if len(preview) > 72:
            preview = preview[:69] + "…"
        state = "Resolved" if sos.resolved_at else "Open"
        out.append(
            _record(
                id=sos.id,
                title=f"SOS · {reporter_name}",
                subtitle=f"{state} · {preview or 'No message text'}",
                href=f"/dashboard/report-queue?report={sos.id}",
                group="sos",
                group_label="SOS reports",
            )
        )
    return _sort_records(out, needle)


def _cache_get(key: tuple[str, int]) -> Optional[dict[str, Any]]:
    hit = _CACHE.get(key)
    if not hit:
        return None
    ts, payload = hit
    if time.monotonic() - ts > _CACHE_TTL_SEC:
        _CACHE.pop(key, None)
        return None
    return payload


def _cache_set(key: tuple[str, int], payload: dict[str, Any]) -> None:
    if len(_CACHE) >= _CACHE_MAX:
        oldest = min(_CACHE.items(), key=lambda item: item[1][0])[0]
        _CACHE.pop(oldest, None)
    _CACHE[key] = (time.monotonic(), payload)


async def run_admin_global_search(
    db: AsyncSession,
    *,
    query: str,
    limit_per_group: int = 5,
) -> dict[str, Any]:
    needle = (query or "").strip()
    if len(needle) < 2:
        return {"query": needle, "groups": []}

    limit = max(1, min(limit_per_group, 10))
    cache_key = (needle.lower(), limit)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    kyc = await _search_kyc_signups(db, needle, limit)
    users = await _search_users(db, needle, limit)
    students = await _search_students(db, needle, limit)
    circles = await _search_circles(db, needle, limit)
    support = await _search_support(db, needle, limit)
    website = await _search_website(db, needle, limit)
    suppliers = await _search_suppliers(db, needle, limit)
    legal = await _search_legal(db, needle, limit)
    sos = await _search_sos(db, needle, limit)

    groups: list[dict[str, Any]] = []
    for group_key, label, items in (
        ("kyc_signups", "Signups", kyc),
        ("users", "Users", users),
        ("students", "Students", students),
        ("circles", "Circles", circles),
        ("support", "Support inbox", support),
        ("website", "Website queries", website),
        ("suppliers", "Suppliers", suppliers),
        ("legal", "Legal acceptances", legal),
        ("sos", "SOS reports", sos),
    ):
        if items:
            groups.append({"type": group_key, "label": label, "items": items})

    result = {"query": needle, "groups": groups}
    _cache_set(cache_key, result)
    return result
