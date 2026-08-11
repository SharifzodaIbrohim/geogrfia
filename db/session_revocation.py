"""
P1.2 — Server-side session invalidation (JWT jti denylist).

Logout flow:
  1. Read session JWT from cookie
  2. Extract jti (+ exp)
  3. Add to revoked set (memory + optional PostgreSQL)
  4. Clear cookie
  5. Drop legacy ADMIN_TOKENS entry

decode_token rejects revoked jti → old cookie no longer authenticates.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any

log = logging.getLogger("geografia.session_revoke")

_lock = threading.Lock()
# jti -> expires_at (unix)
_revoked: dict[str, int] = {}


def _purge_expired(now: int | None = None) -> None:
    now = now or int(time.time())
    dead = [k for k, exp in _revoked.items() if exp <= now]
    for k in dead:
        _revoked.pop(k, None)


def revoke_jti(jti: str, exp: int | None = None) -> None:
    if not jti:
        return
    exp_i = int(exp or (time.time() + 86400 * 8))
    with _lock:
        _revoked[jti] = exp_i
        _purge_expired()
    _persist_revoke(jti, exp_i)


def is_revoked(jti: str | None) -> bool:
    if not jti:
        return False
    now = int(time.time())
    with _lock:
        _purge_expired(now)
        exp = _revoked.get(jti)
        if exp is not None:
            return exp > now
    # Optional PG lookup (covers other workers / restart)
    if _pg_is_revoked(jti):
        with _lock:
            _revoked[jti] = now + 3600
        return True
    return False


def revoke_token(token: str) -> dict[str, Any] | None:
    """Decode enough to revoke; returns claims if token was parseable."""
    if not token:
        return None
    try:
        import jwt
        from db.auth_tokens import JWT_ALG, JWT_SECRET

        # verify signature but allow expired so logout still works after TTL edge
        try:
            data = jwt.decode(
                token,
                JWT_SECRET,
                algorithms=[JWT_ALG],
                options={"verify_exp": False},
            )
        except jwt.PyJWTError:
            return None
        jti = data.get("jti")
        exp = data.get("exp")
        if jti:
            revoke_jti(str(jti), int(exp) if exp else None)
        return data
    except Exception as e:
        log.debug("revoke_token: %s", e)
        return None


def _persist_revoke(jti: str, exp: int) -> None:
    try:
        from db.connection import get_session, is_postgres_enabled
        from sqlalchemy import text

        if not is_postgres_enabled():
            return
        with get_session() as s:
            s.execute(
                text(
                    "INSERT INTO revoked_sessions (jti, expires_at) "
                    "VALUES (:jti, to_timestamp(:exp)) "
                    "ON CONFLICT (jti) DO UPDATE SET expires_at = EXCLUDED.expires_at"
                ),
                {"jti": jti, "exp": exp},
            )
    except Exception as e:
        # Table may not exist yet — memory denylist still works
        log.debug("persist revoke skipped: %s", e)


def _pg_is_revoked(jti: str) -> bool:
    try:
        from db.connection import get_session, is_postgres_enabled
        from sqlalchemy import text

        if not is_postgres_enabled():
            return False
        with get_session() as s:
            row = s.execute(
                text(
                    "SELECT 1 FROM revoked_sessions "
                    "WHERE jti = :jti AND expires_at > NOW() LIMIT 1"
                ),
                {"jti": jti},
            ).first()
            return bool(row)
    except Exception:
        return False


def revoke_stats() -> dict[str, int]:
    with _lock:
        _purge_expired()
        return {"revoked_cached": len(_revoked)}
