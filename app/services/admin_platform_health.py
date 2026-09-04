"""Platform health probes — full ops surface coverage for admin status page."""

from __future__ import annotations

import asyncio
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Optional, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import settings

logger = logging.getLogger(__name__)

STATUS_OPERATIONAL = "operational"
STATUS_DEGRADED = "degraded"
STATUS_OUTAGE = "outage"
STATUS_UNKNOWN = "unknown"

_STATUS_RANK = {
    STATUS_OPERATIONAL: 0,
    STATUS_UNKNOWN: 1,
    STATUS_DEGRADED: 2,
    STATUS_OUTAGE: 3,
}

_CLOUDINARY_PROBE = (
    "https://res.cloudinary.com/dhlmxyh9f/image/upload/w_32,c_limit,q_auto,f_auto/"
    "v1784295381/home_jfeco0.png"
)

# Mirror adminNavCatalog.js exactly — every sidebar Operations / Safety /
# Algorithms / Finance item gets its own probe row.
# tables = required schema; href = deep-link into admin UI.

_OPS_OPERATIONS: list[dict[str, Any]] = [
    {
        "id": "op_signup_kyc",
        "label": "Signup & KYC",
        "tables": ("signup_requests", "kyc_documents"),
        "href": "/dashboard/signup-review",
        "ok": "Signup queue + KYC documents schema ready",
    },
    {
        "id": "op_legal",
        "label": "Legal & terms",
        "tables": ("legal_documents", "legal_acceptances"),
        "href": "/dashboard/legal",
        "ok": "Legal documents + acceptances ready",
    },
    {
        "id": "op_circle_ops",
        "label": "Circle ops",
        "tables": ("sponsor_circles", "circle_members", "circle_admin_requests"),
        "href": "/dashboard/circle-ops",
        "ok": "Circles, members, and admin request queue ready",
    },
    {
        "id": "op_other_requests",
        "label": "Other requests",
        "tables": ("circle_admin_requests",),
        "href": "/dashboard/other-requests",
        "ok": "Admin request queue table ready",
    },
    {
        "id": "op_uplift",
        "label": "Uplift queue",
        "tables": ("mentor_uplift_actions",),
        "href": "/dashboard/uplift-queue",
        "ok": "Mentor uplift actions schema ready",
    },
    {
        "id": "op_users",
        "label": "Users",
        "tables": ("signup_requests", "refresh_tokens"),
        "href": "/dashboard/users",
        "ok": "User registry + session tokens ready",
    },
    {
        "id": "op_student_progress",
        "label": "Student progress",
        "tables": ("school_students", "school_zqa_snapshots", "school_reports"),
        "href": "/dashboard/student-progress",
        "ok": "School student + ZQA + reports ready",
    },
    {
        "id": "op_suppliers",
        "label": "Suppliers",
        "tables": ("vendor_products", "vendor_orders", "product_requests"),
        "href": "/dashboard/suppliers",
        "ok": "Vendor catalog + orders schema ready",
    },
    {
        "id": "op_support_inbox",
        "label": "Zenk Admin inbox",
        "tables": ("zenk_admin_threads", "zenk_admin_messages"),
        "href": "/dashboard/support",
        "ok": "Support threads + messages ready",
    },
    {
        "id": "op_website_queries",
        "label": "Website queries",
        "tables": ("landing_contact_inquiries", "landing_feedback_submissions"),
        "href": "/dashboard/website-inquiries",
        "ok": "Landing contact + feedback tables ready",
    },
]

_OPS_SAFETY: list[dict[str, Any]] = [
    {
        "id": "op_safety",
        "label": "Safety",
        "tables": ("chat_messages", "sos_reports", "chat_bans"),
        "href": "/dashboard/safety",
        "ok": "SOS + flagged chat + bans schema ready",
    },
    {
        "id": "op_sos",
        "label": "SOS reports",
        "tables": ("sos_reports",),
        "href": "/dashboard/report-queue",
        "ok": "SOS report queue ready",
    },
    {
        "id": "op_chat_bans",
        "label": "Chat bans",
        "tables": ("chat_bans",),
        "href": "/dashboard/chat-bans",
        "ok": "Chat bans table ready",
    },
]

