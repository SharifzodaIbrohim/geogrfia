"""
Database connection helper.
If DATABASE_URL is set → PostgreSQL.
Otherwise → None (server continues with JSON files).
"""
from __future__ import annotations

import os
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()

# Render / Heroku sometimes give postgres:// — SQLAlchemy needs postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

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
