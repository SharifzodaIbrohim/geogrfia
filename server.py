"""Geografia entry — Phase A: plain source first (server_core.py or server_core_part*.py).

Boot order:
  1) server_core.py (single plain file)
  2) server_core_part*.py (joined plain parts)
  3) _srv_b64_*.txt (legacy fallback only)
Then safety-net patches.
"""
from __future__ import annotations

import base64
import zlib
from pathlib import Path

_dir = Path(__file__).resolve().parent
_boot_mode = None
app = None  # set by loaders


def _exec_src(src: str, label: str) -> None:
    global app, _boot_mode
    g = globals()
    exec(compile(src, "server_core.py", "exec"), g)
    if g.get("app") is None:
        raise RuntimeError(f"{label}: Flask app not defined")
    app = g["app"]
    _boot_mode = label
    print(f"[boot] Phase A: {label} OK")


# 1) Single plain file
_core = _dir / "server_core.py"
if app is None and _core.is_file() and _core.stat().st_size > 10000:
    try:
        _exec_src(_core.read_text(encoding="utf-8"), "server_core.py")
    except Exception as e:
        print("[boot] server_core.py failed:", e)

# 2) Plain parts (readable, no b64)
if app is None:
    _parts = sorted(_dir.glob("server_core_part*.py"))
    if _parts and sum(p.stat().st_size for p in _parts) > 10000:
        try:
            _src = "".join(p.read_text(encoding="utf-8") for p in _parts)
            _exec_src(_src, f"parts×{len(_parts)}")
        except Exception as e:
            print("[boot] parts failed:", e)

# 3) Legacy b64 fallback
if app is None:
    try:
        _b64 = sorted(_dir.glob("_srv_b64_*.txt"))
        if not _b64:
            raise RuntimeError("no _srv_b64_*.txt")
        _raw = "".join(p.read_text(encoding="utf-8").strip() for p in _b64)
        _src = zlib.decompress(base64.b64decode(_raw)).decode("utf-8")
        _exec_src(_src, "b64-fallback")
    except Exception as e:
        raise RuntimeError(f"Phase A boot failed (plain + parts + b64): {e}") from e

print(f"[boot] mode={_boot_mode}")

# --- PUBLIC_PATHS ---
try:
    PUBLIC_PATHS.update(  # noqa: F821
        {
            "css/student.css",
            "css/quiz.css",
            "css/platform.css",
            "css/profile.css",
            "js/i18n.js",
            "js/platform-home.js",
            "js/quiz-platform.js",
            "js/profile.js",
            "js/admin-fixes.js",
            "js/admin-gmail.js",
            "js/admin-content.js",
            "js/admin-leaderboard.js",
            "profile.html",
            "quiz.html",
            "courses.html",
            "leaderboard.html",
            "student.html",
            "admin.html",
            "countries.html",
            "js/student.js",
            "js/admin.js",
            "js/admin-session.js",
            "js/admin-students-reg.js",
            "js/admin-olympiad.js",
            "js/admin-rbac-ui.js",
            "js/admin-audit.js",
        }
    )
    print("[boot] PUBLIC_PATHS: student.css + assets allowed")
except Exception as e:
    print("[boot] PUBLIC_PATHS update failed:", e)


def _boot_patch(name: str, *modules: str) -> None:
    last = None
    for mod in modules:
        try:
            m = __import__(mod, fromlist=["install"])
            install = getattr(m, "install", None)
            if install is None:
                continue
            try:
                install(app)
            except TypeError:
                install()
            print(f"[boot] {name} via {mod}")
            return
        except Exception as e:
            last = e
    if last:
        print(f"[boot] {name} failed:", last)


_boot_patch("one_attempt", "one_attempt", "db.one_attempt")
_boot_patch("patch_submit_p112", "patch_submit_p112", "db.patch_submit_p112")
_boot_patch("patch_student_portal", "patch_student_portal", "db.patch_student_portal")
_boot_patch("patch_admin_students", "patch_admin_students", "db.patch_admin_students")
_boot_patch("patch_names", "patch_names", "db.patch_names")
_boot_patch("patch_students_profile", "patch_students_profile", "db.patch_students_profile")
_boot_patch("patch_olympiad_builder", "patch_olympiad_builder", "db.patch_olympiad_builder")
_boot_patch("patch_olympiad_questions_pg", "patch_olympiad_questions_pg", "db.patch_olympiad_questions_pg")
_boot_patch("patch_ui_batch", "patch_ui_batch", "db.patch_ui_batch")


def _install_safety_net() -> None:
    print("[boot] safety-net OK")


try:
    _install_safety_net()
except Exception as e:
    print("[boot] safety-net failed:", e)