_OPS_ALGORITHMS: list[dict[str, Any]] = [
    {
        "id": "op_zenq",
        "label": "ZenQ observatory",
        "tables": ("zenq_events", "zenq_sponsor_scores", "zenq_weight_config"),
        "href": "/dashboard/zenq-lab",
        "ok": "ZenQ events + scores + weights ready",
    },
]

_OPS_FINANCE: list[dict[str, Any]] = [
    {
        "id": "op_financial",
        "label": "Financial",
        "tables": ("circle_disbursements", "circle_finance_events", "ecollection_transactions"),
        "href": "/dashboard/financial",
        "ok": "Disbursements + finance events + eCollection ready",
    },
    {
        "id": "op_analytics",
        "label": "Analytics",
        "tables": ("signup_requests", "sponsor_circles", "vendor_orders"),
        "href": "/dashboard/analytics",
        "ok": "Core aggregates tables ready for analytics",
    },
]

_OPERATION_CHECKS: list[dict[str, Any]] = (
    _OPS_OPERATIONS + _OPS_SAFETY + _OPS_ALGORITHMS + _OPS_FINANCE
)

_PRODUCT_CHECKS: list[dict[str, Any]] = [
    {
        "id": "prod_student",
        "label": "Student dashboard",
        "tables": (
            "student_family_links",
            "parental_consent_log",
            "student_kia_messages",
            "gamified_personas",
        ),
        "href": "/student-dashboard",
        "ok": "Family hats, consent, Kia, personas ready",
    },
    {
        "id": "prod_parent",
        "label": "Parent / My Child",
        "tables": ("parent_academic_submissions", "student_family_links"),
        "href": "/sponsor-circle",
        "ok": "Parent academic submissions + family links ready",
    },
    {
        "id": "prod_school",
        "label": "School portal",
        "tables": (
            "school_profiles",
            "school_students",
            "school_portal_members",
            "school_portal_invites",
            "school_attendance",
        ),
        "href": "/school-dashboard",
        "ok": "School profile, students, RBAC, attendance ready",
    },
    {
        "id": "prod_sponsor_circle",
        "label": "Sponsor circle (member)",
        "tables": ("sponsor_circles", "circle_members", "enrollments", "chat_channels"),
        "href": "/sponsor-circle",
        "ok": "Circle membership + channels ready",
    },
    {
        "id": "prod_sponsor_leader",
        "label": "Sponsor circle (leader)",
        "tables": (
            "sponsor_circles",
            "circle_admin_requests",
            "circle_invite_tokens",
            "circle_payees",
        ),
        "href": "/sponsor-leader",
        "ok": "Leader ops, invites, payees ready",
    },
    {
        "id": "prod_chat",
        "label": "Chat & messaging",
        "tables": ("chat_channels", "chat_messages", "gamified_personas"),
        "href": "/dashboard/support",
        "ok": "Channels + messages + personas ready",
    },
    {
        "id": "prod_mentoring",
        "label": "Mentoring",
        "tables": (
            "mentor_profiles",
            "mentor_sessions",
            "student_mentoring_threads",
            "student_mentoring_messages",
        ),
        "href": "/mentor-dashboard",
        "ok": "Mentor profiles, sessions, student threads ready",
    },
    {
        "id": "prod_marketplace",
        "label": "Marketplace / vendor",
        "tables": ("vendor_products", "vendor_orders", "cart_items", "vendor_settings"),
        "href": "/dashboard/marketplace",
        "ok": "Products, orders, cart, vendor settings ready",
    },
    {
        "id": "prod_corporate",
        "label": "Corporate portal",
        "tables": ("corporate_profiles",),
        "href": "/corporate-dashboard",
        "ok": "Corporate profiles ready",
    },
    {
        "id": "prod_banking",
        "label": "Circle banking (eCollection)",
        "tables": ("ecollection_vans", "ecollection_transactions", "ecollection_events"),
        "href": "/dashboard/financial",
        "ok": "eCollection VAN + transactions + events ready",
    },
    {
        "id": "prod_notifications",
        "label": "Notifications",
        "tables": ("notifications",),
        "href": "/dashboard",
        "ok": "Notifications table ready",
    },
    {
        "id": "prod_onboarding",
        "label": "Student onboarding",
        "tables": (
            "student_school_interests",
            "student_circle_interest_requests",
            "student_school_referrals",
        ),
        "href": "/student-dashboard",
        "ok": "School/circle interest + referral tables ready",
    },
]

