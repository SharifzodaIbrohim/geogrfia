"""
P0.6 — Versioned SQL migrations for Geografia.

Source of truth for schema evolution:
  migrations/001_*.sql
  migrations/002_*.sql
  ...

db/schema.sql remains the human-readable full baseline (documentation +
  bootstrap reference). Applied state is tracked ONLY in schema_migrations.

Usage:
  export DATABASE_URL=postgresql://...
  python -m db.migrate              # apply pending
  python -m db.migrate --status     # show applied / pending
  python -m db.migrate --dry-run    # print what would run

Boot (optional):
  from db.migrate import run_migrations
  run_migrations()  # safe, idempotent
"""
from __future__ import annotations

import argparse
import hashlib
import logging
import os
import re
import sys
from pathlib import Path

log = logging.getLogger("geografia.migrate")

ROOT = Path(__file__).resolve().parent.parent
MIGRATIONS_DIR = ROOT / "migrations"
SCHEMA_FILE = ROOT / "db" / "schema.sql"

VERSION_RE = re.compile(r"^(\d{3,})[_\-].+\.sql$", re.IGNORECASE)

TRACKING_DDL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
  version     TEXT PRIMARY KEY,
  name        TEXT NOT NULL,
  checksum    TEXT,
  applied_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


def _engine_from_env():
    url = (os.environ.get("DATABASE_URL") or "").strip()
    if not url:
        raise RuntimeError("DATABASE_URL is required for migrations")
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    from sqlalchemy import create_engine
    return create_engine(url, pool_pre_ping=True)


def _checksum(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]


def discover_migrations() -> list[dict]:
    """Return sorted list of {version, name, path, sql, checksum}."""
    if not MIGRATIONS_DIR.is_dir():
        return []
    found = []
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        m = VERSION_RE.match(path.name)
        if not m:
            log.warning("skip non-versioned file: %s", path.name)
            continue
        version = m.group(1)
        sql = path.read_text(encoding="utf-8")
        found.append({
            "version": version,
            "name": path.name,
            "path": path,
            "sql": sql,
            "checksum": _checksum(sql),
        })
    found.sort(key=lambda x: int(x["version"]))
    return found


def ensure_tracking(conn) -> None:
    from sqlalchemy import text
    conn.execute(text(TRACKING_DDL))
    conn.commit()


def applied_versions(conn) -> dict[str, dict]:
    from sqlalchemy import text
    ensure_tracking(conn)
    rows = conn.execute(text(
        "SELECT version, name, checksum, applied_at FROM schema_migrations ORDER BY version"
    )).mappings().all()
    return {
        r["version"]: {
            "name": r["name"],
            "checksum": r["checksum"],
            "applied_at": r["applied_at"],
        }
        for r in rows
    }


def _execute_script(conn, sql: str) -> None:
    """
    Run a multi-statement SQL script.

    Prefer the underlying DBAPI cursor so PostgreSQL receives the whole
    script (dollar-quotes, DO $$ blocks, etc.). Fall back to a comment-aware
    splitter + SQLAlchemy text() only if DBAPI path is unavailable.
    """
    # Strip UTF-8 BOM if present
    if sql.startswith("\ufeff"):
        sql = sql[1:]

    dbapi = None
    try:
        # SQLAlchemy 2 Connection
        dbapi = conn.connection.dbapi_connection
    except Exception:
        try:
            dbapi = conn.connection
        except Exception:
            dbapi = None

    if dbapi is not None and hasattr(dbapi, "cursor"):
        cur = dbapi.cursor()
        try:
            cur.execute(sql)
        finally:
            cur.close()
        return

    # Fallback: split safely then execute
    from sqlalchemy import text
    for stmt in _split_sql(sql):
        s = stmt.strip()
        if s:
            conn.execute(text(s))


def apply_one(conn, mig: dict, *, dry_run: bool = False) -> None:
    from sqlalchemy import text
    log.info("%s %s (%s)", "DRY" if dry_run else "APPLY", mig["version"], mig["name"])
    if dry_run:
        return
    _execute_script(conn, mig["sql"])
    conn.execute(
        text(
            "INSERT INTO schema_migrations (version, name, checksum) "
            "VALUES (:v, :n, :c) "
            "ON CONFLICT (version) DO UPDATE SET name = EXCLUDED.name, "
            "checksum = EXCLUDED.checksum, applied_at = now()"
        ),
        {"v": mig["version"], "n": mig["name"], "c": mig["checksum"]},
    )
    conn.commit()


