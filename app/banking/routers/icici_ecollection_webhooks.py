"""
ICICI eCollection MH7 webhooks — bank → ZenK.

UAT URLs (put in BRS):
  POST /webhooks/icici/ecollection/validate
  POST /webhooks/icici/ecollection/credit-confirm
"""

from __future__ import annotations

import logging
import secrets
from typing import Any, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import settings
from app.db.session import get_db
from app.banking.services import icici_ecollection as eco

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks/icici/ecollection", tags=["icici-ecollection"])


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for") or ""
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host or ""
    return ""


def _check_ip_allowlist(ip: str) -> None:
    raw = (settings.icici_ecollection_allowed_ips or "").strip()
    if not raw:
        return
    allowed = {x.strip() for x in raw.split(",") if x.strip()}
    if ip and ip not in allowed:
        # Also allow local / private for simulator
        if ip.startswith(("127.", "10.", "192.168.", "172.")) or ip in ("localhost", "::1"):
            return
        raise HTTPException(status_code=403, detail="IP not allowlisted")


def _check_basic_auth(authorization: Optional[str]) -> None:
    user = (settings.icici_ecollection_basic_user or "").strip()
    password = (settings.icici_ecollection_basic_password or "").strip()
    if not user and not password:
        return
    if not authorization or not authorization.lower().startswith("basic "):
        raise HTTPException(status_code=401, detail="Basic auth required", headers={"WWW-Authenticate": "Basic"})
    import base64

    try:
        decoded = base64.b64decode(authorization.split(" ", 1)[1].strip()).decode("utf-8")
        u, p = decoded.split(":", 1)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid basic auth") from exc
    if not (secrets.compare_digest(u, user) and secrets.compare_digest(p, password)):
        raise HTTPException(status_code=401, detail="Invalid credentials")


async def _parse_body(request: Request) -> dict[str, Any]:
    """
    Accept plaintext JSON for local/UAT simulator.
    Encrypted Apigee payload support lands after ICICI sample packets + key exchange.
    """
    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="JSON body required") from exc
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="JSON object required")

    if settings.icici_ecollection_plaintext:
        return body

    # Placeholder: when plaintext disabled, expect encrypted envelope later
    if "encryptedData" in body or "EncryptedData" in body:
        raise HTTPException(
            status_code=501,
            detail="Encrypted payload handling pending ICICI sample packet + keys",
        )
    # Soft allow plaintext until bank enables encryption on UAT
    return body


@router.post("/validate")
async def validate_credit(
    request: Request,
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(default=None),
):
    ip = _client_ip(request)
    _check_ip_allowlist(ip)
    _check_basic_auth(authorization)
    payload = await _parse_body(request)
    resp, status = await eco.handle_validation(db, payload, client_ip=ip)
    await db.commit()
    return resp


@router.post("/credit-confirm")
async def credit_confirm(
    request: Request,
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(default=None),
):
    ip = _client_ip(request)
    _check_ip_allowlist(ip)
    _check_basic_auth(authorization)
    payload = await _parse_body(request)
    resp, status = await eco.handle_credit_confirm(db, payload, client_ip=ip)
    await db.commit()
    return resp


@router.get("/health")
async def ecollection_health():
    return {
        "ok": True,
        "service": "icici-ecollection-mh7",
        "plaintext": bool(settings.icici_ecollection_plaintext),
        "client_code_configured": bool(settings.icici_ecollection_client_code),
    }
