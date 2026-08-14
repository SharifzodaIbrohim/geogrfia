#!/usr/bin/env python3
"""Materialize server_core.py from _srv_b64_*.txt (local / CI / one-time)."""
from __future__ import annotations

import base64
import zlib
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    parts = sorted(root.glob("_srv_b64_*.txt"))
    if not parts:
        raise SystemExit("no _srv_b64_*.txt found")
    raw = "".join(p.read_text(encoding="utf-8").strip() for p in parts)
    src = zlib.decompress(base64.b64decode(raw)).decode("utf-8")
    if "app = Flask" not in src and "app=Flask" not in src:
        raise SystemExit("payload has no Flask app")
    out = root / "server_core.py"
    out.write_text(src, encoding="utf-8")
    print(f"wrote {out} ({len(src)} chars, {len(src.splitlines())} lines)")


if __name__ == "__main__":
    main()
