"""Olympiad engine loader from local oe_p*.txt chunks."""
from __future__ import annotations
import zlib, base64
from pathlib import Path
_dir = Path(__file__).resolve().parent
_parts = sorted(_dir.glob("oe_p*.txt"))
if not _parts:
    raise RuntimeError("no oe_p*.txt chunks next to olympiad_engine.py")
_src = zlib.decompress(base64.b64decode("".join(p.read_text().strip() for p in _parts))).decode("utf-8")
exec(compile(_src, __file__, "exec"), globals())
