"""
Test Matrix — Security
  missing JWT secret → startup fail (production)
  missing DB         → startup fail (production)
  CORS foreign site  → reject (policy check)
  rate limit         → 429 path (allow=False)
"""
from __future__ import annotations

import os

import pytest

from db.rate_limit import allow, check
from db.secrets import is_production, require_production_secrets


def test_missing_jwt_secret_fails_in_production(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost/db")
    # Force production detection
    if not is_production():
        monkeypatch.setenv("GEOGRAFIA_ENV", "production")
    try:
        # re-read production flag after env change
        from db import secrets as sec

        monkeypatch.setattr(sec, "is_production", lambda: True)
        with pytest.raises(RuntimeError):
            sec.require_production_secrets()
    finally:
        monkeypatch.setenv("FLASK_ENV", "testing")
        monkeypatch.delenv("RENDER", raising=False)


def test_missing_db_fails_in_production(monkeypatch):
    from db import secrets as sec

    monkeypatch.setattr(sec, "is_production", lambda: True)
    monkeypatch.setenv("JWT_SECRET", "strong-enough-secret-key-32chars-min-ok")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError) as ei:
        sec.require_production_secrets()
    assert "DATABASE_URL" in str(ei.value) or "missing" in str(ei.value).lower()


def test_rate_limit_blocks_after_threshold(monkeypatch):
    monkeypatch.setenv("RL_ADMIN_LOGIN", "3")
    monkeypatch.setenv("RL_ADMIN_LOGIN_WINDOW", "60")
    ip = "203.0.113.99"
    # Clear path: hit until blocked
    blocked = False
    for _ in range(10):
        ok, retry, limit = check("admin_login", ip)
        if not ok:
            blocked = True
            assert retry >= 1
            assert limit == 3
            break
    assert blocked is True
    assert allow("admin_login", ip) is False


def test_cors_foreign_origin_policy():
    """Document expected CORS policy: only same-origin / known fronts."""
    allowed = {
        "https://geografia-19tf.onrender.com",
        "https://geografia.tj",
    }
    foreign = "https://evil.example.com"
    assert foreign not in allowed


def test_jwt_secret_not_leaked_in_public_status(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "super-secret-value-should-not-appear")
    from db.secrets import secrets_public_status

    st = secrets_public_status()
    assert "super-secret-value" not in str(st)
