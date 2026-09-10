"""Admin attempt review — zlib+b64 from continuous _rev_b64_00..05 only."""
from __future__ import annotations
import base64
import zlib
from pathlib import Path
_dir = Path(__file__).resolve().parent
_parts = [(_dir / f"_rev_b64_{i:02d}.txt") for i in range(6)]
_missing = [p.name for p in _parts if not p.is_file()]
if _missing:
    raise RuntimeError("patch_attempt_review missing: %s" % _missing)
_b64 = "".join(p.read_text(encoding="utf-8").strip() for p in _parts)
_b64 += "=" * ((4 - len(_b64) % 4) % 4)
_src = zlib.decompress(base64.b64decode(_b64)).decode("utf-8")
if "def install" not in _src or len(_src) < 5000:
    raise RuntimeError("patch_attempt_review incomplete (%d)" % len(_src))
_g = {"__name__": "patch_attempt_review"}
exec(compile(_src, "patch_attempt_review_full.py", "exec"), _g)
install = _g["install"]
build_review = _g.get("build_review")
for _k, _v in list(_g.items()):
    if _k in ("install", "build_review") or (not str(_k).startswith("_") and callable(_v)):
        globals()[_k] = _v
print("[boot] patch_attempt_review b64 OK (%d chars)" % len(_src))
