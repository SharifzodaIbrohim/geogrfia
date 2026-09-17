"""Geografia entry - Phase A+: plain server_core.py is production default (loader)."""
from __future__ import annotations
import base64
from pathlib import Path
_dir = Path(__file__).resolve().parent
_b = "".join((_dir / f"_sp_b64_{i}.txt").read_text(encoding="utf-8").strip() for i in range(5))
exec(compile(base64.b64decode(_b), "server.py", "exec"), globals())