_CRITICAL_CORE_TABLES = (
    "signup_requests",
    "sponsor_circles",
    "circle_members",
    "student_family_links",
    "parental_consent_log",
)


def _cookie_secure_flag() -> bool:
    explicit = os.getenv("AUTH_COOKIE_SECURE", "").strip().lower()
    if explicit == "true":
        return True
    if explicit == "false":
        return False
    if os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_PROJECT_ID"):
        return True
    base = (settings.frontend_base_url or "").lower()
    return base.startswith("https://")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _check(
    *,
    id: str,
    label: str,
    status: str,
    detail: str,
    latency_ms: Optional[int] = None,
    href: Optional[str] = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": id,
        "label": label,
        "status": status,
        "detail": detail,
        "latency_ms": latency_ms,
        "checked_at": _utc_now_iso(),
    }
    if href:
        out["href"] = href
    return out


def _worst(*statuses: str) -> str:
    return max(statuses, key=lambda s: _STATUS_RANK.get(s, 0))


def _summary_for(overall: str) -> str:
    if overall == STATUS_OPERATIONAL:
        return "All systems operational"
    if overall == STATUS_DEGRADED:
        return "Some systems degraded"
    if overall == STATUS_OUTAGE:
        return "Outage detected — investigate immediately"
    return "Status unknown"


