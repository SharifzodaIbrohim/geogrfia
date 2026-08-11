"""
P1.8 — Structured request logging (no secrets).

Logs: request_id, method, path, status, latency_ms, user/admin id (if known).
Never logs: password, JWT, session tokens, Google tokens, Authorization body.
"""
from __future__ import annotations

import logging
import secrets
import time
from typing import Any

log = logging.getLogger("geografia.request")

_SENSITIVE_KEYS = {
    "password",
    "passwd",
    "token",
    "access_token",
    "refresh_token",
    "id_token",
    "session",
    "sessiontoken",
    "session_token",
    "authorization",
    "jwt",
    "secret",
    "credential",
    "credentials",
}


def _new_rid() -> str:
    return secrets.token_hex(8)


def install(app) -> None:
    @app.before_request
    def _req_start():
        from flask import g, request

        g._req_start = time.perf_counter()
        g.request_id = request.headers.get("X-Request-Id") or _new_rid()

    @app.after_request
    def _req_log(resp):
        from flask import g, request

        try:
            start = getattr(g, "_req_start", None)
            latency = int((time.perf_counter() - start) * 1000) if start else -1
            rid = getattr(g, "request_id", "-")
            path = request.path or ""
            # Skip noisy static if desired
            if path.startswith("/css/") or path.startswith("/js/") or path.startswith("/books/"):
                resp.headers.setdefault("X-Request-Id", rid)
                return resp

            admin_id = None
            user_id = None
            try:
                admin_id = getattr(g, "admin_id", None)
                user_id = getattr(g, "user_id", None)
            except Exception:
                pass

            status = resp.status_code
            level = logging.WARNING if status >= 500 else logging.INFO
            log.log(
                level,
                "rid=%s method=%s path=%s status=%s latency_ms=%s admin=%s user=%s",
                rid,
                request.method,
                path,
                status,
                latency,
                admin_id or "-",
                user_id or "-",
            )
            resp.headers.setdefault("X-Request-Id", rid)
        except Exception as e:
            log.debug("request log failed: %s", e)
        return resp

    @app.errorhandler(Exception)
    def _unhandled(err):
        from flask import g, jsonify, request

        # Let HTTPException pass through Flask defaults
        try:
            from werkzeug.exceptions import HTTPException

            if isinstance(err, HTTPException):
                return err
        except Exception:
            pass

        rid = getattr(g, "request_id", _new_rid())
        log.exception(
            "rid=%s unhandled path=%s error=%s",
            rid,
            getattr(request, "path", "?"),
            type(err).__name__,
        )
        return jsonify({
            "error": "Хатои дохилии сервер.",
            "requestId": rid,
        }), 500

    # Ensure logger has a handler in production gunicorn
    if not log.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s [req] %(message)s")
        )
        log.addHandler(handler)
        log.setLevel(logging.INFO)
        log.propagate = False

    print("[boot] request logging: on")


def redact_dict(data: dict[str, Any] | None) -> dict[str, Any]:
    """Return a copy with sensitive keys redacted (for optional debug)."""
    if not data:
        return {}
    out = {}
    for k, v in data.items():
        if str(k).lower() in _SENSITIVE_KEYS:
            out[k] = "***"
        elif isinstance(v, dict):
            out[k] = redact_dict(v)
        else:
            out[k] = v
    return out
