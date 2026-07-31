"""Security response headers (CSP, clickjacking, MIME sniffing)."""

from __future__ import annotations

import logging
import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

_SWAGGER_CDN = "https://cdn.jsdelivr.net"
logger = logging.getLogger(__name__)


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


def _apply_security_headers(request: Request, response: Response) -> Response:
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault(
        "Permissions-Policy",
        "camera=(), microphone=(), geolocation=(), payment=()",
    )
    response.headers.setdefault(
        "Content-Security-Policy",
        _csp_value(allow_swagger_cdn=_is_api_docs_path(request.url.path)),
    )
    if request.url.scheme == "https":
        response.headers.setdefault(
            "Strict-Transport-Security",
            "max-age=31536000; includeSubDomains",
        )
    return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        try:
            response = await call_next(request)
        except Exception as exc:
            # BaseHTTPMiddleware + re-raise drops CORS headers in the browser.
            # Convert to a Response so CORSMiddleware can still attach ACAO.
            from app.db.resilience import is_stale_plan_error, safe_service_unavailable_detail

            if is_stale_plan_error(exc):
                try:
                    from app.db.session import reset_db_pool

                    await reset_db_pool()
                except Exception:
                    logger.exception("Failed to reset DB pool after stale plan error")
                logger.warning(
                    "Stale DB plan after schema change; pool reset. detail=%s",
                    type(exc).__name__,
                )
                response = JSONResponse(
                    {"detail": safe_service_unavailable_detail()},
                    status_code=503,
                )
            else:
                logger.exception("Unhandled error in request path")
                response = JSONResponse(
                    {"detail": "Internal server error"},
                    status_code=500,
                )
        return _apply_security_headers(request, response)
