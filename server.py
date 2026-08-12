"""Geografia entry — Phase 25.5.1 local-only (no remote exec, no network at boot)."""
from __future__ import annotations

from pathlib import Path

_core = Path(__file__).resolve().parent / "server_core.py"
if not _core.is_file():
    raise RuntimeError(
        "missing server_core.py — Phase 25.5.1 requires local payload. "
        "No remote GitHub load."
    )
_src = _core.read_text(encoding="utf-8")
exec(compile(_src, str(_core), "exec"), globals())
