"""Geografia entry — Phase 25.5.1 local-only (no remote exec, no network at boot)."""
from __future__ import annotations

import base64
import zlib
from pathlib import Path

_dir = Path(__file__).resolve().parent


def _load() -> str:
    errors = []

    # 1) Prefer plain server_core.py (reliable, no corruption risk)
    core = _dir / "server_core.py"
    if core.is_file():
        try:
            return core.read_text(encoding="utf-8")
        except Exception as e:
            errors.append(f"server_core.py: {e}")

    # 2) Plain split parts
    py_parts = sorted(_dir.glob("server_core_part*.py"))
    if py_parts:
        try:
            return "".join(p.read_text(encoding="utf-8") for p in py_parts)
        except Exception as e:
            errors.append(f"parts: {e}")

    # 3) zlib+b64 chunks
    b64_parts = sorted(_dir.glob("_srv_b64_*.txt"))
    if b64_parts:
        try:
            return zlib.decompress(
                base64.b64decode(
                    "".join(p.read_text(encoding="utf-8").strip() for p in b64_parts)
                )
            ).decode("utf-8")
        except Exception as e:
            errors.append(f"b64: {e}")

    raise RuntimeError(
        "Phase 25.5.1: missing local payload "
        "(_srv_b64_*.txt | server_core_part*.py | server_core.py). "
        f"Tried: {errors}. No remote GitHub load."
    )


_src = _load()
exec(compile(_src, "server_core.py", "exec"), globals())


def _boot_patch(name: str, *modules: str) -> None:
    last = None
    for mod in modules:
        try:
            m = __import__(mod, fromlist=["install"])
            m.install(app)  # noqa: F821
            print(f"[boot] {name} via {mod}")
            return
        except Exception as e:
            last = e
    print(f"[boot] {name} failed:", last)


_boot_patch("patch_submit_p112", "db.patch_submit_p112", "patch_submit_p112")
_boot_patch("patch_student_portal", "db.patch_student_portal", "patch_student_portal")
_boot_patch("patch_admin_students", "db.patch_admin_students", "patch_admin_students")
