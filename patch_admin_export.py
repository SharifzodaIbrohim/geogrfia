"""Admin export — join _pae0..3.txt plain parts."""
from __future__ import annotations
from pathlib import Path
_dir = Path(__file__).resolve().parent

def install(app=None):
    parts = sorted(_dir.glob("_pae*.txt"))
    if not parts:
        raise RuntimeError("export: no _pae*.txt")
    src = "".join(p.read_text(encoding="utf-8") for p in parts)
    g = {"__name__": "patch_admin_export_body"}
    exec(compile(src, "patch_admin_export_body.py", "exec"), g)
    fn = g.get("install")
    if not callable(fn):
        raise RuntimeError("export has no install()")
    return fn(app)
