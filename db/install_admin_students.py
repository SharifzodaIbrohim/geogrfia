"""
Hardened /api/admin/students GET + POST + DELETE + audit (P1.9).
"""
from __future__ import annotations

import logging
import secrets
import uuid

from flask import jsonify, request
from sqlalchemy import text

log = logging.getLogger("geografia.admin_students")


def _gen_student_code() -> str:
    n = secrets.randbelow(9 * 10**18) + 10**18
    return str(n)


def _client_ip() -> str:
    xff = (request.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
    return xff or (request.remote_addr or "")


def _current_admin() -> dict | None:
    try:
        from db.session_cookies import current_admin

        return current_admin(request)
    except Exception:
        return None


def _audit(action: str, target_id: str | None = None, meta: dict | None = None) -> None:
    try:
        from db.audit import log_action

        log_action(
            action=action,
            admin=_current_admin(),
            target_type="student",
            target_id=target_id,
            meta=meta or {},
            ip=_client_ip(),
        )
    except Exception as e:
        log.warning("audit failed action=%s: %s", action, e)


def install(app) -> None:
    from db.connection import get_session, is_postgres_enabled
    from db.repo import find_student_by_code, list_students, use_pg, create_student as repo_create

    def create_one(full_name: str, class_name: str, school: str, created_by: str = "") -> dict:
        code = _gen_student_code()
        for _ in range(8):
            if not find_student_by_code(code):
                break
            code = _gen_student_code()

        if is_postgres_enabled() or use_pg():
            sid = str(uuid.uuid4())
            with get_session() as s:
                s.execute(
                    text(
                        "INSERT INTO students "
                        "(id, student_code, full_name, class_name, school_name, status, created_by) "
                        "VALUES (:id, :c, :n, :cl, :sch, CAST(:st AS student_status), :by)"
                    ),
                    {
                        "id": sid,
                        "c": code,
                        "n": full_name,
                        "cl": class_name,
                        "sch": school or "",
                        "st": "active",
                        "by": created_by or None,
                    },
                )
            st = find_student_by_code(code)
            return st or {
                "id": code,
                "fullName": full_name,
                "className": class_name,
                "school": school or "",
                "status": "active",
            }

        return repo_create(code, full_name, class_name, school, created_by)

    def delete_one(code: str) -> bool:
        code = (code or "").strip()
        if not code:
            return False
        if is_postgres_enabled() or use_pg():
            with get_session() as s:
                res = s.execute(
                    text(
                        "UPDATE students SET status = CAST('inactive' AS student_status) "
                        "WHERE student_code = :c AND status = CAST('active' AS student_status)"
                    ),
                    {"c": code},
                )
                if res.rowcount and res.rowcount > 0:
                    return True
                exists = s.execute(
                    text("SELECT 1 FROM students WHERE student_code = :c LIMIT 1"),
                    {"c": code},
                ).first()
                return bool(exists)
        from db.repo import STUDENTS_FILE, _load_json, _save_json

        items = _load_json(STUDENTS_FILE)
        new_items = [st for st in items if str(st.get("id")) != code]
        found = len(new_items) != len(items)
        if found:
            _save_json(STUDENTS_FILE, new_items)
        return found

    def admin_students():
        if request.method == "GET":
            try:
                return jsonify({"students": list_students()})
            except Exception as e:
                log.exception("list students")
                return jsonify({"students": [], "error": str(e)[:160]}), 500

        payload = request.get_json(silent=True) or {}
        full_name = str(payload.get("fullName") or payload.get("name") or "").strip()
        class_name = str(payload.get("className") or payload.get("class") or "").strip()
        school = str(payload.get("school") or payload.get("schoolName") or "").strip()

        if not full_name:
            return jsonify({"error": "Ному насабро ворид кунед."}), 400
        if not class_name:
            return jsonify({"error": "Синфро ворид кунед."}), 400
        if not school:
            return jsonify({"error": "Мактабро ворид кунед."}), 400

        try:
            st = create_one(full_name, class_name, school)
            _audit(
                "CREATE_STUDENT",
                target_id=st.get("id"),
                meta={"fullName": full_name, "className": class_name, "school": school},
            )
            return jsonify({"ok": True, "student": st}), 201
        except Exception as e:
            log.exception("create student failed: %s", e)
            return jsonify({
                "error": "Сохтани хонанда ноком шуд.",
                "detail": str(e)[:240],
            }), 500

    def admin_student_delete(student_id: str):
        code = (student_id or "").strip()
        if not code:
            return jsonify({"error": "ID лозим аст."}), 400
        try:
            ok = delete_one(code)
            if not ok:
                return jsonify({"error": "Хонанда ёфт нашуд."}), 404
            _audit("DELETE_STUDENT", target_id=code, meta={"mode": "soft"})
            return jsonify({"ok": True, "deleted": code, "mode": "soft"})
        except Exception as e:
            log.exception("delete student %s: %s", code, e)
            return jsonify({
                "error": "Нест кардан ноком шуд.",
                "detail": str(e)[:240],
            }), 500

    for r in list(app.url_map.iter_rules()):
        if r.rule == "/api/admin/students":
            app.view_functions[r.endpoint] = admin_students

    try:
        app.add_url_rule(
            "/api/admin/students",
            "admin_students_hardened",
            admin_students,
            methods=["GET", "POST"],
        )
    except AssertionError:
        app.view_functions["admin_students_hardened"] = admin_students

    for path, ep in [
        ("/api/admin/students/<student_id>", "admin_student_delete_code"),
        ("/api/admin/students/<id>", "admin_student_delete_id"),
    ]:
        try:
            app.add_url_rule(path, ep, admin_student_delete, methods=["DELETE"])
        except AssertionError:
            for r in list(app.url_map.iter_rules()):
                if r.rule == path:
                    app.view_functions[r.endpoint] = admin_student_delete

    print("[boot] admin students: create/list/delete + audit")
