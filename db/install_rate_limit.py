"""
P1.4 — Apply rate limits to sensitive endpoints.
"""
from __future__ import annotations

import logging
import re

from flask import jsonify, request

log = logging.getLogger("geografia.rate_limit")

# path patterns → bucket
_RULES: list[tuple[re.Pattern, str, set[str] | None]] = [
    (re.compile(r"^/api/admin/login/?$"), "admin_login", {"POST"}),
    (re.compile(r"^/api/auth/google/?$"), "google_auth", {"POST"}),
    (re.compile(r"^/api/student/login/?$"), "student_login", {"POST"}),
    (re.compile(r"^/api/student/verify/?$"), "student_login", {"POST", "GET"}),
    (re.compile(r"^/api/olympiads/[^/]+/start/?$"), "quiz_start", {"POST"}),
    (re.compile(r"^/api/olympiads/[^/]+/submit/?$"), "quiz_submit", {"POST"}),
    (re.compile(r"^/api/quizzes/[^/]+/start/?$"), "quiz_start", {"POST"}),
    (re.compile(r"^/api/quizzes/[^/]+/submit/?$"), "quiz_submit", {"POST"}),
    (re.compile(r"^/api/admin/"), "admin_api", None),  # any method
    (re.compile(r"^/api/auth/"), "auth_api", None),
]


def install(app) -> None:
    from db.rate_limit import check, client_ip

    @app.before_request
    def _rate_limit_gate():
        path = request.path or ""
        method = (request.method or "GET").upper()
        bucket = None
        for rx, b, methods in _RULES:
            if methods and method not in methods:
                continue
            if rx.search(path):
                bucket = b
                break
        if not bucket:
            return None
        ip = client_ip(request)
        ok, retry, limit = check(bucket, ip)
        if ok:
            return None
        log.warning("rate limit bucket=%s ip=%s path=%s", bucket, ip, path)
        resp = jsonify({
            "error": "Зиёд кӯшиш. Лутфан баъдтар такрор кунед.",
            "reason": "rate_limited",
            "bucket": bucket,
            "retryAfter": retry,
            "limit": limit,
        })
        resp.status_code = 429
        resp.headers["Retry-After"] = str(retry)
        return resp

    log.info("rate limit installed")
    print("[boot] rate limit: on")
