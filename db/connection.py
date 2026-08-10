"""
Database connection helper — Phase 25.5 / P0.5

Production:
  - DATABASE_URL is mandatory
  - PostgreSQL is the only backend
  - JSON fallback is OFF unless ALLOW_JSON_BACKEND=1 (emergency only)

Local/dev:
  - Without DATABASE_URL → JSON files (dev convenience)
"""
from __future__ import annotations

import logging
import os
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

log = logging.getLogger("geografia.db")

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()

# Render / Heroku sometimes give postgres:// — SQLAlchemy needs postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

_env = (
    os.environ.get("FLASK_ENV")
    or os.environ.get("ENV")
    or os.environ.get("APP_ENV")
    or ""
).strip().lower()
_is_prod = _env in ("production", "prod") or bool(
    os.environ.get("RENDER") or os.environ.get("DYNO")
)
# Explicit opt-in JSON for emergency recovery only
_allow_json = os.environ.get("ALLOW_JSON_BACKEND", "").strip().lower() in (
    "1",
    "true",
    "yes",
)

if _is_prod and not DATABASE_URL and not _allow_json:
    raise RuntimeError(
        "DATABASE_URL is required in production. "
        "PostgreSQL is the only production backend. "
        "Set ALLOW_JSON_BACKEND=1 only for emergency recovery."
    )

if _is_prod and _allow_json and not DATABASE_URL:
    log.warning(
        "ALLOW_JSON_BACKEND=1 in production — JSON emergency mode. "
        "Do not use this permanently."
    )

engine = None
SessionLocal = None

if DATABASE_URL:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    log.info("PostgreSQL engine configured")
elif not _is_prod:
    log.info("No DATABASE_URL — JSON backend (dev only)")


def is_production() -> bool:
    return _is_prod


def is_postgres_enabled() -> bool:
    """True when DATABASE_URL is configured (engine created)."""
    return bool(DATABASE_URL and engine is not None)


def json_backend_allowed() -> bool:
    """JSON file backend is allowed only outside prod, or with emergency flag."""
    if is_postgres_enabled():
        return False  # PG configured → never prefer JSON
    if _is_prod:
        return _allow_json
    return True


@contextmanager
def get_session():
    if not SessionLocal:
        raise RuntimeError(
            "DATABASE_URL not set — PostgreSQL disabled. "
            "In production set DATABASE_URL; for local JSON use without this call."
        )
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def health_check() -> dict:
    if not is_postgres_enabled():
        return {
            "backend": "json",
            "ok": bool(json_backend_allowed()),
            "production": _is_prod,
            "jsonAllowed": json_backend_allowed(),
        }
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {
            "backend": "postgresql",
            "ok": True,
            "production": _is_prod,
            "jsonAllowed": False,
        }
    except Exception as e:
        # In production do not claim JSON is a healthy alternative
        return {
            "backend": "postgresql",
            "ok": False,
            "error": str(e),
            "production": _is_prod,
            "jsonAllowed": False,
        }
