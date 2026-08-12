"""Geografia entry — Phase 25.5.1 local-only (no remote exec, no network at boot)."""
from __future__ import annotations

from pathlib import Path

_dir = Path(__file__).resolve().parent
_parts = sorted(_dir.glob("server_core_part*.py"))
if not _parts:
    _core = _dir / "server_core.py"
    if not _core.is_file():
        raise RuntimeError(
            "missing server_core_part*.py / server_core.py — Phase 25.5.1 local payload required. "
            "No remote GitHub load."
        )
    _src = _core.read_text(encoding="utf-8")
else:
    _src = "".join(p.read_text(encoding="utf-8") for p in _parts)
exec(compile(_src, "server_core.py", "exec"), globals())
