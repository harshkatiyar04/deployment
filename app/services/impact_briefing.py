"""
Impact Briefing — India education / charity headlines via RSS + Zenk circle insights.

Replaces the Guardian API (noisy, UK-heavy). External items come from Google News RSS
with strict topic filters; internal items are generated from real circle data.
"""

from __future__ import annotations

import logging
import re
import time
import xml.etree.ElementTree as ET
from html import unescape
from typing import Any, Optional

import httpx

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.models import SponsorCircle
from app.models.school import SchoolStudent, SchoolStudentEnrollmentRequest
from app.services.school_enrollment_constants import ENROLLMENT_PENDING
from app.services.sponsor_circle_finance import fetch_circle_orders

logger = logging.getLogger(__name__)

CACHE_TTL_SEC = 1800  # 30 min
_CACHE_VERSION = 1
_cache: dict[str, Any] = {"version": 0, "timestamp": 0.0, "items": []}

_HTML = re.compile(r"<[^>]+>")

# Google News RSS — India-focused education / giving (no API key)
RSS_FEEDS: tuple[tuple[str, str], ...] = (
    (
        "India Impact",
        "https://news.google.com/rss/search?q=India+education+charity+scholarship+donation+NGO&hl=en-IN&gl=IN&ceid=IN:en",
    ),
    (
        "CSR & Giving",
        "https://news.google.com/rss/search?q=India+CSR+philanthropy+school+fund+nonprofit&hl=en-IN&gl=IN&ceid=IN:en",
    ),
)

TOXIC = frozenset(
    {
        "cricket",
        "world cup",
        "t20",
        "football",
        "rugby",
        "tennis",
        "as it happened",
        "murder",
        "guilty of",
        "election",
        "trump",
        "starmer",
        "reform uk",
        "iran",
        "ukraine",
        "gaza",
        "air india crash",
        "stock to fund",
        "ai spending",
        "recipe",
        "film review",
        " review ",
        "obituary",
    }
)

IMPACT_TERMS = (
    "charity",
    "donat",
    "scholarship",
    "ngo",
    "nonprofit",
    "philanthrop",
    "csr",
    "fundraise",
    "literacy",
    "school",
    "student",
    "education",
    "enrollment",
    "dropout",
    "grant",
    "mid-day meal",
    "girl child",
    "rural",
    "underprivileged",
    "volunteer",
    "mentor",
)


def _clean_text(raw: str) -> str:
    text = unescape(_HTML.sub("", raw or ""))
    return re.sub(r"\s+", " ", text).strip()


def _is_relevant(title: str, summary: str) -> bool:
    combined = f"{title} {summary}".lower()
    if len(title) < 16:
        return False
    if any(t in combined for t in TOXIC):
        return False
    if "india" not in combined and "indian" not in combined:
        return False
    if not any(term in combined for term in IMPACT_TERMS):
        return False
    return True


def _categorize(combined: str) -> str:
    if any(w in combined for w in ("donat", "fundraise", "csr", "philanthrop", "grant")):
        return "Funding & CSR"
    if any(w in combined for w in ("scholarship", "endowment")):
        return "Scholarships"
    if any(w in combined for w in ("ngo", "nonprofit", "charity", "volunteer")):
        return "NGO & Community"
    return "Education Access"


