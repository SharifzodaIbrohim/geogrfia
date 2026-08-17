"""Geografia entry — Phase A: plain server_core preferred.

Boot order:
  1) server_core.py if present and valid (plain source)
  2) materialize server_core.py from _srv_b64_*.txt once, then exec
  3) fail if neither works

After first successful boot, server_core.py exists as readable Python.
Safety-net patches follow.
"""
from __future__ import annotations

import base64
import zlib
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
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
    """Write plain server_core.py from b64 chunks (one-time)."""
    src = _load_b64_src()
    if "app = Flask" not in src and "app=Flask" not in src:
        raise RuntimeError("b64 payload has no Flask app")
    out = _dir / "server_core.py"
    out.write_text(src, encoding="utf-8")
    print(f"[boot] materialized {out.name} ({len(src)} chars)")
    return out


# --- 1) Plain server_core.py ---
_core = _dir / "server_core.py"
if _core.is_file() and _core.stat().st_size > 10000:
    try:
        _exec_src(_core.read_text(encoding="utf-8"), "server_core.py (plain)")
    except Exception as e:
        print("[boot] plain server_core.py failed:", e)

# --- 2) Materialize from b64, then plain exec ---
if app is None:
    try:
        _core = _materialize_core_from_b64()
        _exec_src(_core.read_text(encoding="utf-8"), "server_core.py (from b64)")
    except Exception as e:
        raise RuntimeError(f"Phase A boot failed: {e}") from e

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
            "js/admin-olympiad.js",
            "js/admin-students-reg.js",
            "js/admin-rbac-ui.js",
            "js/admin-session.js",
            "js/admin-audit.js",
            "js/student.js",
            "js/admin.js",
            "profile.html",
            "quiz.html",
            "courses.html",
            "leaderboard.html",
            "student.html",
            "admin.html",
            "countries.html",
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
            print(f"[boot] {name} try {mod}: {e}")
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
    from flask import jsonify, request

    # student login: accept studentId | id | code
    for ep_name in list(app.view_functions.keys()):
        if "student" in ep_name.lower() and "login" in ep_name.lower():
            orig = app.view_functions[ep_name]

            def student_login_wrap(*args, _orig=orig, **kwargs):
                data = request.get_json(silent=True) or {}
                if isinstance(data, dict):
                    code = data.get("studentId") or data.get("id") or data.get("code")
                    if code is not None:
                        data = dict(data)
                        data["id"] = code
                        data["studentId"] = code
                        data["code"] = code
                        try:
                            request.json = data  # type: ignore
                        except Exception:
                            pass
                return _orig(*args, **kwargs)

            app.view_functions[ep_name] = student_login_wrap
            print("[boot] safety-net: student_login id|studentId|code")
            break

    # /api/student/olympiads if missing
    if "/api/student/olympiads" not in [str(r) for r in app.url_map.iter_rules()]:

        @app.get("/api/student/olympiads")
        def student_olympiads_list():
            sid = request.args.get("studentId") or request.args.get("id")
            if not sid:
                body = request.get_json(silent=True) or {}
                sid = body.get("studentId") or body.get("id")
            if not sid:
                return jsonify({"ok": False, "error": "studentId required"}), 400
            try:
                from db import repo

                olympiads = []
                for key in ("list_active_olympiads", "get_active_olympiads", "list_olympiads"):
                    fn = getattr(repo, key, None)
                    if callable(fn):
                        try:
                            olympiads = fn() or []
                            break
                        except Exception:
                            pass
                out = [o for o in olympiads if isinstance(o, dict)]
                return jsonify({"ok": True, "olympiads": out, "studentId": str(sid)})
            except Exception as e:
                return jsonify({"ok": False, "error": str(e)}), 500

        print("[boot] safety-net: /api/student/olympiads")

    try:
        for rule in list(app.url_map.iter_rules()):
            if "DELETE" in (rule.methods or set()) and "student" in rule.rule.lower() and "<" in rule.rule:
                ep = rule.endpoint
                orig = app.view_functions.get(ep)
                if not orig:
                    continue

                def make_wrapper(original):
                    def delete_safe(student_id=None, **kw):
                        sid = student_id or kw.get("id") or kw.get("student_id")
                        if sid:
                            try:
                                from db import repo

                                if hasattr(repo, "soft_delete_student"):
                                    repo.soft_delete_student(str(sid))
                                elif hasattr(repo, "update_student"):
                                    repo.update_student(str(sid), {"status": "inactive"})
                                return jsonify({"ok": True, "status": "inactive"})
                            except Exception as e:
                                return jsonify({"ok": False, "error": str(e)}), 500
                        return original(student_id, **kw) if student_id is not None else original(**kw)

                    return delete_safe

                app.view_functions[ep] = make_wrapper(orig)
                print(f"[boot] safety-net: soft-delete {ep}")
                break
    except Exception as e:
        print("[boot] soft-delete skip:", e)
    print("[boot] safety-net OK")


try:
    _install_safety_net()
except Exception as e:
    print("[boot] safety-net failed:", e)

# Guarantee gunicorn can find app
if app is None:
    raise RuntimeError("Flask app not loaded — check server_core.py / _srv_b64")
print("[boot] ready for gunicorn server:app")
