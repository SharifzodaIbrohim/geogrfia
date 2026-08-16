#!/usr/bin/env python3
"""Quick checks before Ubuntu/production boot."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    ok = True
    print("Geografia preflight")
    print("root:", ROOT)

    core = ROOT / "server_core.py"
    if core.is_file() and core.stat().st_size > 10000:
        print("[ok] server_core.py", core.stat().st_size, "bytes")
    else:
        print("[warn] server_core.py missing/small — boot may materialize from _srv_b64_*")

    req = ROOT / "requirements.txt"
    print("[ok] requirements.txt" if req.is_file() else "[fail] requirements.txt missing")
    if not req.is_file():
        ok = False

    db_url = os.environ.get("DATABASE_URL", "").strip()
    if db_url.startswith("postgresql"):
        print("[ok] DATABASE_URL set")
    else:
        print("[warn] DATABASE_URL not set in this shell (load .env for prod)")

    jwt = os.environ.get("JWT_SECRET", "").strip()
    if len(jwt) >= 32:
        print("[ok] JWT_SECRET length", len(jwt))
    elif jwt:
        print("[warn] JWT_SECRET short (<32)")
    else:
        print("[warn] JWT_SECRET not set")

    for name in ("server.py", "db/olympiad_engine.py", "db/student_access.py"):
        p = ROOT / name
        if p.is_file():
            print("[ok]", name)
        else:
            print("[fail]", name, "missing")
            ok = False

    print("result:", "PASS" if ok else "CHECK WARNINGS")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
