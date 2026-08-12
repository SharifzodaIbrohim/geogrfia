"""Geografia entry — Phase 25.5.1 local-only (no remote exec, no network at boot)."""
from __future__ import annotations

import base64
import zlib
from pathlib import Path

_dir = Path(__file__).resolve().parent

def _load() -> str:
    # 1) Prefer zlib+b64 chunks (compact)
    b64_parts = sorted(_dir.glob("_srv_b64_*.txt"))
    if b64_parts:
        return zlib.decompress(
            base64.b64decode("".join(p.read_text(encoding="utf-8").strip() for p in b64_parts))
        ).decode("utf-8")
    # 2) Plain split parts
    py_parts = sorted(_dir.glob("server_core_part*.py"))
    if py_parts:
        return "".join(p.read_text(encoding="utf-8") for p in py_parts)
    # 3) Single core file
    core = _dir / "server_core.py"
    if core.is_file():
        return core.read_text(encoding="utf-8")
    raise RuntimeError(
        "Phase 25.5.1: missing local payload "
        "(_srv_b64_*.txt | server_core_part*.py | server_core.py). "
        "No remote GitHub load."
    )

_src = _load()
exec(compile(_src, "server_core.py", "exec"), globals())
