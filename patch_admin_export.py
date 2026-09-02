"""Admin export — loader from plain body or _export_b64_*.txt."""
from __future__ import annotations

import base64
import zlib
from pathlib import Path

_dir = Path(__file__).resolve().parent


def _load_src() -> str:
    plain = _dir / "patch_admin_export_body.py"
    if plain.is_file() and plain.stat().st_size > 2000:
        return plain.read_text(encoding="utf-8")
    parts = sorted(_dir.glob("_export_b64_*.txt"))
    if not parts:
        raise RuntimeError("no _export_b64_*.txt and no patch_admin_export_body.py")
    raw = "".join(p.read_text(encoding="utf-8").strip() for p in parts)
    pad = (4 - len(raw) % 4) % 4
    raw += "=" * pad
    return zlib.decompress(base64.b64decode(raw)).decode("utf-8")


def install(app=None):
    src = _load_src()
    g = {"__name__": "patch_admin_export_body"}
    exec(compile(src, "patch_admin_export_body.py", "exec"), g)
    return g["install"](app)
