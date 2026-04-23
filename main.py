from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import asyncio
import logging

from app.api.router import api_router
from app.db.init_db import init_db
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

app = FastAPI(title="ZENK BE")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("static/uploads", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


async def _keepalive_loop():
    """Ping the DB every 4 minutes to prevent Neon.tech free-tier sleep."""
    from sqlalchemy import text
    while True:
        await asyncio.sleep(4 * 60)  # 4 minutes
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
    logger.info("[Startup] DB keepalive task started.")


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(api_router)
