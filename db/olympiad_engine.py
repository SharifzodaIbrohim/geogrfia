"""Olympiad engine — plain source parts (no zlib/b64)."""
from __future__ import annotations
from pathlib import Path
_dir = Path(__file__).resolve().parent
def _key(p):
    try:
        return int(p.stem.rsplit("_", 1)[-1])
    except Exception:
        return p.name
_parts = sorted(_dir.glob("olympiad_engine_src_*.py"), key=_key)
if not _parts:
    raise RuntimeError("olympiad_engine_src_*.py missing")
_src = "".join(p.read_text(encoding="utf-8") for p in _parts)
exec(compile(_src, "db/olympiad_engine.py", "exec"), globals())
