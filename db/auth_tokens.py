"""
Phase 2 — JWT tokens for users and admins.
Env: JWT_SECRET (required in production). Falls back to a dev secret only if unset.
"""
from __future__ import annotations

import os
import time
from typing import Any

import jwt


def _resolve_jwt_secret() -> str:
    secret = os.environ.get("JWT_SECRET", "").strip()
    env = (os.environ.get("FLASK_ENV") or os.environ.get("ENV") or os.environ.get("APP_ENV") or "").strip().lower()
    is_prod = env in ("production", "prod") or bool(os.environ.get("RENDER") or os.environ.get("DYNO"))
    if secret:
        return secret
    if is_prod:
        raise RuntimeError(
            "JWT_SECRET environment variable is required in production. "
            "Refusing to start with a default secret."
        )
    return "geografia-dev-only-change-me"


JWT_SECRET = _resolve_jwt_secret()
JWT_ALG = "HS256"
USER_TTL = int(os.environ.get("USER_SESSION_TTL", str(60 * 60 * 24 * 7)))
ADMIN_TTL = int(os.environ.get("ADMIN_SESSION_TTL", str(60 * 60 * 12)))


def issue_user_token(user: dict) -> str:
    now = int(time.time())
    payload = {
        "typ": "user",
        "sub": str(user["id"]),
        "email": user.get("email"),
        "name": user.get("name"),
        "avatar": user.get("avatar") or user.get("avatar_url"),
        "iat": now,
        "exp": now + USER_TTL,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def issue_admin_token(admin: dict) -> str:
    now = int(time.time())
    payload = {
        "typ": "admin",
        "sub": str(admin["id"]),
        "login": admin.get("login"),
        "name": admin.get("name") or admin.get("login"),
        "role": admin.get("role") or "monitor",
        "iat": now,
        "exp": now + ADMIN_TTL,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def decode_token(token: str) -> dict[str, Any] | None:
    if not token:
        return None
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.PyJWTError:
        return None


def user_from_token(token: str) -> dict | None:
    data = decode_token(token)
    if not data or data.get("typ") != "user":
        return None
    return {
        "id": data["sub"],
        "email": data.get("email"),
        "name": data.get("name"),
        "avatar": data.get("avatar"),
    }


def admin_from_token(token: str) -> dict | None:
    data = decode_token(token)
    if not data or data.get("typ") != "admin":
        return None
    return {
        "id": data["sub"],
        "login": data.get("login"),
        "name": data.get("name"),
        "role": data.get("role"),
    }
