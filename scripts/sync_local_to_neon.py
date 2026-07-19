"""
Pre-deploy DB sync: local Postgres -> Neon (ZENK + audit schemas).

Local is the source of truth for day-to-day work. Run this BEFORE every
Railway deploy / git push that needs production data to match local.

Usage (from zenkimpact_BE):
  .\\venv\\Scripts\\python.exe scripts\\sync_local_to_neon.py
  .\\venv\\Scripts\\python.exe scripts\\sync_local_to_neon.py --check   # compare only
  .\\sync-db-to-neon.ps1                                           # Windows wrapper

Requires: pg_dump + psql (PostgreSQL 16+ Windows install or on PATH).
Reads DATABASE_URL (local) and NEON_DATABASE_URL from .env.
Refuses Supabase URLs.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlparse

BE_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = BE_ROOT / ".env"
BACKUPS = BE_ROOT / "backups"
PG_BIN_CANDIDATES = [
    Path(r"C:\Program Files\PostgreSQL\18\bin"),
    Path(r"C:\Program Files\PostgreSQL\17\bin"),
    Path(r"C:\Program Files\PostgreSQL\16\bin"),
]

COMPARE_SQL = r"""
SELECT
  (SELECT count(*) FROM information_schema.tables WHERE table_schema = 'ZENK') AS zenk_tables,
  (SELECT count(*) FROM information_schema.tables WHERE table_schema = 'audit') AS audit_tables,
  (SELECT count(*) FROM "ZENK".signup_requests) AS signup_requests,
  (SELECT count(*) FROM "ZENK".sponsor_circles) AS sponsor_circles,
  (SELECT count(*) FROM "ZENK".chat_messages) AS chat_messages;
