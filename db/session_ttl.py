"""
P1.3 — Configurable session TTL.

Env:
  USER_SESSION_TTL   seconds (default 7 days = 604800)
  ADMIN_SESSION_TTL  seconds (default 12 hours = 43200)

Bounds prevent accidental infinite / tiny sessions.
"""
from __future__ import annotations

import os

# Defaults
_DEFAULT_USER = 60 * 60 * 24 * 7   # 7 days
_DEFAULT_ADMIN = 60 * 60 * 12     # 12 hours

_MIN = 60           # 1 minute floor
_MAX_USER = 60 * 60 * 24 * 30   # 30 days
_MAX_ADMIN = 60 * 60 * 24 * 2   # 2 days (admins shorter by policy)


def _parse(name: str, default: int, lo: int, hi: int) -> int:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        val = int(raw)
    except ValueError:
        return default
    return max(lo, min(hi, val))


def user_session_ttl() -> int:
    return _parse("USER_SESSION_TTL", _DEFAULT_USER, _MIN, _MAX_USER)


def admin_session_ttl() -> int:
    return _parse("ADMIN_SESSION_TTL", _DEFAULT_ADMIN, _MIN, _MAX_ADMIN)


def ttl_public_status() -> dict:
    u, a = user_session_ttl(), admin_session_ttl()
    return {
        "userSessionSec": u,
        "adminTtlSec": a,
        "userDays": round(u / 86400, 2),
        "adminHours": round(a / 3600, 2),
    }
