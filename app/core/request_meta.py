from __future__ import annotations

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
