"""
P0.9 — Secrets & credentials policy.

Rules:
  - Never commit real secrets to git.
  - Production MUST set JWT_SECRET (and DATABASE_URL).
  - Weak / empty secrets are rejected in production.
  - Optional secrets (Google OAuth) degrade features, do not crash.
"""
from __future__ import annotations

import logging
import os
import secrets as _secrets
from typing import Any

log = logging.getLogger("geografia.secrets")

REQUIRED_IN_PRODUCTION = (
    "DATABASE_URL",
    "JWT_SECRET",
)

OPTIONAL = (
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
    "ALLOW_JSON_BACKEND",
    "USER_SESSION_TTL",
    "ADMIN_SESSION_TTL",
    "GEOGRAFIA_STRICT_SECRETS",
)

# Known-bad / tutorial values — never accept in production
_WEAK = {
    "",
    "change-me",
    "changeme",
    "secret",
    "jwt-secret",
    "jwt_secret",
    "geografia-dev-only-change-me",
    "dev",
    "test",
    "password",
    "123456",
    "admin",
    "Admin@2026",
}

MIN_JWT_LEN_PROD = 32
MIN_JWT_LEN_DEV = 16


def is_production() -> bool:
    env = (
        os.environ.get("FLASK_ENV")
        or os.environ.get("ENV")
        or os.environ.get("APP_ENV")
        or ""
    ).strip().lower()
    if env in ("production", "prod"):
        return True
    if os.environ.get("RENDER") or os.environ.get("DYNO") or os.environ.get("RAILWAY_ENVIRONMENT"):
        return True
    db = (os.environ.get("DATABASE_URL") or "").lower()
    if db and "localhost" not in db and "127.0.0.1" not in db:
        return True
    return False


def strict_secrets() -> bool:
    return os.environ.get("GEOGRAFIA_STRICT_SECRETS", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _is_weak(value: str | None, *, prod: bool) -> bool:
    if value is None:
        return True
    v = value.strip()
    if v.lower() in _WEAK:
        return True
    min_len = MIN_JWT_LEN_PROD if prod else MIN_JWT_LEN_DEV
    if len(v) < min_len:
        return True
    return False


def get_jwt_secret() -> str:
    """
    Resolve JWT signing secret.
    Production: required, >=32 chars, not a known weak value.
    Dev: ephemeral random if unset (process-local only).
    """
    raw = (os.environ.get("JWT_SECRET") or "").strip()
    prod = is_production()
    if raw and not _is_weak(raw, prod=prod):
        return raw
    if prod:
        raise RuntimeError(
            "P0.9: JWT_SECRET is missing or too weak for production. "
            "Set a random secret (>=32 chars) in the host environment. "
            "Example: python -c \"import secrets; print(secrets.token_urlsafe(48))\""
        )
    if raw:
        log.warning("JWT_SECRET is weak; accepting only because not production")
        return raw
    # Ephemeral — sessions die on restart (acceptable for local dev)
    log.warning("JWT_SECRET unset — using ephemeral dev secret (not for production)")
    return "geografia-dev-only-" + _secrets.token_hex(24)


def require_production_secrets() -> dict[str, Any]:
    """
    Validate secrets. Raises RuntimeError when production secrets are invalid.
    Return value never includes secret material.
    """
    prod = is_production()
    status: dict[str, Any] = {
        "production": prod,
        "strict": strict_secrets(),
        "ok": True,
        "missing": [],
        "weak": [],
        "optional_present": [],
        "google_oauth": bool((os.environ.get("GOOGLE_CLIENT_ID") or "").strip()),
    }

    for name in OPTIONAL:
        if name == "GEOGRAFIA_STRICT_SECRETS":
            continue
        if (os.environ.get(name) or "").strip():
            status["optional_present"].append(name)

    if not prod:
        return status

    for name in REQUIRED_IN_PRODUCTION:
        val = (os.environ.get(name) or "").strip()
        if not val:
            status["missing"].append(name)
        elif name == "JWT_SECRET" and _is_weak(val, prod=True):
            status["weak"].append(name)

    if status["missing"] or status["weak"]:
        status["ok"] = False
        parts = []
        if status["missing"]:
            parts.append("missing=" + ",".join(status["missing"]))
        if status["weak"]:
            parts.append("weak=" + ",".join(status["weak"]))
        raise RuntimeError("P0.9 production secrets invalid: " + "; ".join(parts))

    return status


def secrets_public_status() -> dict[str, Any]:
    """Safe status for /api/health — never leaks values."""
    prod = is_production()
    jwt = (os.environ.get("JWT_SECRET") or "").strip()
    db = (os.environ.get("DATABASE_URL") or "").strip()
    return {
        "production": prod,
        "strict": strict_secrets(),
        "databaseUrlSet": bool(db),
        "jwtSecretSet": bool(jwt),
        "jwtSecretStrong": bool(jwt) and not _is_weak(jwt, prod=prod),
        "googleClientIdSet": bool((os.environ.get("GOOGLE_CLIENT_ID") or "").strip()),
        "jsonBackendAllowed": (os.environ.get("ALLOW_JSON_BACKEND") or "").strip().lower()
        in ("1", "true", "yes"),
    }


def redact(value: str | None, keep: int = 4) -> str:
    if not value:
        return ""
    if len(value) <= keep * 2:
        return "***"
    return value[:keep] + "…" + value[-keep:]
