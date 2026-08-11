"""
P0.9 — Secrets & credentials policy.

Rules:
  - Never commit real secrets to git.
  - Production MUST set JWT_SECRET (and DATABASE_URL).
  - Weak / empty secrets refuse to boot when production is detected.
  - Optional secrets (Google OAuth) degrade features, do not crash.
"""
from __future__ import annotations

import logging
import os
import secrets as _secrets
from typing import Any

log = logging.getLogger("geografia.secrets")

# Names only — values always from environment
REQUIRED_IN_PRODUCTION = (
    "DATABASE_URL",
    "JWT_SECRET",
)

OPTIONAL = (
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
    "ALLOW_JSON_BACKEND",  # emergency only
    "USER_SESSION_TTL",
    "ADMIN_SESSION_TTL",
)

_WEAK = {
    "",
    "change-me",
    "changeme",
    "secret",
    "jwt-secret",
    "geografia-dev-only-change-me",
    "dev",
    "test",
    "password",
    "123456",
}


def is_production() -> bool:
    env = (
        os.environ.get("FLASK_ENV")
        or os.environ.get("ENV")
        or os.environ.get("APP_ENV")
        or ""
    ).strip().lower()
    if env in ("production", "prod"):
        return True
    # Hosted platforms
    if os.environ.get("RENDER") or os.environ.get("DYNO") or os.environ.get("RAILWAY_ENVIRONMENT"):
        return True
    # DATABASE_URL on a non-local host is a strong signal
    db = (os.environ.get("DATABASE_URL") or "").lower()
    if db and "localhost" not in db and "127.0.0.1" not in db:
        return True
    return False


def _is_weak(value: str | None) -> bool:
    if value is None:
        return True
    v = value.strip()
    if len(v) < 16:
        return True
    if v.lower() in _WEAK:
        return True
    return False


def get_jwt_secret() -> str:
    """
    Resolve JWT signing secret.
    Production: required, min 16 chars, not a known weak value.
    Dev: stable local default (never used on Render if detection works).
    """
    raw = (os.environ.get("JWT_SECRET") or "").strip()
    if raw and not _is_weak(raw):
        return raw
    if is_production():
        raise RuntimeError(
            "P0.9: JWT_SECRET is missing or too weak for production. "
            "Set a random secret (>=32 chars) in the host environment."
        )
    if raw:
        log.warning("JWT_SECRET is weak; using it only because not production")
        return raw
    log.warning("JWT_SECRET unset — using ephemeral dev secret (not for production)")
    return "geografia-dev-only-" + _secrets.token_hex(16)


def require_production_secrets() -> dict[str, Any]:
    """
    Call at boot. Raises RuntimeError if production secrets are invalid.
    Returns a status dict (never includes secret values).
    """
    prod = is_production()
    status: dict[str, Any] = {
        "production": prod,
        "ok": True,
        "missing": [],
        "weak": [],
        "optional_present": [],
    }
    if not prod:
        for name in OPTIONAL:
            if (os.environ.get(name) or "").strip():
                status["optional_present"].append(name)
        return status

    for name in REQUIRED_IN_PRODUCTION:
        val = (os.environ.get(name) or "").strip()
        if not val:
            status["missing"].append(name)
        elif name == "JWT_SECRET" and _is_weak(val):
            status["weak"].append(name)

    for name in OPTIONAL:
        if (os.environ.get(name) or "").strip():
            status["optional_present"].append(name)

    if status["missing"] or status["weak"]:
        status["ok"] = False
        parts = []
        if status["missing"]:
            parts.append("missing=" + ",".join(status["missing"]))
        if status["weak"]:
            parts.append("weak=" + ",".join(status["weak"]))
        raise RuntimeError("P0.9 production secrets invalid: " + "; ".join(parts))

    return status


def redact(value: str | None, keep: int = 4) -> str:
    if not value:
        return ""
    if len(value) <= keep * 2:
        return "***"
    return value[:keep] + "…" + value[-keep:]
