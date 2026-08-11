"""
Phase 2 / P0.9 / P1.2 / P1.3 — JWT with jti + configurable TTL.
"""
from __future__ import annotations

import secrets
import time
from typing import Any

import jwt

from db.secrets import get_jwt_secret
from db.session_ttl import admin_session_ttl, user_session_ttl

JWT_SECRET = get_jwt_secret()
JWT_ALG = "HS256"


def __getattr__(name: str):
    # Legacy imports: from db.auth_tokens import USER_TTL, ADMIN_TTL
    if name == "USER_TTL":
        return user_session_ttl()
    if name == "ADMIN_TTL":
        return admin_session_ttl()
    raise AttributeError(name)


def _new_jti() -> str:
    return secrets.token_urlsafe(24)


def issue_user_token(user: dict) -> str:
    now = int(time.time())
    ttl = user_session_ttl()
    payload = {
        "typ": "user",
        "sub": str(user["id"]),
        "email": user.get("email"),
        "name": user.get("name"),
        "avatar": user.get("avatar") or user.get("avatar_url"),
        "jti": _new_jti(),
        "iat": now,
        "exp": now + ttl,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def issue_admin_token(admin: dict) -> str:
    now = int(time.time())
    role = admin.get("role")
    if not role:
        role = "monitor"
    ttl = admin_session_ttl()
    payload = {
        "typ": "admin",
        "sub": str(admin["id"]),
        "login": admin.get("login"),
        "name": admin.get("name") or admin.get("login"),
        "role": role,
        "jti": _new_jti(),
        "iat": now,
        "exp": now + ttl,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def decode_token(token: str) -> dict[str, Any] | None:
    if not token:
        return None
    try:
        data = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.PyJWTError:
        return None
    try:
        from db.session_revocation import is_revoked

        if is_revoked(data.get("jti")):
            return None
    except Exception:
        pass
    return data


def user_from_token(token: str) -> dict | None:
    data = decode_token(token)
    if not data or data.get("typ") != "user":
        return None
    return {
        "id": data["sub"],
        "email": data.get("email"),
        "name": data.get("name"),
        "avatar": data.get("avatar"),
        "jti": data.get("jti"),
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
        "jti": data.get("jti"),
    }
