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
    allow_origins=[
        "https://bdb9-117-213-200-3.ngrok-free.app",
        "https://969a-112-133-220-139.ngrok-free.app",
        "https://b895-112-133-220-139.ngrok-free.app",
        "https://0d61-112-133-220-139.ngrok-free.app",
        "http://localhost:5174",
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "*", # Allow all for ngrok testing
    ],  # Add your frontend URLs
    allow_credentials=True,
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

# Trigger uvicorn hot-reload


