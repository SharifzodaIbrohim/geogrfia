"""Boot patch: grade by question text + selected option text (shuffle-safe)."""
from __future__ import annotations
import base64, zlib
from pathlib import Path
_dir = Path(__file__).resolve().parent
_parts = sorted(_dir.glob("_pst_b64_*.txt"))
if not _parts:
    raise RuntimeError("patch_score_text parts missing")
_b64 = "".join(p.read_text(encoding="utf-8").strip() for p in _parts)
_src = zlib.decompress(base64.b64decode(_b64)).decode("utf-8")
exec(compile(_src, "db/patch_score_text.py", "exec"), globals())
