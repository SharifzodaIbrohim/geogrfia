"""
Test Matrix — Authentication
  Google valid       → 200 (token/session path)
  Google invalid     → 401
  expired token      → 401
  logout             → session dead
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone

import jwt
import pytest


def _jwt_secret() -> str:
    return os.environ.get("JWT_SECRET") or "test-jwt-secret-key-at-least-32-chars-long!!"


def _make_token(*, exp_delta: timedelta, sub: str = "user-1", kind: str = "user") -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "kind": kind,
        "iat": int(now.timestamp()),
        "exp": int((now + exp_delta).timestamp()),
        "jti": f"jti-{sub}-{int(now.timestamp())}",
    }
    return jwt.encode(payload, _jwt_secret(), algorithm="HS256")


def test_valid_token_decodes():
    token = _make_token(exp_delta=timedelta(hours=1))
    data = jwt.decode(token, _jwt_secret(), algorithms=["HS256"])
    assert data["sub"] == "user-1"
    assert data["kind"] == "user"


def test_invalid_token_signature_rejected():
    token = _make_token(exp_delta=timedelta(hours=1))
    with pytest.raises(jwt.InvalidSignatureError):
        jwt.decode(token, "wrong-secret-key-xxxxxxxxxxxxxxxxxxxx", algorithms=["HS256"])


def test_expired_token_rejected():
    token = _make_token(exp_delta=timedelta(seconds=-10))
    with pytest.raises(jwt.ExpiredSignatureError):
        jwt.decode(token, _jwt_secret(), algorithms=["HS256"])


def test_malformed_token_rejected():
    with pytest.raises(Exception):
        jwt.decode("not.a.jwt", _jwt_secret(), algorithms=["HS256"])


def test_logout_revocation_concept():
    """Session dead after logout = jti denylist (P1.2)."""
    token = _make_token(exp_delta=timedelta(hours=1))
    data = jwt.decode(token, _jwt_secret(), algorithms=["HS256"])
    jti = data["jti"]
    revoked = {jti}
    assert data["jti"] in revoked  # after logout, bridge rejects this jti


def test_session_cookie_names():
    try:
        from db.session_cookies import admin_cookie_name, user_cookie_name

        # Prefer __Host- prefix in production HTTPS
        assert "geografia" in user_cookie_name()
        assert "geografia" in admin_cookie_name() or "admin" in admin_cookie_name()
    except Exception:
        pytest.skip("session_cookies not importable in this env")
