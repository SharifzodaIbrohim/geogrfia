"""P1 Olympiad Engine — loaded from local _oe_b64 chunks (P1.12)."""
from __future__ import annotations
import base64, zlib
from pathlib import Path
_dir = Path(__file__).resolve().parent
_parts = sorted(_dir.glob("_oe_b64_*.txt"))
if not _parts:
    raise RuntimeError("missing db/_oe_b64_*.txt olympiad engine payload")
_src = zlib.decompress(base64.b64decode("".join(p.read_text().strip() for p in _parts))).decode("utf-8")
exec(compile(_src, "olympiad_engine.py", "exec"), globals())
