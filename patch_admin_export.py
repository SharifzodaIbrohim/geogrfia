"""Admin export — loader from _export_b64_*.txt."""
from __future__ import annotations
import base64, zlib
from pathlib import Path
_dir = Path(__file__).resolve().parent
def _load_src() -> str:
    parts = sorted(_dir.glob("_export_b64_*.txt"))
    if not parts:
        raise RuntimeError("no _export_b64_*.txt")
    raw = "".join(p.read_text(encoding="utf-8").strip() for p in parts)
    return zlib.decompress(base64.b64decode(raw)).decode("utf-8")
def install(app=None):
    src = _load_src()
    g = {"__name__": "patch_admin_export_body"}
    exec(compile(src, "patch_admin_export_body.py", "exec"), g)
    return g["install"](app)
