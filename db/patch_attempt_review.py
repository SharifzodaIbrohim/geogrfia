"""Admin attempt review — 3 plain parts."""
from __future__ import annotations
from pathlib import Path
_b = Path(__file__).resolve().parent
_c = "".join((_b / ("_mini_%d.txt" % i)).read_text(encoding="utf-8") for i in range(3))
exec(compile(_c, "patch_attempt_review_body.py", "exec"), globals())
