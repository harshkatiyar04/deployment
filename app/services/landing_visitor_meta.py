"""Capture IP, device, UTM, and approximate geo for landing visitors."""

from __future__ import annotations

import logging
from typing import Any, Optional

import httpx
from fastapi import Request

from app.core.request_meta import best_client_ip

logger = logging.getLogger(__name__)

_PRIVATE_PREFIXES = ("127.", "10.", "192.168.", "172.16.", "172.17.", "172.18.", "172.19.",
                     "172.2", "172.30.", "172.31.", "::1", "fc", "fd", "localhost")


def _is_probably_private(ip: Optional[str]) -> bool:
    if not ip:
        return True
    low = ip.lower().strip()
    return any(low.startswith(p) for p in _PRIVATE_PREFIXES)


_EMPTY_GEO = {"geo_country": None, "geo_region": None, "geo_city": None}


async def _query_ip_api(ip: Optional[str]) -> dict[str, Optional[str]]:
    """Call ip-api. Empty `ip` resolves the caller's own public IP."""
    try:
        target = "" if not ip else ip
        async with httpx.AsyncClient(timeout=2.5) as client:
            res = await client.get(
                f"http://ip-api.com/json/{target}",
                params={"fields": "status,country,regionName,city,query"},
            )
        if res.status_code != 200:
            return dict(_EMPTY_GEO)
        data = res.json()
        if data.get("status") != "success":
            return dict(_EMPTY_GEO)
        return {
            "geo_country": (data.get("country") or None),
            "geo_region": (data.get("regionName") or None),
            "geo_city": (data.get("city") or None),
        }
    except Exception:
        logger.debug("Geo lookup failed for ip=%s", ip, exc_info=True)
        return dict(_EMPTY_GEO)


async def lookup_geo_from_ip(ip: Optional[str]) -> dict[str, Optional[str]]:
    """Best-effort city/region/country. Never raises; empty on failure.

    When the client IP is private/localhost (local dev, or a proxy that did not
    forward the real IP), fall back to resolving the server's own public IP so
    the record still shows an approximate location instead of "unknown".
    """
    if _is_probably_private(ip):
        return await _query_ip_api(None)
    return await _query_ip_api(ip)


def _clip(value: Any, max_len: int) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text[:max_len]


async def collect_visitor_meta(
    request: Request,
    *,
    client_meta: Optional[dict[str, Any]] = None,
) -> dict[str, Optional[str]]:
    """Merge request headers with optional browser-reported fields + geo."""
    client_meta = client_meta or {}
    ip = best_client_ip(request)

    # Prefer Cloudflare country when present (no extra hop).
    cf_country = _clip(request.headers.get("cf-ipcountry"), 80)
    geo = await lookup_geo_from_ip(ip)
    if cf_country and cf_country.upper() not in ("XX", "T1"):
        geo["geo_country"] = geo["geo_country"] or cf_country

    return {
        "session_id": _clip(client_meta.get("session_id"), 64),
        "ip_address": _clip(ip, 64),
        "user_agent": _clip(
            client_meta.get("user_agent") or request.headers.get("user-agent"), 2000
        ),
        "accept_language": _clip(request.headers.get("accept-language"), 120),
        "referrer": _clip(client_meta.get("referrer"), 2000),
        "landing_path": _clip(client_meta.get("landing_path"), 500),
        "utm_source": _clip(client_meta.get("utm_source"), 120),
        "utm_medium": _clip(client_meta.get("utm_medium"), 120),
        "utm_campaign": _clip(client_meta.get("utm_campaign"), 120),
        "timezone": _clip(client_meta.get("timezone"), 80),
        "screen": _clip(client_meta.get("screen"), 40),
        **geo,
    }
