"""Admin attempt review — base64 parts (no zlib)."""
from __future__ import annotations
import base64
from pathlib import Path
_base = Path(__file__).resolve().parent
_b64 = "".join((_base / ("_rev_b64p_%d.txt" % i)).read_text(encoding="utf-8").strip() for i in range(7))
exec(compile(base64.b64decode(_b64).decode("utf-8"), "patch_attempt_review_body.py", "exec"), globals())
