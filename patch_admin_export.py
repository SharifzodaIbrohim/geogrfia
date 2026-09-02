"""Admin export — join _px00..07.txt sequential plain parts."""
from __future__ import annotations
from pathlib import Path
_dir = Path(__file__).resolve().parent

def install(app=None):
    parts = sorted(_dir.glob("_px*.txt"))
    if not parts:
        raise RuntimeError("export: no _px*.txt body parts")
    src = "".join(p.read_text(encoding="utf-8") for p in parts)
    g = {"__name__": "patch_admin_export_body"}
    exec(compile(src, "patch_admin_export_body.py", "exec"), g)
    fn = g.get("install")
    if not callable(fn):
        raise RuntimeError("export has no install()")
    return fn(app)
