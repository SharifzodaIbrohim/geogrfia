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
            txt = core.read_text(encoding="utf-8")
            # Reject obvious placeholders / truncated payloads
            if "def student_login" in txt and "Flask" in txt and len(txt) > 5000:
                return txt
            errors.append("server_core.py: too short or missing student_login")
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

# Hard safety net: student login accepts studentId + /api/student/olympiads always present
try:
    from flask import jsonify, request
    from datetime import datetime, timezone
    from db import repo as _repo_fix

    def _student_login_safe():
        payload = request.get_json(silent=True) or {}
        code = str(
            payload.get("studentId") or payload.get("id") or payload.get("code") or ""
        ).strip()
        if not code:
            return jsonify({"error": "ID-и хонанда лозим аст."}), 400
        st = _repo_fix.find_student_by_code(code)
        if not st:
            return jsonify({"error": "ID нодуруст аст ё хонанда ёфт нашуд."}), 401
        return jsonify({"ok": True, "student": {
            "id": st.get("id"),
            "fullName": st.get("fullName"),
            "className": st.get("className"),
            "school": st.get("school") or "",
        }})

    def _student_olympiads_safe():
        code = str(
            request.args.get("studentId")
            or request.args.get("id")
            or request.headers.get("X-Student-Id")
            or ""
        ).strip()
        if not code:
            return jsonify({"error": "studentId лозим аст.", "olympiads": [], "quizzes": []}), 400
        st = _repo_fix.find_student_by_code(code)
        if not st:
            return jsonify({"error": "Хонанда ёфт нашуд.", "olympiads": [], "quizzes": []}), 401
        olympiads, quizzes, seen = [], [], set()
        try:
            items = _repo_fix.list_olympiads() or []
        except Exception:
            items = []
        now = datetime.now(timezone.utc)

        def _win(o):
            if o.get("isActive") is False:
                return "closed"
            def parse(v):
                if not v:
                    return None
                if isinstance(v, datetime):
                    return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
                try:
                    s = str(v).replace("Z", "+00:00")
                    d = datetime.fromisoformat(s)
                    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
                except Exception:
                    return None
            start = parse(o.get("startTime") or o.get("start_at"))
            end = parse(o.get("endTime") or o.get("end_at"))
            if start and now < start:
                return "not_started"
            if end and now > end:
                return "ended"
            return "open"

        for o in items:
            oid = str(o.get("id") or "")
            if not oid or oid in seen or o.get("isActive") is False:
                continue
            seen.add(oid)
            window = _win(o)
            card = {
                "id": oid,
                "title": o.get("title") or "Бе ном",
                "description": o.get("description") or "",
                "type": (o.get("type") or "olympiad").lower(),
                "passScore": o.get("passScore") or 70,
                "questionCount": o.get("questionCount") or len(o.get("questions") or []),
                "isActive": True,
                "isOpen": window == "open",
                "windowStatus": window,
                "startTime": o.get("startTime"),
                "endTime": o.get("endTime"),
                "durationSec": o.get("durationSec"),
            }
            (quizzes if card["type"] == "quiz" else olympiads).append(card)
        return jsonify({
            "ok": True,
            "student": {
                "id": st.get("id"),
                "fullName": st.get("fullName"),
                "className": st.get("className"),
                "school": st.get("school") or "",
            },
            "olympiads": olympiads,
            "quizzes": quizzes,
        })

    def _admin_delete_student_safe(student_id: str):
        admin = None
        try:
            admin = require_admin()  # noqa: F821
        except Exception:
            admin = None
        if not admin:
            return jsonify({"error": "Дастрасӣ рад шуд."}), 401
        code = (student_id or "").strip()
        if not code:
            return jsonify({"error": "ID лозим аст."}), 400
        try:
            ok = _repo_fix.delete_student(code)
        except Exception as e:
            return jsonify({"error": "Нест кардан ноком шуд.", "detail": str(e)[:200]}), 500
        if not ok:
            st = _repo_fix.find_student_by_code(code)
            if not st:
                return jsonify({"ok": True, "deleted": code, "mode": "already_gone"})
            return jsonify({"error": "Хонанда ёфт нашуд."}), 404
        return jsonify({"ok": True, "deleted": code})

    # Override / register
    for ep in ("student_login", "student_portal_login"):
        if ep in app.view_functions:  # noqa: F821
            app.view_functions[ep] = _student_login_safe
    try:
        app.add_url_rule("/api/student/login", "student_portal_login", _student_login_safe, methods=["POST"])
    except Exception:
        pass
    if "student_login" in app.view_functions:  # noqa: F821
        app.view_functions["student_login"] = _student_login_safe

    for ep in ("student_portal_olympiads", "student_list_olympiads"):
        if ep in app.view_functions:  # noqa: F821
            app.view_functions[ep] = _student_olympiads_safe
    try:
        app.add_url_rule("/api/student/olympiads", "student_portal_olympiads", _student_olympiads_safe, methods=["GET"])
    except Exception:
        for r in list(app.url_map.iter_rules()):  # noqa: F821
            if r.rule == "/api/student/olympiads":
                app.view_functions[r.endpoint] = _student_olympiads_safe  # noqa: F821

    for r in list(app.url_map.iter_rules()):  # noqa: F821
        if "students" in r.rule and "DELETE" in (r.methods or set()):
            app.view_functions[r.endpoint] = _admin_delete_student_safe  # noqa: F821
    if "admin_delete_student" in app.view_functions:  # noqa: F821
        app.view_functions["admin_delete_student"] = _admin_delete_student_safe

    # Empty participant list open
    try:
        from db import student_access as _sa_fix
        def _open_access(olympiad_id, student_code):
            student_code = (student_code or "").strip()
            student = _repo_fix.find_student_by_code(student_code) if student_code else None
            if not student_code:
                return {"allowed": False, "reason": "student_id_required"}
            if student_code.startswith(("g:", "gmail:")) and not student:
                return {"allowed": False, "reason": "student_id_required"}
            if not student:
                return {"allowed": False, "reason": "student_not_found"}
            try:
                parts = _sa_fix.list_olympiad_participants(olympiad_id)
            except Exception:
                parts = []
            if parts:
                assigned = any(
                    str(p.get("id") or p.get("student_code") or "") == student_code
                    and p.get("status", "assigned") == "assigned"
                    for p in parts
                )
                if not assigned:
                    return {"allowed": False, "reason": "not_assigned"}
            return {"allowed": True, "reason": "open_or_assigned", "student": student}
        _sa_fix.student_has_olympiad_access = _open_access
    except Exception as e:
        print("[boot] access open failed:", e)

    print("[boot] safety-net: student login/olympiads/delete installed")
except Exception as e:
    print("[boot] safety-net failed:", e)