def _strip_line_comments(script: str) -> str:
    """Remove -- line comments that are not inside quotes / dollar-quotes."""
    out: list[str] = []
    i = 0
    n = len(script)
    in_single = False
    dollar_tag: str | None = None
    while i < n:
        ch = script[i]
        if not in_single and dollar_tag is None and ch == "-" and i + 1 < n and script[i + 1] == "-":
            # skip until newline
            while i < n and script[i] not in ("\n", "\r"):
                i += 1
            continue
        if not in_single and script.startswith("$", i):
            m = re.match(r"\$([A-Za-z0-9_]*)\$", script[i:])
            if m:
                tag = m.group(0)
                if dollar_tag is None:
                    dollar_tag = tag
                elif tag == dollar_tag:
                    dollar_tag = None
                out.append(tag)
                i += len(tag)
                continue
        if dollar_tag is not None:
            out.append(ch)
            i += 1
            continue
        if ch == "'" and not in_single:
            in_single = True
            out.append(ch)
            i += 1
            continue
        if ch == "'" and in_single:
            if i + 1 < n and script[i + 1] == "'":
                out.append("''")
                i += 2
                continue
            in_single = False
            out.append(ch)
            i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _split_sql(script: str) -> list[str]:
    """Split on ';' outside of dollar-quotes and single quotes. Comments stripped first."""
    script = _strip_line_comments(script)
    parts: list[str] = []
    buf: list[str] = []
    i = 0
    n = len(script)
    in_single = False
    dollar_tag: str | None = None
    while i < n:
        ch = script[i]
        if not in_single and script.startswith("$", i):
            m = re.match(r"\$([A-Za-z0-9_]*)\$", script[i:])
            if m:
                tag = m.group(0)
                if dollar_tag is None:
                    dollar_tag = tag
                    buf.append(tag)
                    i += len(tag)
                    continue
                if tag == dollar_tag:
                    buf.append(tag)
                    i += len(tag)
                    dollar_tag = None
                    continue
        if dollar_tag is not None:
            buf.append(ch)
            i += 1
            continue
        if ch == "'" and not in_single:
            in_single = True
            buf.append(ch)
            i += 1
            continue
        if ch == "'" and in_single:
            if i + 1 < n and script[i + 1] == "'":
                buf.append("''")
                i += 2
                continue
            in_single = False
            buf.append(ch)
            i += 1
            continue
        if ch == ";" and not in_single:
            parts.append("".join(buf))
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    if buf:
        parts.append("".join(buf))
    return parts


def run_migrations(*, dry_run: bool = False, engine=None) -> dict:
    """
    Apply all pending migrations in order.
    Returns {applied: [...], pending: [...], already: [...], dry_run: bool}.
    """
    eng = engine or _engine_from_env()
    migrations = discover_migrations()
    result = {"applied": [], "pending": [], "already": [], "dry_run": dry_run}

    with eng.connect() as conn:
        applied = applied_versions(conn)
        for mig in migrations:
            ver = mig["version"]
            if ver in applied:
                prev = applied[ver]
                if prev.get("checksum") and prev["checksum"] != mig["checksum"]:
                    log.warning(
                        "checksum mismatch for %s (DB=%s file=%s) — not re-applied",
                        ver, prev["checksum"], mig["checksum"],
                    )
                result["already"].append(ver)
                continue
            result["pending"].append(ver)
            try:
                apply_one(conn, mig, dry_run=dry_run)
                if not dry_run:
                    result["applied"].append(ver)
            except Exception as e:
                log.error("migration %s failed: %s", ver, e)
                raise

    log.info(
        "migrations done: applied=%s pending_were=%s already=%s",
        result["applied"], result["pending"], result["already"],
    )
    return result


def status(*, engine=None) -> dict:
    eng = engine or _engine_from_env()
    migrations = discover_migrations()
    with eng.connect() as conn:
        applied = applied_versions(conn)
    rows = []
    for mig in migrations:
        ver = mig["version"]
        info = applied.get(ver)
        rows.append({
            "version": ver,
            "name": mig["name"],
            "status": "applied" if info else "pending",
            "applied_at": str(info["applied_at"]) if info else None,
            "checksum_ok": (
                info["checksum"] == mig["checksum"] if info and info.get("checksum") else None
            ),
        })
    return {
        "migrations": rows,
        "count_applied": sum(1 for r in rows if r["status"] == "applied"),
        "count_pending": sum(1 for r in rows if r["status"] == "pending"),
    }


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="[migrate] %(message)s")
    parser = argparse.ArgumentParser(description="Geografia versioned migrations")
    parser.add_argument("--status", action="store_true", help="Show applied/pending")
    parser.add_argument("--dry-run", action="store_true", help="Do not execute SQL")
    args = parser.parse_args(argv)

    if not os.environ.get("DATABASE_URL"):
        print("DATABASE_URL is not set", file=sys.stderr)
        return 2

    if args.status:
        st = status()
        for r in st["migrations"]:
            mark = "OK" if r["status"] == "applied" else "  "
            print(f"  [{mark}] {r['version']}  {r['name']}  {r['status']}")
        print(f"applied={st['count_applied']} pending={st['count_pending']}")
        return 0

    result = run_migrations(dry_run=args.dry_run)
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
