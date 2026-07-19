"""Protect Swagger / ReDoc / OpenAPI when ENABLE_API_DOCS=true."""

from __future__ import annotations

import base64
import secrets
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.settings import settings


def is_api_docs_path(path: str) -> bool:
    return path in ("/docs", "/redoc", "/openapi.json") or path.startswith(
        ("/docs/", "/redoc/")
    )


def _authorized(username: str, password: str) -> bool:
    expected_user = (settings.admin_email or "admin@zenk").strip()
    expected_pass = (settings.admin_password or "").strip()
    api_key = (settings.admin_api_key or "").strip()

    if expected_pass and secrets.compare_digest(username.strip(), expected_user):
        if secrets.compare_digest(password, expected_pass):
            return True

    # Scripts / alternate: any username + ZENK_ADMIN_API_KEY as password
    if api_key and secrets.compare_digest(password, api_key):
        return True

    return False


def _parse_basic(authorization: Optional[str]) -> tuple[str, str] | None:
    if not authorization or not authorization.lower().startswith("basic "):
        return None
    try:
        raw = base64.b64decode(authorization.split(" ", 1)[1].strip()).decode("utf-8")
    except Exception:
        return None
    if ":" not in raw:
        return None
    user, password = raw.split(":", 1)
    return user, password


class DocsAuthMiddleware(BaseHTTPMiddleware):
    """HTTP Basic Auth for /docs, /redoc, and /openapi.json."""

    async def dispatch(self, request: Request, call_next) -> Response:
        if not is_api_docs_path(request.url.path):
            return await call_next(request)

        parsed = _parse_basic(request.headers.get("authorization"))
        if parsed and _authorized(parsed[0], parsed[1]):
            return await call_next(request)

        return Response(
            content="Authentication required for API docs.",
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="ZENK API Docs"'},
            media_type="text/plain",
        )
