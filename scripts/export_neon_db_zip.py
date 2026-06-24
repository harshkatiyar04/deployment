"""
Read-only export of the Neon PostgreSQL database to a local .zip file.

- Uses NEON_DATABASE_URL from zenkimpact_BE/.env (falls back to DATABASE_URL).
- Only SELECT queries — nothing is written, updated, or deleted on Neon.
- Output: zenkimpact_BE/backups/neon_export_<timestamp>.zip
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import asyncpg

BE_ROOT = Path(__file__).resolve().parents[1]
BACKUPS_DIR = BE_ROOT / "backups"
ENV_FILE = BE_ROOT / ".env"

SYSTEM_SCHEMAS = frozenset(
    {"pg_catalog", "information_schema", "pg_toast", "pg_temp_1", "pg_toast_temp_1"}
)


def _load_env_value(key: str) -> str | None:
    if not ENV_FILE.exists():
        return os.environ.get(key)
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        if k.strip() == key:
            return v.strip().strip('"').strip("'")
    return os.environ.get(key)


def _resolve_database_url(explicit: str | None) -> str:
    url = explicit or _load_env_value("NEON_DATABASE_URL") or _load_env_value("DATABASE_URL")
    if not url:
        raise SystemExit(
            "No database URL found. Set NEON_DATABASE_URL in .env or pass --url."
        )
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    if not url.startswith("postgresql://"):
        raise SystemExit(f"Unsupported URL scheme: {url[:32]}...")
    return url


def _sql_literal(value) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, (bytes, bytearray, memoryview)):
        raw = bytes(value)
        return "'\\x" + raw.hex() + "'"
    if isinstance(value, (dict, list)):
        return "'" + json.dumps(value).replace("'", "''") + "'"
    if hasattr(value, "isoformat"):
        return "'" + value.isoformat().replace("'", "''") + "'"
    text = str(value).replace("'", "''")
    return f"'{text}'"


def _quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


async def _list_tables(conn: asyncpg.Connection) -> list[tuple[str, str]]:
    rows = await conn.fetch(
        """
        SELECT table_schema, table_name
        FROM information_schema.tables
        WHERE table_type = 'BASE TABLE'
          AND table_schema NOT LIKE 'pg_%'
          AND table_schema <> 'information_schema'
        ORDER BY table_schema, table_name
        """
    )
    return [(r["table_schema"], r["table_name"]) for r in rows]


async def _table_columns(conn: asyncpg.Connection, schema: str, table: str) -> list[str]:
    rows = await conn.fetch(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = $1 AND table_name = $2
        ORDER BY ordinal_position
        """,
        schema,
        table,
    )
    return [r["column_name"] for r in rows]


async def _export_table_sql(
    conn: asyncpg.Connection,
    schema: str,
    table: str,
    chunk_size: int = 500,
) -> tuple[str, int]:
    columns = await _table_columns(conn, schema, table)
    if not columns:
        return "", 0

    qualified = f"{_quote_ident(schema)}.{_quote_ident(table)}"
    col_list = ", ".join(_quote_ident(c) for c in columns)
    lines: list[str] = [
        f"-- Table: {schema}.{table}",
        f"-- Read-only export; restore with psql if needed.",
        "",
    ]
    row_count = 0
    offset = 0

    while True:
        rows = await conn.fetch(
            f"SELECT {col_list} FROM {qualified} ORDER BY 1 LIMIT $1 OFFSET $2",
            chunk_size,
            offset,
        )
        if not rows:
            break
        for row in rows:
            values = ", ".join(_sql_literal(row[c]) for c in columns)
            lines.append(f"INSERT INTO {qualified} ({col_list}) VALUES ({values});")
            row_count += 1
        offset += chunk_size

    lines.append("")
    return "\n".join(lines), row_count


async def export_neon_to_zip(
    database_url: str,
    output_zip: Path | None = None,
) -> Path:
    """Read-only export. Returns path to created zip."""
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    stamp_dir = BACKUPS_DIR / f"neon_export_{ts}"
    stamp_dir.mkdir(parents=True, exist_ok=True)

    if output_zip is None:
        output_zip = BACKUPS_DIR / f"neon_export_{ts}.zip"

    conn = await asyncpg.connect(database_url, ssl="require")
    try:
        db_name = await conn.fetchval("SELECT current_database()")
        pg_version = await conn.fetchval("SHOW server_version")
        tables = await _list_tables(conn)

        manifest = {
            "exported_at_utc": datetime.now(timezone.utc).isoformat(),
            "database": db_name,
            "postgres_version": pg_version,
            "mode": "read_only_select",
            "tables": [],
        }

        schema_sql_parts = [
            "-- ZENK Neon read-only export",
            f"-- Database: {db_name}",
            f"-- Exported at (UTC): {manifest['exported_at_utc']}",
            "-- No changes were made on the source database.",
            "",
            "BEGIN;",
            "",
        ]

        total_rows = 0
        for schema, table in tables:
            sql_body, count = await _export_table_sql(conn, schema, table)
            table_file = stamp_dir / "tables" / schema / f"{table}.sql"
            table_file.parent.mkdir(parents=True, exist_ok=True)
            table_file.write_text(sql_body, encoding="utf-8")
            schema_sql_parts.append(sql_body)
            manifest["tables"].append(
                {"schema": schema, "table": table, "rows": count}
            )
            total_rows += count
            print(f"  exported {schema}.{table}: {count} rows")

        manifest["total_rows"] = total_rows
        (stamp_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )

        full_sql = "\n".join(schema_sql_parts) + "\nCOMMIT;\n"
        (stamp_dir / "full_dump.sql").write_text(full_sql, encoding="utf-8")

        with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in sorted(stamp_dir.rglob("*")):
                if path.is_file():
                    arcname = path.relative_to(stamp_dir).as_posix()
                    zf.write(path, arcname)

        print(f"\nDone. {len(tables)} tables, {total_rows} rows.")
        print(f"Zip: {output_zip}")
        return output_zip
    finally:
        await conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Read-only Neon DB export to zip (no writes on source DB)."
    )
    parser.add_argument(
        "--url",
        help="Override connection URL (default: NEON_DATABASE_URL from .env)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        help="Output zip path (default: backups/neon_export_<timestamp>.zip)",
    )
    args = parser.parse_args()

    url = _resolve_database_url(args.url)
    host_hint = re.sub(r":[^@]+@", ":***@", url)
    print(f"Connecting (read-only): {host_hint}")
    print("No INSERT/UPDATE/DELETE will run on Neon.\n")

    asyncio.run(export_neon_to_zip(url, args.out))


if __name__ == "__main__":
    main()
