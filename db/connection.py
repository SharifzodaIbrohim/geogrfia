"""
Database connection helper.
Production: DATABASE_URL required (PostgreSQL only).
Dev: JSON fallback when DATABASE_URL is unset.
"""
from __future__ import annotations

import os
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

_env = (os.environ.get("FLASK_ENV") or os.environ.get("ENV") or os.environ.get("APP_ENV") or "").strip().lower()
_is_prod = _env in ("production", "prod") or bool(os.environ.get("RENDER") or os.environ.get("DYNO"))
_allow_json = os.environ.get("ALLOW_JSON_BACKEND", "").strip() in ("1", "true", "yes")

if _is_prod and not DATABASE_URL and not _allow_json:
    raise RuntimeError(
        "DATABASE_URL is required in production. "
        "PostgreSQL is the only production backend. "
        "Set ALLOW_JSON_BACKEND=1 only for emergency recovery."
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


def is_postgres_enabled() -> bool:
    return bool(DATABASE_URL and engine is not None)


@contextmanager
def get_session():
    if not SessionLocal:
        raise RuntimeError("DATABASE_URL not set — PostgreSQL disabled")
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
        return {"backend": "json", "ok": True}
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"backend": "postgresql", "ok": True}
    except Exception as e:
        return {"backend": "postgresql", "ok": False, "error": str(e)}
