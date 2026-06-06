"""Fail CI/local pre-push if main:app cannot be imported. Run from zenkimpact_BE root."""
from __future__ import annotations

import sys
from pathlib import Path

_BE_ROOT = Path(__file__).resolve().parents[1]
if str(_BE_ROOT) not in sys.path:
    sys.path.insert(0, str(_BE_ROOT))


def main() -> int:
    try:
        from main import app  # noqa: F401
    except Exception as exc:
        print(f"IMPORT FAILED: {exc}", file=sys.stderr)
        return 1
    print("import OK:", getattr(app, "title", app))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