"""


def load_env(key: str) -> str | None:
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


def find_pg_bin() -> Path:
    for p in PG_BIN_CANDIDATES:
        if (p / "pg_dump.exe").exists():
            return p
    return Path(".")


def parse_url(url: str) -> dict:
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    u = urlparse(url)
    return {
        "host": u.hostname or "localhost",
        "port": str(u.port or 5432),
        "db": (u.path or "/").lstrip("/") or "postgres",
        "user": unquote(u.username or ""),
        "password": unquote(u.password or ""),
    }


def run(cmd: list[str], *, env: dict, check: bool = True) -> subprocess.CompletedProcess:
    print(">", " ".join(cmd[:6]), "...")
    return subprocess.run(cmd, env=env, check=check)


def fetch_snapshot(psql: str, url: str, *, ssl: bool) -> dict[str, int] | None:
    cfg = parse_url(url.replace("-pooler", "") if ssl else url)
    env = os.environ.copy()
    env["PGPASSWORD"] = cfg["password"]
    conn = (
        f"host={cfg['host']} port={cfg['port']} dbname={cfg['db']} "
        f"user={cfg['user']}"
    )
    if ssl:
        conn += " sslmode=require"
    r = subprocess.run(
        [psql, conn, "-t", "-A", "-F", "|", "-c", COMPARE_SQL],
        env=env,
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        print(f"  ERROR: {r.stderr.strip()[:400]}", file=sys.stderr)
        return None
    parts = r.stdout.strip().split("|")
    if len(parts) != 5:
        print(f"  ERROR: unexpected snapshot: {r.stdout!r}", file=sys.stderr)
        return None
    keys = ("zenk_tables", "audit_tables", "signup_requests", "sponsor_circles", "chat_messages")
    return {k: int(v) for k, v in zip(keys, parts)}


def print_snapshot(label: str, snap: dict[str, int]) -> None:
    print(
        f"  {label}: tables ZENK={snap['zenk_tables']} audit={snap['audit_tables']} | "
        f"signup={snap['signup_requests']} circles={snap['sponsor_circles']} "
        f"chat_msgs={snap['chat_messages']}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync local Postgres -> Neon before deploy.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Compare local vs Neon only (no dump/restore).",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompt (for CI / non-interactive).",
    )
    args = parser.parse_args()

    local_url = load_env("DATABASE_URL")
    neon_url = load_env("NEON_DATABASE_URL")
    if not local_url or not neon_url:
        print("Need DATABASE_URL and NEON_DATABASE_URL in .env", file=sys.stderr)
        return 1
    if "supabase" in neon_url.lower() or "supabase" in local_url.lower():
        print("Refusing to sync: a URL still points at Supabase.", file=sys.stderr)
        return 1
    if "localhost" not in local_url and "127.0.0.1" not in local_url:
        print(
            "Refusing: DATABASE_URL does not look local (expected localhost/127.0.0.1).",
            file=sys.stderr,
        )
        return 1
    if "neon.tech" not in neon_url.lower():
        print("Refusing: NEON_DATABASE_URL does not look like Neon.", file=sys.stderr)
        return 1

    pg = find_pg_bin()
    pg_dump = str(pg / "pg_dump.exe") if (pg / "pg_dump.exe").exists() else "pg_dump"
    psql = str(pg / "psql.exe") if (pg / "psql.exe").exists() else "psql"

    print("=== Pre-deploy DB sync: local -> Neon ===")
    print("Before:")
    local_before = fetch_snapshot(psql, local_url, ssl=False)
    neon_before = fetch_snapshot(psql, neon_url, ssl=True)
    if not local_before or not neon_before:
        return 1
    print_snapshot("LOCAL", local_before)
    print_snapshot("NEON ", neon_before)

    if args.check:
        same = local_before == neon_before
        print("Status:", "IN SYNC" if same else "OUT OF SYNC (run without --check to push local -> Neon)")
        return 0 if same else 2

    if not args.yes and sys.stdin.isatty():
        print()
        print("This OVERWRITES Neon ZENK + audit with your local DB.")
        ans = input("Continue? [y/N]: ").strip().lower()
        if ans not in ("y", "yes"):
            print("Aborted.")
            return 1

    local = parse_url(local_url)
    neon = parse_url(neon_url.replace("-pooler", ""))

    BACKUPS.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dump = BACKUPS / f"local_to_neon_{stamp}.sql"
    clean = BACKUPS / f"local_to_neon_{stamp}_clean.sql"
    log_path = BACKUPS / f"local_to_neon_resync_{stamp}.log"

    env = os.environ.copy()
    env["PGPASSWORD"] = local["password"]

    dump_cmd = [
        pg_dump,
        "-h", local["host"],
        "-p", local["port"],
        "-U", local["user"],
        "-d", local["db"],
        "--clean",
        "--if-exists",
        "--no-owner",
        "--no-acl",
        "-F", "p",
        "-f", str(dump),
        "-n", '"ZENK"',
        "-n", "audit",
    ]

    print()
    print(f"Dumping local {local['db']} -> {dump.name}")
    if sys.platform == "win32":
        cmd = (
            f'"{pg_dump}" -h {local["host"]} -p {local["port"]} -U {local["user"]} '
            f'-d {local["db"]} --clean --if-exists --no-owner --no-acl -F p '
            f'-f "{dump}" -n "\\"ZENK\\"" -n audit'
        )
        subprocess.run(cmd, env=env, check=True, shell=True)
    else:
        run(dump_cmd, env=env)

    lines = dump.read_text(encoding="utf-8", errors="replace").splitlines()
    cleaned = [
        ln
        for ln in lines
        if not ln.startswith("\\restrict ") and not ln.startswith("\\unrestrict ")
    ]
    clean.write_text("\n".join(cleaned) + "\n", encoding="utf-8")
    print(f"Wrote {clean.name} ({clean.stat().st_size} bytes)")

    env["PGPASSWORD"] = neon["password"]
    print(f"Restoring into Neon {neon['host']}/{neon['db']} (overwrites ZENK+audit)...")
    restore_cmd = [
        psql,
        f"host={neon['host']} port={neon['port']} dbname={neon['db']} user={neon['user']} sslmode=require",
        "-v",
        "ON_ERROR_STOP=1",
        "-f",
        str(clean),
    ]
    with log_path.open("w", encoding="utf-8") as logf:
        proc = subprocess.run(
            restore_cmd,
            env=env,
            check=False,
            stdout=logf,
            stderr=subprocess.STDOUT,
            text=True,
        )
    if proc.returncode != 0:
        print(f"Restore FAILED (exit {proc.returncode}). See {log_path}", file=sys.stderr)
        return 1

    print()
    print("After:")
    local_after = fetch_snapshot(psql, local_url, ssl=False)
    neon_after = fetch_snapshot(psql, neon_url, ssl=True)
    if not local_after or not neon_after:
        return 1
    print_snapshot("LOCAL", local_after)
    print_snapshot("NEON ", neon_after)

    if local_after != neon_after:
        print("WARNING: counts still differ after sync.", file=sys.stderr)
        print(f"Log: {log_path}")
        return 1

    print()
    print("OK: local and Neon are in sync. Safe to deploy (Railway must use Neon DATABASE_URL).")
    print(f"Log: {log_path}")
    return 0


if __name__ == "__main__":
    # Avoid Windows console crashes on unicode arrows in older code paths
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    raise SystemExit(main())