async def _load_zenk_tables(db: AsyncSession) -> set[str]:
    res = await db.execute(
        text(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'ZENK'
            """
        )
    )
    return {str(row[0]) for row in res.fetchall()}


def _probe_tables_cached(
    *,
    id: str,
    label: str,
    tables: Sequence[str],
    present: set[str],
    ok_detail: str,
    href: Optional[str] = None,
    latency_ms: int = 0,
) -> dict[str, Any]:
    missing = [t for t in tables if t not in present]
    if not missing:
        return _check(
            id=id,
            label=label,
            status=STATUS_OPERATIONAL,
            detail=ok_detail,
            latency_ms=latency_ms,
            href=href,
        )
    if len(missing) == len(tables):
        return _check(
            id=id,
            label=label,
            status=STATUS_OUTAGE,
            detail=f"Missing all tables: {', '.join(missing)}",
            latency_ms=latency_ms,
            href=href,
        )
    return _check(
        id=id,
        label=label,
        status=STATUS_DEGRADED,
        detail=f"Partial — missing: {', '.join(missing)}",
        latency_ms=latency_ms,
        href=href,
    )


async def _probe_api() -> dict[str, Any]:
    return _check(
        id="api",
        label="API gateway",
        status=STATUS_OPERATIONAL,
        detail="Process healthy",
        latency_ms=0,
        href="/dashboard/platform-health",
    )


async def _probe_database(db: AsyncSession) -> dict[str, Any]:
    t0 = time.perf_counter()
    try:
        await db.execute(text("SELECT 1"))
        ms = int((time.perf_counter() - t0) * 1000)
        status = STATUS_DEGRADED if ms > 1500 else STATUS_OPERATIONAL
        detail = f"SELECT 1 ok ({ms} ms)" if status == STATUS_OPERATIONAL else f"Slow response ({ms} ms)"
        return _check(
            id="database",
            label="Database (Neon)",
            status=status,
            detail=detail,
            latency_ms=ms,
        )
    except Exception as exc:  # noqa: BLE001
        ms = int((time.perf_counter() - t0) * 1000)
        logger.exception("platform_health_db_probe_failed")
        return _check(
            id="database",
            label="Database (Neon)",
            status=STATUS_OUTAGE,
            detail=f"DB probe failed: {type(exc).__name__}",
            latency_ms=ms,
        )


def _probe_auth_config() -> dict[str, Any]:
    secure = _cookie_secure_flag()
    fe = (settings.frontend_base_url or "").strip().rstrip("/")
    on_railway = bool(os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_PROJECT_ID"))

    if on_railway or secure:
        if not fe or "localhost" in fe.lower():
            return _check(
                id="auth_config",
                label="Auth / sessions",
                status=STATUS_DEGRADED,
                detail="FRONTEND_BASE_URL should be production Vercel URL for cookie/CORS",
                latency_ms=0,
            )
        if not secure:
            return _check(
                id="auth_config",
                label="Auth / sessions",
                status=STATUS_DEGRADED,
                detail="AUTH_COOKIE_SECURE should be true on Railway (SameSite=None)",
                latency_ms=0,
            )
        return _check(
            id="auth_config",
            label="Auth / sessions",
            status=STATUS_OPERATIONAL,
            detail=f"Cookie secure · FE={fe}",
            latency_ms=0,
        )

    return _check(
        id="auth_config",
        label="Auth / sessions",
        status=STATUS_OPERATIONAL,
        detail="Local cookie mode (Secure=false, SameSite=Lax)",
        latency_ms=0,
    )


def _probe_email() -> dict[str, Any]:
    if (settings.resend_api_key or "").strip():
        return _check(
            id="email",
            label="Email (Resend / SMTP)",
            status=STATUS_OPERATIONAL,
            detail="RESEND_API_KEY configured",
            latency_ms=0,
        )
    if settings.smtp_enabled and settings.smtp_host and settings.smtp_username:
        return _check(
            id="email",
            label="Email (Resend / SMTP)",
            status=STATUS_OPERATIONAL,
            detail=f"SMTP enabled via {settings.smtp_host}",
            latency_ms=0,
        )
    return _check(
        id="email",
        label="Email (Resend / SMTP)",
        status=STATUS_DEGRADED,
        detail="No Resend key and SMTP not fully configured — transactional mail may fail",
        latency_ms=0,
    )


def _probe_ai() -> dict[str, Any]:
    groq = bool((settings.groq_api_key or "").strip() or os.getenv("GROQ_API_KEY"))
    gemini = bool((settings.gemini_api_key or "").strip() or os.getenv("GEMINI_API_KEY"))
    if groq:
        return _check(
            id="ai",
            label="Kia AI keys",
            status=STATUS_OPERATIONAL,
            detail=f"Groq ready{' + Gemini set' if gemini else ''}",
            latency_ms=0,
        )
    if gemini:
        return _check(
            id="ai",
            label="Kia AI keys",
            status=STATUS_DEGRADED,
            detail="Gemini set but GROQ_API_KEY missing — Kia may be limited",
            latency_ms=0,
        )
    return _check(
        id="ai",
        label="Kia AI keys",
        status=STATUS_DEGRADED,
        detail="GROQ_API_KEY / GEMINI_API_KEY not set",
        latency_ms=0,
    )


def _probe_cloudinary_sync() -> dict[str, Any]:
    t0 = time.perf_counter()
    try:
        req = Request(_CLOUDINARY_PROBE, method="GET", headers={"User-Agent": "ZenK-Health/1.0"})
        with urlopen(req, timeout=5) as resp:
            code = getattr(resp, "status", 200)
            _ = resp.read(64)
        ms = int((time.perf_counter() - t0) * 1000)
        if 200 <= int(code) < 400:
            status = STATUS_DEGRADED if ms > 2500 else STATUS_OPERATIONAL
            return _check(
                id="cloudinary",
                label="Cloudinary CDN",
                status=status,
                detail=f"CDN reachable ({ms} ms)",
                latency_ms=ms,
            )
        return _check(
            id="cloudinary",
            label="Cloudinary CDN",
            status=STATUS_DEGRADED,
            detail=f"Unexpected HTTP {code}",
            latency_ms=ms,
        )
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        ms = int((time.perf_counter() - t0) * 1000)
        return _check(
            id="cloudinary",
            label="Cloudinary CDN",
            status=STATUS_DEGRADED,
            detail=f"CDN probe failed: {type(exc).__name__}",
            latency_ms=ms,
        )


def _probe_frontend_config() -> dict[str, Any]:
    fe = (settings.frontend_base_url or "").strip().rstrip("/")
    website = (settings.website_url or "").strip().rstrip("/")
    on_railway = bool(os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_PROJECT_ID"))
    if on_railway:
        if "vercel.app" in fe.lower() or "zenkimpact" in fe.lower():
            return _check(
                id="frontend_config",
                label="Frontend / CORS origin",
                status=STATUS_OPERATIONAL,
                detail=f"FRONTEND_BASE_URL={fe}",
                latency_ms=0,
            )
        return _check(
            id="frontend_config",
            label="Frontend / CORS origin",
            status=STATUS_DEGRADED,
            detail=f"Check FRONTEND_BASE_URL ({fe or 'unset'}) for Vercel",
            latency_ms=0,
        )
    return _check(
        id="frontend_config",
        label="Frontend / CORS origin",
        status=STATUS_OPERATIONAL,
        detail=f"Local FE={fe or 'localhost'} · site={website or '—'}",
        latency_ms=0,
    )


async def build_platform_health(db: AsyncSession) -> dict[str, Any]:
    started = time.perf_counter()

    api_c = await _probe_api()
    db_c = await _probe_database(db)

    t0 = time.perf_counter()
    try:
        present = await _load_zenk_tables(db)
        schema_ms = int((time.perf_counter() - t0) * 1000)
        schema_c = _probe_tables_cached(
            id="schema",
            label="Schema migrations (critical)",
            tables=_CRITICAL_CORE_TABLES,
            present=present,
            ok_detail=f"Critical tables present ({len(present)} ZENK tables indexed)",
            latency_ms=schema_ms,
        )
    except Exception as exc:  # noqa: BLE001
        present = set()
        schema_ms = int((time.perf_counter() - t0) * 1000)
        schema_c = _check(
            id="schema",
            label="Schema migrations (critical)",
            status=STATUS_UNKNOWN,
            detail=f"Could not list ZENK tables: {type(exc).__name__}",
            latency_ms=schema_ms,
        )

    auth_c = _probe_auth_config()
    fe_c = _probe_frontend_config()

    def _checks_for(specs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            _probe_tables_cached(
                id=spec["id"],
                label=spec["label"],
                tables=spec["tables"],
                present=present,
                ok_detail=spec["ok"],
                href=spec.get("href"),
                latency_ms=0,
            )
            for spec in specs
        ]

    product_checks = _checks_for(_PRODUCT_CHECKS)

    email_c = _probe_email()
    ai_c = _probe_ai()
    cloudinary_c = await asyncio.to_thread(_probe_cloudinary_sync)

    groups = [
        {
            "id": "core",
            "label": "Core platform",
            "checks": [api_c, db_c, auth_c, fe_c, schema_c],
        },
        {
            "id": "operations",
            "label": "Operations",
            "checks": _checks_for(_OPS_OPERATIONS),
        },
        {
            "id": "safety",
            "label": "Safety & trust",
            "checks": _checks_for(_OPS_SAFETY),
        },
        {
            "id": "algorithms",
            "label": "Algorithms",
            "checks": _checks_for(_OPS_ALGORITHMS),
        },
        {
            "id": "finance",
            "label": "Finance & insights",
            "checks": _checks_for(_OPS_FINANCE),
        },
        {
            "id": "products",
            "label": "Product portals",
            "checks": product_checks,
        },
        {
            "id": "deps",
            "label": "Dependencies",
            "checks": [email_c, ai_c, cloudinary_c],
        },
    ]

    all_statuses = [c["status"] for g in groups for c in g["checks"]]
    overall = _worst(*all_statuses) if all_statuses else STATUS_UNKNOWN
    checked_in_ms = int((time.perf_counter() - started) * 1000)

    return {
        "generated_at": _utc_now_iso(),
        "overall": overall,
        "summary": _summary_for(overall),
        "checked_in_ms": checked_in_ms,
        "groups": groups,
        "incidents": [],
    }
