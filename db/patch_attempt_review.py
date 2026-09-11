"""Admin attempt review — loads compressed parts from db/_pr_part_*.txt"""
from __future__ import annotations
import base64, zlib
from pathlib import Path

def _load():
    base = Path(__file__).resolve().parent
    parts = []
    i = 0
    while True:
        f = base / ("_pr_part_%d.txt" % i)
        if not f.exists():
            break
        parts.append(f.read_text(encoding="utf-8").strip())
        i += 1
    if not parts:
        raise RuntimeError("review parts missing")
    raw = zlib.decompress(base64.b64decode("".join(parts)))
    exec(compile(raw, str(base / "patch_attempt_review_body.py"), "exec"), globals())

_load()
