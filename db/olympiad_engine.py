"""Olympiad engine — single zlib+b64 multi-file loader."""
from __future__ import annotations
import zlib, base64
from pathlib import Path
_dir = Path(__file__).resolve().parent
_parts = sorted(_dir.glob("oe_b64_*.txt"))
if not _parts:
    raise RuntimeError("oe_b64_*.txt missing")
_b64 = "".join(p.read_text(encoding="utf-8").strip() for p in _parts)
_src = zlib.decompress(base64.b64decode(_b64)).decode("utf-8")
exec(compile(_src, "db/olympiad_engine.py", "exec"), globals())
