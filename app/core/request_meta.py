from __future__ import annotations

import os

from fastapi import Request


def get_client_ip(request: Request) -> tuple[str | None, str | None]:
    """Return (direct_client_ip, forwarded_ip_from_proxy)."""
    forwarded = request.headers.get("x-forwarded-for") or request.headers.get("X-Forwarded-For")
    forwarded_ip = None
    if forwarded:
        forwarded_ip = forwarded.split(",")[0].strip() or None
    direct = request.client.host if request.client else None
    return direct, forwarded_ip


def best_client_ip(request: Request) -> str | None:
    """Prefer public/proxy-forwarded IP for audit logs."""
    direct, forwarded_ip = get_client_ip(request)
    return forwarded_ip or direct


def _force_https_if_public_host(url: str) -> str:
    lowered = url.lower()
    if not lowered.startswith("http://"):
        return url
    if any(
        h in lowered
        for h in ("railway.app", "vercel.app", "zenkimpact", "zenk-fe")
    ):
        return "https://" + url[len("http://") :]
    return url


def public_api_base_url(request: Request) -> str:
    """
    Absolute API origin for share/OG links.

    Railway terminates TLS at the edge; request.base_url is often http://.
    Prefer PUBLIC_API_BASE_URL / X-Forwarded-* and force https for public hosts.
    """
    configured = (
        os.getenv("PUBLIC_API_BASE_URL")
        or os.getenv("VITE_API_BASE_URL")
        or ""
    ).strip().rstrip("/")
    if configured:
        return _force_https_if_public_host(configured)

    proto = (
        (request.headers.get("x-forwarded-proto") or request.url.scheme or "https")
        .split(",")[0]
        .strip()
        or "https"
    )
    host = (
        (request.headers.get("x-forwarded-host") or request.headers.get("host") or "")
        .split(",")[0]
        .strip()
    )
    if host:
        base = f"{proto}://{host}".rstrip("/")
        return _force_https_if_public_host(base)

    return _force_https_if_public_host(str(request.base_url).rstrip("/"))
