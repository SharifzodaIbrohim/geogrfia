"""
Reliable admin student create/list for /api/admin/students.
Fixes 500 on create by using explicit UUID + student_code insert.
"""
from __future__ import annotations

import logging
import secrets
import uuid

from flask import jsonify, request
from sqlalchemy import text

log = logging.getLogger("geografia.admin_students")


def _gen_student_code() -> str:
    """Long numeric ID (similar to existing 19-digit codes)."""
    # 19 digits, avoid leading zero
    n = secrets.randbelow(9 * 10**18) + 10**18
    return str(n)


def install(app) -> None:
    from db.connection import get_session, is_postgres_enabled, use_pg if False else None  # noqa
    from db.connection import is_postgres_enabled, get_session
    from db.repo import list_students, find_student_by_code, use_pg

    def create_student_pg(full_name: str, class_name: str, school: str, created_by: str = "") -> dict:
        code = _gen_student_code()
        # ensure uniqueness (rare collision)
        for _ in range(5):
            if not find_student_by_code(code):
                break
            code = _gen_student_code()
        sid = str(uuid.uuid4())
        with get_session() as s:
            s.execute(
                text(
                    "INSERT INTO students "
                    "(id, student_code, full_name, class_name, school_name, status, created_by) "
                    "VALUES (:id, :c, :n, :cl, :sch, 'active', :by)"
                ),
                {
                    "id": sid,
                    "c": code,
                    "n": full_name,
                    "cl": class_name,
                    "sch": school or "",
                    "by": created_by or None,
                },
            )
        st = find_student_by_code(code)
        if st:
            return st
        return {
            "id": code,
            "fullName": full_name,
            "className": class_name,
            "school": school or "",
            "status": "active",
        }

    def admin_create_student():
        # Auth: cookie or header (session bridge already in before_request)
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
            if is_postgres_enabled() or use_pg():
                st = create_student_pg(full_name, class_name, school)
            else:
                from db.repo import create_student

                code = _gen_student_code()
                st = create_student(code, full_name, class_name, school)
            return jsonify({"ok": True, "student": st}), 201
        except Exception as e:
            log.exception("create student failed")
            return jsonify({
                "error": "Сохтани хонанда ноком шуд.",
                "detail": str(e)[:200],
            }), 500

    def admin_list_students():
        try:
            items = list_students()
            return jsonify({"students": items})
        except Exception as e:
            log.exception("list students")
            return jsonify({"students": [], "error": str(e)[:120]}), 500

    # Replace existing handlers for these paths
    for rule, ep, fn, methods in [
        ("/api/admin/students", "admin_list_students_v2", admin_list_students, ["GET"]),
        ("/api/admin/students", "admin_create_student_v2", admin_create_student, ["POST"]),
    ]:
        replaced = False
        for r in list(app.url_map.iter_rules()):
            if r.rule == rule and set(methods) & (r.methods or set()):
                # same path may share endpoint for GET+POST — only replace matching methods carefully
                if set(methods).issubset(r.methods or set()) or (r.methods & set(methods)):
                    # If endpoint handles both GET and POST, we need separate rules
                    pass
        # Prefer add_url_rule with unique endpoints; remove conflicting by overriding view
        try:
            app.add_url_rule(rule, ep, fn, methods=methods)
            replaced = True
        except AssertionError:
            # Endpoint or rule exists — force view_functions
            if ep in app.view_functions:
                app.view_functions[ep] = fn
                replaced = True
            else:
                for r in list(app.url_map.iter_rules()):
                    if r.rule == rule and (set(methods) & (r.methods or set())):
                        # Can't easily split methods; replace the view for that endpoint
                        # Only if methods match exactly or POST-only handler needed
                        if methods == ["POST"] and "POST" in (r.methods or set()) and "GET" in (r.methods or set()):
                            # Combined GET+POST endpoint — wrap both
                            old = app.view_functions.get(r.endpoint)

                            def _combo(old_fn=old, post_fn=fn if methods == ["POST"] else None):
                                if request.method == "POST":
                                    return admin_create_student()
                                if old_fn:
                                    return old_fn()
                                return admin_list_students()

                            app.view_functions[r.endpoint] = (
                                (lambda: admin_create_student())
                                if methods == ["POST"]
                                else fn
                            )
                            # Better combined wrapper:
                            def make_wrapper(endpoint_name):
                                def wrapped(*a, **k):
                                    if request.method == "POST":
                                        return admin_create_student()
                                    return admin_list_students()
                                wrapped.__name__ = endpoint_name
                                return wrapped

                            app.view_functions[r.endpoint] = make_wrapper(r.endpoint)
                            replaced = True
                            break
                        app.view_functions[r.endpoint] = fn
                        replaced = True
                        break

    # Cleaner approach: always install a combined handler last
    def admin_students():
        if request.method == "POST":
            return admin_create_student()
        return admin_list_students()

    for r in list(app.url_map.iter_rules()):
        if r.rule == "/api/admin/students":
            app.view_functions[r.endpoint] = admin_students

    try:
        if "admin_students_combo" not in app.view_functions:
            app.add_url_rule(
                "/api/admin/students",
                "admin_students_combo",
                admin_students,
                methods=["GET", "POST"],
            )
    except AssertionError:
        pass

    log.info("admin students create/list installed")
    print("[boot] admin students: create/list hardened")
