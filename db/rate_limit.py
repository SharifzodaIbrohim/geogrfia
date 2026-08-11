"""
P1.4 — In-process sliding-window rate limiter.

Key = (bucket, client_ip). Suitable for single-worker Render free tier.
Configure limits via env (requests per window seconds).
"""
from __future__ import annotations

import os
import threading
import time
from collections import defaultdict, deque
from typing import Deque

_lock = threading.Lock()
_hits: dict[str, Deque[float]] = defaultdict(deque)


def _env_int(name: str, default: int) -> int:
    try:
        return int((os.environ.get(name) or str(default)).strip())
    except ValueError:
        return default


# bucket -> (max_requests, window_seconds)
def _limits() -> dict[str, tuple[int, int]]:
    return {
        "admin_login": (_env_int("RL_ADMIN_LOGIN", 5), _env_int("RL_ADMIN_LOGIN_WINDOW", 60)),
        "google_auth": (_env_int("RL_GOOGLE_AUTH", 10), _env_int("RL_GOOGLE_AUTH_WINDOW", 60)),
        "student_login": (_env_int("RL_STUDENT_LOGIN", 20), _env_int("RL_STUDENT_LOGIN_WINDOW", 60)),
        "quiz_start": (_env_int("RL_QUIZ_START", 10), _env_int("RL_QUIZ_START_WINDOW", 60)),
        "quiz_submit": (_env_int("RL_QUIZ_SUBMIT", 30), _env_int("RL_QUIZ_SUBMIT_WINDOW", 60)),
        "admin_api": (_env_int("RL_ADMIN_API", 120), _env_int("RL_ADMIN_API_WINDOW", 60)),
        "auth_api": (_env_int("RL_AUTH_API", 60), _env_int("RL_AUTH_API_WINDOW", 60)),
    }


def client_ip(environ_or_request) -> str:
    """Best-effort client IP (Render sets X-Forwarded-For)."""
    try:
        # Flask request
        xff = (environ_or_request.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
        if xff:
            return xff
        return environ_or_request.remote_addr or "0.0.0.0"
    except Exception:
        pass
    try:
        env = environ_or_request
        xff = (env.get("HTTP_X_FORWARDED_FOR") or "").split(",")[0].strip()
        if xff:
            return xff
        return env.get("REMOTE_ADDR") or "0.0.0.0"
    except Exception:
        return "0.0.0.0"


def check(bucket: str, ip: str) -> tuple[bool, int, int]:
    """
    Returns (allowed, retry_after_sec, limit).
    If not allowed, retry_after_sec > 0.
    """
    limits = _limits()
    max_n, window = limits.get(bucket, (60, 60))
    key = f"{bucket}:{ip}"
    now = time.time()
    with _lock:
        q = _hits[key]
        while q and q[0] <= now - window:
            q.popleft()
        if len(q) >= max_n:
            retry = int(max(1, window - (now - q[0])))
            return False, retry, max_n
        q.append(now)
        return True, 0, max_n


def allow(bucket: str, ip: str) -> bool:
    ok, _, _ = check(bucket, ip)
    return ok
