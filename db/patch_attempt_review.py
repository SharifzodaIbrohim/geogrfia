"""Admin attempt review — plain text parts."""
from __future__ import annotations
from pathlib import Path
_base = Path(__file__).resolve().parent
_code = "".join((_base / ("_rev_plain_%d.txt" % i)).read_text(encoding="utf-8") for i in range(3))
exec(compile(_code, str(_base / "patch_attempt_review_body.py"), "exec"), globals())
