"""
Phase 2 / P0.9 — JWT tokens for users and admins.
Secret resolution via db.secrets (required in production).
"""
from __future__ import annotations

import os
import time
from typing import Any

import jwt

from db.secrets import get_jwt_secret

JWT_SECRET = get_jwt_secret()
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
    role = admin.get("role")
    # P0.7: never invent super_admin; unknown → monitor (least privilege for token claim)
    if not role:
        role = "monitor"
    payload = {
        "typ": "admin",
        "sub": str(admin["id"]),
        "login": admin.get("login"),
        "name": admin.get("name") or admin.get("login"),
        "role": role,
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
