"""Olympiad engine — plain multi-part source loader (NO zlib)."""
from __future__ import annotations
from pathlib import Path
_dir = Path(__file__).resolve().parent
_parts = sorted(_dir.glob("olympiad_engine_src_*.py"))
if not _parts:
    raise RuntimeError("olympiad_engine_src_*.py missing — deploy incomplete")
_src = "".join(p.read_text(encoding="utf-8") for p in _parts)
exec(compile(_src, "db/olympiad_engine.py", "exec"), globals())
