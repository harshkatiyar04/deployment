"""Security response headers (CSP, clickjacking, MIME sniffing)."""

from __future__ import annotations

import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


def _csp_value() -> str:
    api = os.getenv("VITE_API_BASE_URL", "http://localhost:8000")
    railway = "https://deployment-production-27bd.up.railway.app"
    cloudinary = "https://res.cloudinary.com"
    return (
        "default-src 'self'; "
        "base-uri 'self'; "
        "frame-ancestors 'none'; "
        "form-action 'self'; "
        "object-src 'none'; "
        f"connect-src 'self' {api} {railway} ws://localhost:8000 wss://localhost:8000 "
        f"wss://*.railway.app https://*.railway.app https://*.vercel.app; "
        f"img-src 'self' data: blob: {cloudinary} https:; "
        "style-src 'self' 'unsafe-inline'; "
        "font-src 'self' data:; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "worker-src 'self' blob:;"
    )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=(), payment=()",
        )
        response.headers.setdefault("Content-Security-Policy", _csp_value())
        if request.url.scheme == "https":
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        return response
