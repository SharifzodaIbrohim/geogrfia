"""P1 Admin attempt review — prefer plain src, else _par_b64_*.txt."""
from __future__ import annotations

import base64
import zlib
from pathlib import Path

_dir = Path(__file__).resolve().parent
_plain = _dir / "patch_attempt_review_src.py"
if not _plain.is_file():
    _plain = _dir.parent / "patch_attempt_review.py"

if _plain.is_file() and _plain.stat().st_size > 2000:
    _src = _plain.read_text(encoding="utf-8")
else:
    _parts = sorted(_dir.glob("_par_b64_*.txt"))
    if not _parts:
        _parts = sorted(_dir.parent.glob("_par_b64_*.txt"))
    if not _parts:
        raise RuntimeError("patch_attempt_review: missing src and _par_b64_*.txt")
    _b64 = "".join(p.read_text(encoding="utf-8").strip() for p in _parts)
    _b64 += "=" * ((4 - len(_b64) % 4) % 4)
    _src = zlib.decompress(base64.b64decode(_b64)).decode("utf-8")

_g: dict = {"__name__": "patch_attempt_review"}
exec(compile(_src, "patch_attempt_review_full.py", "exec"), _g)
install = _g["install"]
build_review = _g.get("build_review")
for _k, _v in list(_g.items()):
    if _k in ("install", "build_review") or (not _k.startswith("_") and callable(_v)):
        globals()[_k] = _v
