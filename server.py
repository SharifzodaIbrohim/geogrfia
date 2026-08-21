"""Geografia entry — Phase A: plain server_core.py preferred (no network at boot)."""
from __future__ import annotations

import base64
import zlib
from pathlib import Path

# Ubuntu / local: load .env before server_core imports connection
try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent / ".env", override=False)
except Exception:
    pass

_dir = Path(__file__).resolve().parent
_boot_mode = None
app = None


def _exec_src(src: str, label: str) -> None:
    global app, _boot_mode
    g = globals()
    exec(compile(src, "server_core.py", "exec"), g)
    if g.get("app") is None:
        raise RuntimeError(f"{label}: Flask app not defined")
    app = g["app"]
    _boot_mode = label
    print(f"[boot] Phase A: {label} OK")


def _load_b64_src() -> str:
    parts = sorted(_dir.glob("_srv_b64_*.txt"))
    if not parts:
        raise RuntimeError("no _srv_b64_*.txt")
    raw = "".join(p.read_text(encoding="utf-8").strip() for p in parts)
    return zlib.decompress(base64.b64decode(raw)).decode("utf-8")


def _materialize_core_from_b64() -> Path:
    src = _load_b64_src()
    if "app = Flask" not in src and "app=Flask" not in src:
        raise RuntimeError("b64 payload has no Flask app")
    out = _dir / "server_core.py"
    out.write_text(src, encoding="utf-8")
    print(f"[boot] materialized {out.name} ({len(src)} chars)")
    return out


_core = _dir / "server_core.py"
if _core.is_file() and _core.stat().st_size > 10000:
    try:
        _exec_src(_core.read_text(encoding="utf-8"), "server_core.py (plain)")
    except Exception as e:
        print("[boot] plain server_core.py failed:", e)

if app is None:
    try:
        _core = _materialize_core_from_b64()
        _exec_src(_core.read_text(encoding="utf-8"), "server_core.py (from b64)")
    except Exception as e:
        raise RuntimeError(f"Phase A boot failed: {e}") from e

print(f"[boot] mode={_boot_mode}")

_EXTRA_PUBLIC = {
    "index.html",
    "admin.html",
    "student.html",
    "profile.html",
    "quiz.html",
    "courses.html",
    "leaderboard.html",
    "countries.html",
    "css.css",
    "css/admin.css",
    "css/student.css",
    "css/quiz.css",
    "css/platform.css",
    "css/profile.css",
    "js.js",
    "js/i18n.js",
    "js/platform-home.js",
    "js/quiz-platform.js",
    "js/profile.js",
    "js/admin.js",
    "js/admin-session.js",
    "js/admin-fixes.js",
    "js/admin-gmail.js",
    "js/admin-content.js",
    "js/admin-leaderboard.js",
    "js/admin-students-reg.js",
    "js/admin-olympiad.js",
    "js/admin-audit.js",
    "js/admin-rbac-ui.js",
}

try:
    PUBLIC_PATHS.update(_EXTRA_PUBLIC)  # noqa: F821
    print("[boot] PUBLIC_PATHS: current static set OK")
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
    if last is not None:
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
_boot_patch("patch_score_text", "patch_score_text", "db.patch_score_text")
_boot_patch("force_olympiad_routes", "force_olympiad_routes", "db.force_olympiad_routes")


def _install_safety_net() -> None:
    from flask import request

    if "student_login" in app.view_functions:
        _orig = app.view_functions["student_login"]

        def student_login_safe():
            data = request.get_json(silent=True) or {}
            sid = data.get("id") or data.get("studentId") or data.get("code")
            if sid and not data.get("id"):
                try:
                    request._cached_json = (  # type: ignore
                        {**data, "id": str(sid).strip()},
                        {**data, "id": str(sid).strip()},
                    )
                except Exception:
                    pass
            return _orig()

        app.view_functions["student_login"] = student_login_safe
        print("[boot] safety-net: student_login id|studentId|code")

    print("[boot] safety-net OK")


try:
    _install_safety_net()
except Exception as e:
    print("[boot] safety-net failed:", e)
