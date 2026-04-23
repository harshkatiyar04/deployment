from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.api.router import api_router
from app.db.init_db import init_db


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


@app.on_event("startup")
async def _startup() -> None:
    await init_db()


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(api_router)

# Trigger uvicorn hot-reload!
