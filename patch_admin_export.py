"""Admin export loader: half-b64 body, then src parts, then plain, then legacy b64."""
from __future__ import annotations

import base64
import zlib
from pathlib import Path

_dir = Path(__file__).resolve().parent


def _load_src() -> str:
    # 1) Two-half compressed body (most reliable after this fix)
    h0 = _dir / "_export_half_0.txt"
    h1 = _dir / "_export_half_1.txt"
    if h0.is_file() and h1.is_file():
        raw = h0.read_text(encoding="utf-8").strip() + h1.read_text(encoding="utf-8").strip()
        pad = (4 - len(raw) % 4) % 4
        raw += "=" * pad
        return zlib.decompress(base64.b64decode(raw)).decode("utf-8")
    # 2) Plain single file
    plain = _dir / "patch_admin_export_body.py"
    if plain.is_file() and plain.stat().st_size > 2000:
        return plain.read_text(encoding="utf-8")
    # 3) Plain source parts
    src_parts = sorted(_dir.glob("_export_src_*.txt"))
    if src_parts and sum(p.stat().st_size for p in src_parts) > 2000:
        return "".join(p.read_text(encoding="utf-8") for p in src_parts)
    # 4) Legacy multi b64
    b64_parts = sorted(_dir.glob("_export_b64_*.txt"))
    if not b64_parts:
        raise RuntimeError("export: no body sources found")
    raw = "".join(p.read_text(encoding="utf-8").strip() for p in b64_parts)
    pad = (4 - len(raw) % 4) % 4
    raw += "=" * pad
    return zlib.decompress(base64.b64decode(raw)).decode("utf-8")


def install(app=None):
    src = _load_src()
    g = {"__name__": "patch_admin_export_body"}
    exec(compile(src, "patch_admin_export_body.py", "exec"), g)
    fn = g.get("install")
    if not callable(fn):
        raise RuntimeError("export body has no install()")
    return fn(app)
