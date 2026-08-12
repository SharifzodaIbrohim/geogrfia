"""Geografia entry — Phase 25.5.1 local-only (no remote exec)."""
from __future__ import annotations
import base64
import zlib
from pathlib import Path

_parts = sorted(Path(__file__).resolve().parent.glob("_srv_b64_*.txt"))
if not _parts:
    raise RuntimeError(
        "missing _srv_b64_*.txt — local server payload. "
        "Phase 25.5.1: no remote GitHub load."
    )
_src = zlib.decompress(
    base64.b64decode("".join(p.read_text(encoding="utf-8").strip() for p in _parts))
).decode("utf-8")
exec(compile(_src, "server.py", "exec"), globals())
