"""
P1.1 / P1.3 — HttpOnly Secure session cookies; TTL from session_ttl.
"""
from __future__ import annotations

import os
from typing import Any

from flask import Request, Response

from db.auth_tokens import (
    admin_from_token,
    issue_admin_token,
    issue_user_token,
    user_from_token,
)
from db.secrets import is_production
from db.session_ttl import admin_session_ttl, user_session_ttl

USER_COOKIE_HOST = "__Host-geografia_session"
ADMIN_COOKIE_HOST = "__Host-geografia_admin"
USER_COOKIE_DEV = "geografia_session"
ADMIN_COOKIE_DEV = "geografia_admin"


def _use_host_prefix() -> bool:
    if is_production():
        return True
    force = (os.environ.get("SESSION_COOKIE_HOST_PREFIX") or "").strip().lower()
    if force in ("1", "true", "yes"):
        return True
    if force in ("0", "false", "no"):
        return False
    return False


def user_cookie_name() -> str:
    return USER_COOKIE_HOST if _use_host_prefix() else USER_COOKIE_DEV


def admin_cookie_name() -> str:
    return ADMIN_COOKIE_HOST if _use_host_prefix() else ADMIN_COOKIE_DEV


def _cookie_kwargs(max_age: int) -> dict[str, Any]:
    kw: dict[str, Any] = {
        "max_age": max_age,
        "httponly": True,
        "samesite": "Lax",
        "path": "/",
    }
    if _use_host_prefix() or is_production():
        kw["secure"] = True
    else:
        kw["secure"] = False
    return kw


def set_user_session(resp: Response, user: dict) -> str:
    token = issue_user_token(user)
    resp.set_cookie(user_cookie_name(), token, **_cookie_kwargs(user_session_ttl()))
    return token


def set_admin_session(resp: Response, admin: dict) -> str:
    token = issue_admin_token(admin)
    resp.set_cookie(admin_cookie_name(), token, **_cookie_kwargs(admin_session_ttl()))
    return token


def clear_user_session(resp: Response) -> None:
    resp.set_cookie(
        user_cookie_name(),
        "",
        expires=0,
        max_age=0,
        httponly=True,
        samesite="Lax",
        path="/",
        secure=_use_host_prefix() or is_production(),
    )


def clear_admin_session(resp: Response) -> None:
    resp.set_cookie(
        admin_cookie_name(),
        "",
        expires=0,
        max_age=0,
        httponly=True,
        samesite="Lax",
        path="/",
        secure=_use_host_prefix() or is_production(),
    )


def _token_from_request(
    request: Request,
    *,
    cookie_name: str,
    header_names: tuple[str, ...] = (),
) -> str:
    tok = (request.cookies.get(cookie_name) or "").strip()
    if tok:
        return tok
    auth = (request.headers.get("Authorization") or "").strip()
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    for h in header_names:
        v = (request.headers.get(h) or "").strip()
        if v:
            return v
    return ""


def current_user(request: Request) -> dict | None:
    tok = _token_from_request(
        request,
        cookie_name=user_cookie_name(),
        header_names=("X-User-Token",),
    )
    return user_from_token(tok)


def current_admin(request: Request) -> dict | None:
    tok = _token_from_request(
        request,
        cookie_name=admin_cookie_name(),
        header_names=("X-Admin-Token",),
    )
    admin = admin_from_token(tok)
    if admin:
        return admin
    if tok:
        try:
            import sys

            for modname in ("server_12d7430", "server_core_remote", "__main__"):
                mod = sys.modules.get(modname)
                if not mod:
                    continue
                tokens = getattr(mod, "ADMIN_TOKENS", None)
                if tokens and tok in tokens:
                    return dict(tokens[tok])
        except Exception:
            pass
    return None
