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


def google_configured() -> bool:
    return bool(GOOGLE_CLIENT_ID)


def verify_google_id_token(id_token: str) -> dict[str, Any] | None:
    """
    Verify Google ID token and return {sub, email, name, picture} or None.
    Uses google-auth if installed; otherwise returns None.
    """
    if not GOOGLE_CLIENT_ID or not id_token:
        return None
    try:
        from google.oauth2 import id_token as google_id_token
        from google.auth.transport import requests as google_requests

        info = google_id_token.verify_oauth2_token(
            id_token,
            google_requests.Request(),
            GOOGLE_CLIENT_ID,
        )
        if info.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
            return None
        email = info.get("email")
        if not email or not info.get("email_verified", True):
            return None
        return {
            "sub": info["sub"],
            "email": email,
            "name": info.get("name") or email.split("@")[0],
            "picture": info.get("picture"),
        }
    except Exception:
        return None
