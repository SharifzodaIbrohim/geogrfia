"""Local server foundation — Phase 25.5.1 (no remote GitHub load)."""
from __future__ import annotations
import base64
import zlib
from pathlib import Path

_dir = Path(__file__).resolve().parent
_parts = sorted(_dir.glob("_sf_part*.txt"))
if not _parts:
    raise RuntimeError("missing _sf_part*.txt foundation chunks")
_b64 = "".join(p.read_text(encoding="utf-8").strip() for p in _parts)
_src = zlib.decompress(base64.b64decode(_b64)).decode("utf-8")
exec(compile(_src, "server_foundation.py", "exec"), globals())
