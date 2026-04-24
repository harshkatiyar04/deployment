from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import asyncio
import logging

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.api.router import api_router
from app.db.init_db import init_db
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

# ── Startup Security Guard ────────────────────────────────────────────────────
# Crash LOUDLY if the SECRET_KEY is the insecure default.
# This prevents accidental deployment with a forgeable JWT secret.
from app.core.jwt_auth import jwt_settings  # noqa: E402
_INSECURE_DEFAULTS = {"changeme-insecure-default", "secret", "password", ""}
if jwt_settings.secret_key in _INSECURE_DEFAULTS:
    raise RuntimeError(
        " SECURITY ERROR: SECRET_KEY is not set or is using an insecure default. "
        "Set a strong SECRET_KEY environment variable before starting the server."
    )

# ── Rate Limiter ──────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])

app = FastAPI(title="ZENK BE")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ──────────────────────────────────────────────────────────────────────
# Locked to known production + dev origins only
ALLOWED_ORIGINS = [
    "https://zenk-impact.vercel.app",
    "https://zenk-fe.vercel.app",
    "https://zenkimpact.vercel.app",
    # Allow all vercel preview deployments for this project
    "https://zenk-fe-git-main-alphah-devs-projects.vercel.app",
    # Local development
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

os.makedirs("static/uploads", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


async def _keepalive_loop():
    """Ping the DB every 4 minutes to prevent Neon.tech free-tier sleep."""
    from sqlalchemy import text
    while True:
        await asyncio.sleep(4 * 60)
        try:
            async with SessionLocal() as session:
                await session.execute(text("SELECT 1"))
            logger.info("[Keepalive] DB ping successful.")
        except Exception as e:
            logger.warning(f"[Keepalive] DB ping failed: {e}")


@app.on_event("startup")
async def _startup() -> None:
    await init_db()
    asyncio.create_task(_keepalive_loop())
    logger.info("[Startup] Server ready. DB keepalive task started.")


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(api_router)
