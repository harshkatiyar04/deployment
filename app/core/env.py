from __future__ import annotations

from pathlib import Path


def get_env_file() -> str | None:
    """
    Return the first existing .env file path from known locations.

    Supported locations (in order):
    1) Project root: <BE>/.env
    2) Venv folder:  <BE>/ZENK/.env
    """
    be_root = Path(__file__).resolve().parents[2]  # .../BE
    candidates = [
        be_root / ".env",
        be_root / "ZENK" / ".env",
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return None


