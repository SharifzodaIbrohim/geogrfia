"""Admin attempt review — 4 plain parts + chain results_score_fix."""
from __future__ import annotations
from pathlib import Path
_b = Path(__file__).resolve().parent
_names = ["_mini_0.txt", "_mini_1a.txt", "_mini_1b.txt", "_mini_2.txt"]
_c = "".join((_b / n).read_text(encoding="utf-8") for n in _names)
exec(compile(_c, "patch_attempt_review_body.py", "exec"), globals())

# Chain: enrich Results/Monitor scores after review is available
_orig_install = install

def install(app=None):
    _orig_install(app)
    try:
        from db.patch_results_score_fix import install as _rsf
        _rsf(app)
    except Exception as e:
        print("[boot] patch_results_score_fix (chained) failed:", e)
