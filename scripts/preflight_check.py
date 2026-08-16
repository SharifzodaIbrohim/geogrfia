#!/usr/bin/env python3
"""Checks before Ubuntu/production boot — aligned to current stack."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

STATIC_MUST = [
    "index.html",
    "admin.html",
    "student.html",
    "quiz.html",
    "server.py",
    "server_core.py",
    "requirements.txt",
    "js/admin-students-reg.js",
    "js/admin.js",
    "css/admin.css",
    "db/connection.py",
    "db/olympiad_engine.py",
    "db/student_access.py",
]


def main() -> int:
    ok = True
    print("Geografia preflight")
    print("root:", ROOT)

    # optional .env load
    env_path = ROOT / ".env"
    if env_path.is_file():
        try:
            from dotenv import load_dotenv

            load_dotenv(env_path, override=False)
            print("[ok] loaded .env")
        except Exception as e:
            print("[warn] .env present but not loaded:", e)
    else:
        print("[warn] .env missing (copy from .env.example)")

    core = ROOT / "server_core.py"
    if core.is_file() and core.stat().st_size > 10000:
        print("[ok] server_core.py", core.stat().st_size, "bytes")
    else:
        print("[warn] server_core.py missing/small — boot may use _srv_b64_*")

    for name in STATIC_MUST:
        p = ROOT / name
        if p.is_file() and p.stat().st_size > 0:
            print("[ok]", name)
        else:
            print("[fail]", name, "missing")
            ok = False

    db_url = os.environ.get("DATABASE_URL", "").strip()
    if db_url.startswith("postgres"):
        print("[ok] DATABASE_URL set")
        try:
            sys.path.insert(0, str(ROOT))
            from db.connection import health_check

            h = health_check()
            if h.get("ok"):
                print("[ok] DB health", h.get("backend"))
            else:
                print("[fail] DB health", h)
                ok = False
        except Exception as e:
            print("[warn] DB health check skipped:", e)
    else:
        print("[warn] DATABASE_URL not set (required for Ubuntu prod)")

    jwt = os.environ.get("JWT_SECRET", "").strip()
    if len(jwt) >= 32:
        print("[ok] JWT_SECRET length", len(jwt))
    elif jwt:
        print("[warn] JWT_SECRET short (<32)")
    else:
        print("[warn] JWT_SECRET not set")

    print("result:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
