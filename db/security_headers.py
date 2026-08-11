"""
P1.5 — OWASP-oriented security headers for production responses.
"""
from __future__ import annotations

import logging
import os

from db.secrets import is_production

log = logging.getLogger("geografia.security_headers")

# Conservative CSP: allow self + Google Sign-In scripts/frames if used
_DEFAULT_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' https://accounts.google.com https://apis.google.com; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: https: blob:; "
    "font-src 'self' data:; "
    "connect-src 'self' https://accounts.google.com; "
    "frame-src 'self' https://accounts.google.com; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'"
)


def install(app) -> None:
    csp = (os.environ.get("CONTENT_SECURITY_POLICY") or _DEFAULT_CSP).strip()
    hsts = (os.environ.get("HSTS_VALUE") or "max-age=31536000; includeSubDomains").strip()

    @app.after_request
    def _set_security_headers(resp):
        # Always useful
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault(
            "Permissions-Policy",
            "geolocation=(), microphone=(), camera=(), payment=()",
        )
        resp.headers.setdefault("Content-Security-Policy", csp)

        if is_production():
            resp.headers.setdefault("Strict-Transport-Security", hsts)
            # Avoid caching authenticated API responses by default
            if (resp.headers.get("Cache-Control") is None) and (
                (getattr(resp, "direct_passthrough", False) is False)
            ):
                path = ""
                try:
                    from flask import request as _req
                    path = _req.path or ""
                except Exception:
                    pass
                if path.startswith("/api/"):
                    resp.headers.setdefault("Cache-Control", "no-store")

        return resp

    log.info("security headers installed (prod=%s)", is_production())
    print("[boot] security headers: on")