def _parse_rss(xml_text: str, source_label: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return items

    for node in root.iter("item"):
        title = _clean_text(node.findtext("title") or "")
        link = (node.findtext("link") or "").strip()
        summary = _clean_text(node.findtext("description") or "")
        pub = (node.findtext("pubDate") or "").strip()
        if not _is_relevant(title, summary):
            continue
        combined = f"{title} {summary}".lower()
        items.append(
            {
                "id": link or title[:48],
                "text": title,
                "summary": summary[:300] if summary else title,
                "category": _categorize(combined),
                "source": source_label,
                "time": pub,
                "image": None,
                "url": link,
                "type": "EXTERNAL",
            }
        )
    return items


async def _fetch_rss(client: httpx.AsyncClient, label: str, url: str) -> list[dict]:
    try:
        resp = await client.get(url, follow_redirects=True)
        resp.raise_for_status()
        return _parse_rss(resp.text, label)
    except Exception as exc:
        logger.warning("RSS fetch failed %s: %s", label, exc)
        return []


async def build_platform_insights(
    db: AsyncSession,
    circle: SponsorCircle,
) -> list[dict[str, Any]]:
    """Real Zenk circle facts — always on-topic for sponsors."""
    insights: list[dict[str, Any]] = []
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    student_res = await db.execute(
        select(func.count(SchoolStudent.id)).where(SchoolStudent.circle_id == circle.id)
    )
    students = int(student_res.scalar() or 0)

    pending_res = await db.execute(
        select(func.count(SchoolStudentEnrollmentRequest.id)).where(
            SchoolStudentEnrollmentRequest.circle_id == circle.id,
            SchoolStudentEnrollmentRequest.status == ENROLLMENT_PENDING,
        )
    )
    pending = int(pending_res.scalar() or 0)

    orders = await fetch_circle_orders(db, circle)
    spent = sum(int(round(float(o.total_amount or 0))) for o, _ in orders)
    order_count = len(orders)

    if students > 0:
        insights.append(
            {
                "id": f"zenk-students-{circle.id}",
                "text": f"Your circle is uplifting {students} enrolled student{'s' if students != 1 else ''}.",
                "summary": "Live count from school enrollments linked to this sponsor circle.",
                "category": "Your Circle",
                "source": "Zenk Impact",
                "time": now,
                "image": None,
                "url": "",
                "type": "PLATFORM",
            }
        )

    if spent > 0:
        insights.append(
            {
                "id": f"zenk-spent-{circle.id}",
                "text": f"₹{spent:,} deployed across {order_count} marketplace order{'s' if order_count != 1 else ''}.",
                "summary": "Student-fund and circle orders recorded in your ledger — not estimates.",
                "category": "Your Circle",
                "source": "Zenk Impact",
                "time": now,
                "image": None,
                "url": "",
                "type": "PLATFORM",
            }
        )

    if pending > 0:
        insights.append(
            {
                "id": f"zenk-pending-{circle.id}",
                "text": f"{pending} school enrollment{'s' if pending != 1 else ''} awaiting circle review.",
                "summary": "Approve enrollments in School Comm to add students to your impact roster.",
                "category": "Action",
                "source": "Zenk Impact",
                "time": now,
                "image": None,
                "url": "",
                "type": "PLATFORM",
            }
        )

    if not insights:
        insights.append(
            {
                "id": f"zenk-start-{circle.id}",
                "text": "Start your impact journey: enroll students, set circle budget, and fund via marketplace.",
                "summary": "Briefing will fill in as your circle records real activity.",
                "category": "Getting Started",
                "source": "Zenk Impact",
                "time": now,
                "image": None,
                "url": "",
                "type": "PLATFORM",
            }
        )

    return insights[:3]


async def fetch_impact_briefing(
    *,
    force_refresh: bool = False,
    platform_insights: Optional[list[dict]] = None,
) -> dict[str, Any]:
    """External RSS (filtered) + optional platform insights passed in."""
    now = time.time()
    platform = platform_insights or []

    if (
        not force_refresh
        and _cache.get("version") == _CACHE_VERSION
        and _cache.get("items")
        and (now - float(_cache.get("timestamp") or 0)) < CACHE_TTL_SEC
    ):
        external = list(_cache["items"])
    else:
        external: list[dict] = []
        seen: set[str] = set()
        try:
            async with httpx.AsyncClient(timeout=8.0, headers={"User-Agent": "ZenkImpact/1.0"}) as client:
                for label, url in RSS_FEEDS:
                    for item in await _fetch_rss(client, label, url):
                        if item["id"] in seen:
                            continue
                        seen.add(item["id"])
                        external.append(item)
                        if len(external) >= 6:
                            break
                    if len(external) >= 6:
                        break
        except Exception as exc:
            logger.exception("Impact briefing RSS failed: %s", exc)

        if external:
            _cache["version"] = _CACHE_VERSION
            _cache["items"] = external
            _cache["timestamp"] = now

    combined = platform + external
    return {
        "status": "success" if combined else "unavailable",
        "items": combined,
        "external_count": len(external),
        "platform_count": len(platform),
        "cached": not force_refresh and bool(_cache.get("items")),
        "stale": False,
        "message": None if combined else "No briefing items right now. Circle insights appear once you have activity.",
    }


async def build_briefing_feed_for_circle(
    db: AsyncSession,
    circle: SponsorCircle,
    *,
    force_refresh: bool = False,
) -> dict[str, Any]:
    platform = await build_platform_insights(db, circle)
    payload = await fetch_impact_briefing(force_refresh=force_refresh, platform_insights=platform)
    return payload
