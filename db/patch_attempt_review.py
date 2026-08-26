"""P1 Admin attempt review — materializes full module from _par_b64_*.txt."""
from __future__ import annotations

import base64
import zlib
from pathlib import Path

_dir = Path(__file__).resolve().parent
_parts = sorted(_dir.glob("_par_b64_*.txt"))
if not _parts:
    # when installed as db/patch_attempt_review.py, parts may sit in repo root
    _parts = sorted(_dir.parent.glob("_par_b64_*.txt"))
if not _parts:
    raise RuntimeError("patch_attempt_review: missing _par_b64_*.txt next to module or repo root")

_src = zlib.decompress(
    base64.b64decode("".join(p.read_text(encoding="utf-8").strip() for p in _parts))
).decode("utf-8")
_g: dict = {"__name__": "patch_attempt_review"}
exec(compile(_src, "patch_attempt_review_full.py", "exec"), _g)
install = _g["install"]
build_review = _g.get("build_review")
# re-export public names
for _k, _v in list(_g.items()):
    if _k in ("install", "build_review") or (not _k.startswith("_") and callable(_v)):
        globals()[_k] = _v
