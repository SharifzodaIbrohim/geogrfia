"""Patch olympiad create/scoring for multi-type questions + showResultsToStudents."""
from __future__ import annotations
import base64, zlib
from pathlib import Path
_dir = Path(__file__).resolve().parent
_parts = sorted(_dir.glob("_pob_b64_*.txt"))
if not _parts:
    raise RuntimeError("patch_olympiad_builder parts missing")
_b64 = "".join(p.read_text(encoding="utf-8").strip() for p in _parts)
_src = zlib.decompress(base64.b64decode(_b64)).decode("utf-8")
exec(compile(_src, "db/patch_olympiad_builder.py", "exec"), globals())
