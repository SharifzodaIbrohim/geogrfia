"""Geografia entry — Phase 25.5.1 local-only (no remote exec, no network at boot).
Payload: _srv_b64_*.txt restored from live commit dedc114 (2026-08-13).
"""
from __future__ import annotations

import base64
import zlib
from pathlib import Path

_dir = Path(__file__).resolve().parent


def _load() -> str:
    errors = []
    b64_parts = sorted(_dir.glob("_srv_b64_*.txt"))
    if b64_parts:
        try:
            raw = "".join(p.read_text(encoding="utf-8").strip() for p in b64_parts)
            src = zlib.decompress(base64.b64decode(raw)).decode("utf-8")
            if "app = Flask" in src or "app=Flask" in src:
                return src
            errors.append("b64: no Flask app")
        except Exception as e:
            errors.append(f"b64: {e}")
    py_parts = sorted(_dir.glob("server_core_part*.py"))
    if py_parts:
        try:
            src = "".join(p.read_text(encoding="utf-8") for p in py_parts)
            if len(src) > 10000 and ("app = Flask" in src or "app=Flask" in src):
                return src
            errors.append("parts: too short or no Flask app")
        except Exception as e:
            errors.append(f"parts: {e}")
    core = _dir / "server_core.py"
    if core.is_file():
        try:
            src = core.read_text(encoding="utf-8")
            if len(src) > 10000 and ("app = Flask" in src or "app=Flask" in src):
                return src
            errors.append("server_core.py: invalid")
        except Exception as e:
            errors.append(f"server_core.py: {e}")
    raise RuntimeError(
        "Phase 25.5.1: missing local payload. Tried: " + "; ".join(errors)
    )


_src = _load()
exec(compile(_src, "server_core.py", "exec"), globals())

if "app" not in globals() or app is None:  # noqa: F821
    raise RuntimeError("Phase 25.5.1: payload loaded but Flask app not defined")


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
    if last is not None:
        print(f"[boot] {name} failed:", last)


_boot_patch("one_attempt", "one_attempt", "db.one_attempt")
_boot_patch("patch_submit_p112", "patch_submit_p112", "db.patch_submit_p112")
_boot_patch("patch_student_portal", "patch_student_portal", "db.patch_student_portal")
_boot_patch("patch_admin_students", "patch_admin_students", "db.patch_admin_students")


def _install_safety_net() -> None:
    from flask import request, jsonify

    if "student_login" in app.view_functions:  # noqa: F821
        _orig = app.view_functions["student_login"]  # noqa: F821

        def student_login_safe():
            data = request.get_json(silent=True) or {}
            sid = data.get("id") or data.get("studentId") or data.get("code")
            if sid and not data.get("id"):
                try:
                    request._cached_json = ({**data, "id": str(sid).strip()}, {**data, "id": str(sid).strip()})  # type: ignore
                except Exception:
                    pass
            return _orig()

        app.view_functions["student_login"] = student_login_safe  # noqa: F821
        print("[boot] safety-net: student_login id|studentId|code")

    rules = [r.rule for r in app.url_map.iter_rules()]  # noqa: F821
    if not any("/api/student/olympiads" in r for r in rules):

        @app.post("/api/student/olympiads")  # noqa: F821
        def student_olympiads_safe():
            data = request.get_json(silent=True) or {}
            sid = data.get("studentId") or data.get("id") or data.get("code")
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
                out = []
                for o in olympiads:
                    if isinstance(o, dict):
                        out.append(o)
                    else:
                        out.append({
                            "id": getattr(o, "id", None),
                            "title": getattr(o, "title", None) or getattr(o, "name", None),
                            "type": getattr(o, "type", "olympiad"),
                            "status": getattr(o, "status", "active"),
                        })
                return jsonify({"ok": True, "olympiads": out, "studentId": str(sid)})
            except Exception as e:
                return jsonify({"ok": False, "error": str(e)}), 500

        print("[boot] safety-net: /api/student/olympiads")

    try:
        for rule in list(app.url_map.iter_rules()):  # noqa: F821
            if "DELETE" in (rule.methods or set()) and "student" in rule.rule.lower() and "<" in rule.rule:
                ep = rule.endpoint
                orig = app.view_functions.get(ep)  # noqa: F821
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

                app.view_functions[ep] = make_wrapper(orig)  # noqa: F821
                print(f"[boot] safety-net: soft-delete {ep}")
                break
    except Exception as e:
        print("[boot] soft-delete skip:", e)
    print("[boot] safety-net OK")


try:
    _install_safety_net()
except Exception as e:
    print("[boot] safety-net failed:", e)
