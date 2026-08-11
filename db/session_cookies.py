"""
P1.1 — HttpOnly Secure session cookies (OWASP).

Flow:
  Google verifies identity
    → backend verifies Google ID token
    → backend issues signed session JWT
    → Set-Cookie: HttpOnly; Secure; SameSite=Lax; Path=/

Cookie names (production HTTPS):
  __Host-geografia_session   (user / Gmail)
  __Host-geografia_admin     (admin panel)

Dev (no HTTPS): geografia_session / geografia_admin without __Host- prefix.
"""
from __future__ import annotations

import os
from typing import Any

from flask import Request, Response

from db.auth_tokens import (
    ADMIN_TTL,
    USER_TTL,
    admin_from_token,
    decode_token,
    issue_admin_token,
    issue_user_token,
    user_from_token,
)
from db.secrets import is_production

# __Host- requires Secure + Path=/ + no Domain (RFC 6265bis)
USER_COOKIE_HOST = "__Host-geografia_session"
ADMIN_COOKIE_HOST = "__Host-geografia_admin"
USER_COOKIE_DEV = "geografia_session"
ADMIN_COOKIE_DEV = "geografia_admin"


def _use_host_prefix() -> bool:
    # __Host- only works over HTTPS
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
        # never set domain — required for __Host- and safer generally
    }
    if _use_host_prefix() or is_production():
        kw["secure"] = True
    else:
        # local http://localhost
        kw["secure"] = False
    return kw


def set_user_session(resp: Response, user: dict) -> str:
    token = issue_user_token(user)
    resp.set_cookie(user_cookie_name(), token, **_cookie_kwargs(USER_TTL))
    return token


def set_admin_session(resp: Response, admin: dict) -> str:
    token = issue_admin_token(admin)
    resp.set_cookie(admin_cookie_name(), token, **_cookie_kwargs(ADMIN_TTL))
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
    # 1) Cookie (preferred)
    tok = (request.cookies.get(cookie_name) or "").strip()
    if tok:
        return tok
    # 2) Authorization Bearer (transition / API clients)
    auth = (request.headers.get("Authorization") or "").strip()
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    # 3) Legacy headers
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
    # Legacy in-memory admin tokens from remote core
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
