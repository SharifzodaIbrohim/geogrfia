"""
Phase 2 — Google ID token verification.
Requires env: GOOGLE_CLIENT_ID
Optional: GOOGLE_CLIENT_SECRET (for future server-side code flow)
"""
from __future__ import annotations

import os
from typing import Any

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()

# Last verification error (diagnostics only)
_LAST_ERROR: str | None = None


def google_configured() -> bool:
    return bool(GOOGLE_CLIENT_ID)


def last_verify_error() -> str | None:
    return _LAST_ERROR


def verify_google_id_token(id_token: str) -> dict[str, Any] | None:
    """
    Verify Google ID token and return {sub, email, name, picture} or None.
    Uses google-auth if installed.
    """
    global _LAST_ERROR
    _LAST_ERROR = None

    if not GOOGLE_CLIENT_ID:
        _LAST_ERROR = "GOOGLE_CLIENT_ID not set"
        return None
    if not id_token or not isinstance(id_token, str) or len(id_token) < 20:
        _LAST_ERROR = "empty or short token"
        return None

    try:
        from google.oauth2 import id_token as google_id_token
        from google.auth.transport import requests as google_requests
    except ImportError as e:
        _LAST_ERROR = f"google-auth not installed: {e}"
        return None

    try:
        info = google_id_token.verify_oauth2_token(
            id_token,
            google_requests.Request(),
            GOOGLE_CLIENT_ID,
            clock_skew_in_seconds=60,
        )
    except Exception as e:
        _LAST_ERROR = f"{type(e).__name__}: {e}"
        return None

    try:
        iss = info.get("iss")
        if iss not in ("accounts.google.com", "https://accounts.google.com"):
            _LAST_ERROR = f"bad iss: {iss}"
            return None
        email = info.get("email")
        if not email:
            _LAST_ERROR = "no email in token"
            return None
        # Only reject explicit False (missing/True OK)
        if info.get("email_verified") is False:
            _LAST_ERROR = "email not verified"
            return None
        return {
            "sub": info["sub"],
            "email": email,
            "name": info.get("name") or email.split("@")[0],
            "picture": info.get("picture"),
        }
    except Exception as e:
        _LAST_ERROR = f"parse: {type(e).__name__}: {e}"
        return None
