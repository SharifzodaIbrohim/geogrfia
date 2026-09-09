"""
Bootstrap for empty PostgreSQL (e.g. new Neon DB):
  1) Run pending versioned migrations
  2) If admins table has zero rows, create one super_admin

Credentials (defaults):
  login:    admin
  password: Admin@2026

Override via env (recommended after first login):
  BOOTSTRAP_ADMIN_LOGIN
  BOOTSTRAP_ADMIN_PASSWORD
  BOOTSTRAP_ADMIN_NAME

Safe to call on every boot — only inserts when count(admins) == 0.
"""
from __future__ import annotations

import hashlib
import logging
import os
import secrets
import uuid

log = logging.getLogger("geografia.bootstrap")

DEFAULT_LOGIN = "admin"
DEFAULT_PASSWORD = "Admin@2026"
DEFAULT_NAME = "Админи асосӣ"
PBKDF2_ROUNDS = 120_000


def _hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    if not salt:
        salt = secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        PBKDF2_ROUNDS,
    ).hex()
    return salt, password_hash


def _run_migrations() -> None:
    try:
        from db.migrate import run_migrations
        result = run_migrations()
        log.info(
            "bootstrap migrations: applied=%s already=%s",
            result.get("applied"),
            result.get("already"),
        )
        print(
            f"[boot] migrations applied={result.get('applied')} "
            f"already={len(result.get('already') or [])}"
        )
    except Exception as e:
        log.exception("bootstrap migrations failed: %s", e)
        print(f"[boot] migrations failed: {e}")
        raise


def _admin_count(conn) -> int:
    from sqlalchemy import text
    row = conn.execute(text("SELECT COUNT(*) AS c FROM admins")).mappings().first()
    return int(row["c"] if row else 0)


def _seed_admin(conn) -> dict | None:
    from sqlalchemy import text

    login = (os.environ.get("BOOTSTRAP_ADMIN_LOGIN") or DEFAULT_LOGIN).strip() or DEFAULT_LOGIN
    password = (os.environ.get("BOOTSTRAP_ADMIN_PASSWORD") or DEFAULT_PASSWORD).strip() or DEFAULT_PASSWORD
    name = (os.environ.get("BOOTSTRAP_ADMIN_NAME") or DEFAULT_NAME).strip() or DEFAULT_NAME

    # Never seed if any admin already exists
    if _admin_count(conn) > 0:
        print("[boot] bootstrap: admins already present — skip seed")
        return None

    salt, password_hash = _hash_password(password)
    aid = str(uuid.uuid4())
    conn.execute(
        text(
            "INSERT INTO admins (id, login, name, salt, password_hash, role, status, created_by) "
            "VALUES (CAST(:id AS uuid), :login, :name, :salt, :ph, 'super_admin', 'active', 'bootstrap')"
        ),
        {"id": aid, "login": login, "name": name, "salt": salt, "ph": password_hash},
    )
    conn.commit()
    print(f"[boot] bootstrap: super_admin created login={login!r} id={aid}")
    log.info("bootstrap admin created login=%s id=%s", login, aid)
    return {"id": aid, "login": login, "name": name}


def install_bootstrap() -> None:
    """Call once at process boot after Flask app is loaded."""
    url = (os.environ.get("DATABASE_URL") or "").strip()
    if not url:
        print("[boot] bootstrap: no DATABASE_URL — skip")
        return

    # 1) schema
    _run_migrations()

    # 2) seed admin if empty
    try:
        from db.connection import engine
        if engine is None:
            from sqlalchemy import create_engine
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql://", 1)
            eng = create_engine(url, pool_pre_ping=True)
        else:
            eng = engine
        with eng.connect() as conn:
            try:
                _seed_admin(conn)
            except Exception as e:
                log.exception("bootstrap seed failed: %s", e)
                print(f"[boot] bootstrap seed failed: {e}")
                raise
    except Exception as e:
        print(f"[boot] bootstrap install failed: {e}")
        log.exception("bootstrap install failed")
        return
