"""Security response headers (CSP, clickjacking, MIME sniffing).

Uses pure ASGI middleware (not BaseHTTPMiddleware) so unhandled 500s still
pass through CORSMiddleware and keep Access-Control-Allow-Origin.
"""

from __future__ import annotations

import os

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

_SWAGGER_CDN = "https://cdn.jsdelivr.net"


def _is_api_docs_path(path: str) -> bool:
    return path in ("/docs", "/redoc", "/openapi.json") or path.startswith("/docs/")


def _csp_value(*, allow_swagger_cdn: bool = False) -> str:
    api = os.getenv("VITE_API_BASE_URL", "http://localhost:8000")
    railway = "https://deployment-production-27bd.up.railway.app"
    cloudinary = "https://res.cloudinary.com"
    script_src = "'self' 'unsafe-inline' 'unsafe-eval'"
    style_src = "'self' 'unsafe-inline'"
    if allow_swagger_cdn:
        script_src += f" {_SWAGGER_CDN}"
        style_src += f" {_SWAGGER_CDN}"
    return (
        "default-src 'self'; "
        "base-uri 'self'; "
        "frame-ancestors 'none'; "
        "form-action 'self'; "
        "object-src 'none'; "
        f"connect-src 'self' {api} {railway} ws://localhost:8000 wss://localhost:8000 "
        f"wss://*.railway.app https://*.railway.app https://*.vercel.app; "
        f"img-src 'self' data: blob: {cloudinary} https:; "
        f"style-src {style_src}; "
        "font-src 'self' data:; "
        f"script-src {script_src}; "
        "worker-src 'self' blob:;"
    )


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path") or ""
        scheme = scope.get("scheme") or "http"

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers.setdefault("X-Content-Type-Options", "nosniff")
                headers.setdefault("X-Frame-Options", "DENY")
                headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
                headers.setdefault(
                    "Permissions-Policy",
                    "camera=(), microphone=(), geolocation=(), payment=()",
                )
                headers.setdefault(
                    "Content-Security-Policy",
                    _csp_value(allow_swagger_cdn=_is_api_docs_path(path)),
                )
                if scheme == "https":
                    headers.setdefault(
                        "Strict-Transport-Security",
                        "max-age=31536000; includeSubDomains",
                    )
            await send(message)

        await self.app(scope, receive, send_with_headers)
