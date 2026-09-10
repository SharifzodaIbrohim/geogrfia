"""Admin attempt review — join plain _rev_src_*.txt then exec."""
from __future__ import annotations
from pathlib import Path
_dir = Path(__file__).resolve().parent
_parts = sorted(_dir.glob("_rev_src_*.txt"))
if not _parts:
    raise RuntimeError("patch_attempt_review: missing _rev_src_*.txt")
_src = "".join(p.read_text(encoding="utf-8") for p in _parts)
if "def install" not in _src or len(_src) < 5000:
    raise RuntimeError("patch_attempt_review: incomplete source (%d chars)" % len(_src))
_g: dict = {"__name__": "patch_attempt_review"}
exec(compile(_src, "patch_attempt_review_full.py", "exec"), _g)
install = _g["install"]
build_review = _g.get("build_review")
for _k, _v in list(_g.items()):
    if _k in ("install", "build_review") or (not _k.startswith("_") and callable(_v)):
        globals()[_k] = _v
print("[boot] patch_attempt_review: plain join OK (%d chars)" % len(_src))
