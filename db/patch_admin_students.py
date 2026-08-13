"""Admin soft-delete students (FK-safe)."""
from __future__ import annotations
import logging
from flask import jsonify, request
log = logging.getLogger("geografia.patch_admin_students")

def install(app) -> None:
    try:
        from db.repo import find_student_by_code, use_pg
        from db.connection import get_session, is_postgres_enabled
        from sqlalchemy import text
    except Exception as e:
        log.error("imports: %s", e)
        return

    def soft_delete(code: str) -> bool:
        code = (code or "").strip()
        if not code:
            return False
        try:
            pg = bool(is_postgres_enabled() or use_pg())
        except Exception:
            pg = False
        if pg:
            with get_session() as s:
                for sql in (
                    "UPDATE students SET status = 'inactive' WHERE student_code = :c",
                    "UPDATE students SET status = CAST('inactive' AS student_status) WHERE student_code = :c",
                ):
                    try:
                        res = s.execute(text(sql), {"c": code})
                        if res.rowcount and res.rowcount > 0:
                            return True
                    except Exception:
                        continue
                for sql in (
                    "DELETE FROM attempt_answers WHERE attempt_id IN (SELECT id FROM attempts WHERE student_code=:c OR student_id::text=:c)",
                    "DELETE FROM attempts WHERE student_code=:c OR student_id::text=:c",
                    "DELETE FROM olympiad_participants WHERE student_id::text=:c",
                    "DELETE FROM results WHERE student_id::text=:c OR student_code=:c",
                    "DELETE FROM students WHERE student_code=:c",
                ):
                    try:
                        s.execute(text(sql), {"c": code})
                    except Exception:
                        pass
                exists = s.execute(text("SELECT 1 FROM students WHERE student_code=:c LIMIT 1"), {"c": code}).first()
                return not bool(exists)
        try:
            from db.repo import STUDENTS_FILE, _load_json, _save_json
            items = _load_json(STUDENTS_FILE)
            new_items = [st for st in items if str(st.get("id")) != code]
            if len(new_items) == len(items):
                return False
            _save_json(STUDENTS_FILE, new_items)
            return True
        except Exception:
            return False

    def admin_student_delete(student_id: str):
        token = request.headers.get("X-Admin-Token") or ""
        admin = None
        try:
            from db.auth_tokens import admin_from_token
            from db.admin_role import enrich_admin
            admin = enrich_admin(admin_from_token(token))
        except Exception:
            try:
                from db.auth_tokens import admin_from_token
                admin = admin_from_token(token)
            except Exception:
                admin = None
        if not admin:
            return jsonify({"error": "Дастрасӣ рад шуд."}), 401
        code = (student_id or "").strip()
        if not code:
            return jsonify({"error": "ID лозим аст."}), 400
        try:
            ok = soft_delete(code)
            if not ok:
                st = find_student_by_code(code)
                if not st:
                    return jsonify({"ok": True, "deleted": code, "mode": "already_gone"})
                return jsonify({"error": "Хонанда ёфт нашуд."}), 404
            return jsonify({"ok": True, "deleted": code, "mode": "soft"})
        except Exception as e:
            log.exception("delete %s", code)
            return jsonify({"error": "Нест кардан ноком шуд.", "detail": str(e)[:200]}), 500

    for r in list(app.url_map.iter_rules()):
        if "students" in r.rule and "DELETE" in (r.methods or set()):
            app.view_functions[r.endpoint] = admin_student_delete
    for ep in ("admin_delete_student", "admin_student_delete_code", "admin_student_delete_id"):
        if ep in app.view_functions:
            app.view_functions[ep] = admin_student_delete
    try:
        from db import repo
        repo.delete_student = soft_delete
    except Exception:
        pass
    print("[boot] patch_admin_students: soft-delete installed")
