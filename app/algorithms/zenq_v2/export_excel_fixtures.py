"""Export Circles / Monthly Inputs sheets from the v2 Excel into JSON fixtures.

Usage (from zenkimpact_BE, with openpyxl installed optionally):
  python -m app.algorithms.zenq_v2.export_excel_fixtures

Falls back to writing a stub manifest if the workbook or openpyxl is unavailable.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
DEFAULT_XLSX = (
    Path(__file__).resolve().parents[4]
    / "docs"
    / "zenq-v2"
    / "ZenQ-v2-Final-10-Circle-Model.xlsx"
)


def _sheet_to_records(ws) -> list[dict]:
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []
    headers = [str(h).strip() if h is not None else f"col_{i}" for i, h in enumerate(rows[0])]
    out = []
    for row in rows[1:]:
        if all(c is None for c in row):
            continue
        out.append({headers[i]: row[i] for i in range(len(headers))})
    return out


def export(xlsx_path: Path | None = None) -> Path:
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    path = xlsx_path or DEFAULT_XLSX
    out_path = FIXTURE_DIR / "excel_circles_monthly.json"
    manifest = {
        "source": str(path),
        "exported": False,
        "sheets": {},
        "error": None,
    }
    if not path.is_file():
        manifest["error"] = f"workbook not found: {path}"
        out_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return out_path
    try:
        from openpyxl import load_workbook  # type: ignore
    except ImportError:
        manifest["error"] = "openpyxl not installed; pip install openpyxl to export"
        out_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return out_path

    wb = load_workbook(path, data_only=True, read_only=True)
    for name in wb.sheetnames:
        key = name.strip().lower().replace(" ", "_")
        if any(k in key for k in ("circle", "monthly", "input", "check", "market")):
            manifest["sheets"][name] = _sheet_to_records(wb[name])
    wb.close()
    manifest["exported"] = True
    out_path.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
    return out_path


def main() -> int:
    out = export()
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
