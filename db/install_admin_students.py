"""
Hardened /api/admin/students GET+POST for PostgreSQL.

Create uses explicit UUID + long numeric student_code to avoid 500s.
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
            return jsonify({"ok": True, "student": st}), 201
        except Exception as e:
            log.exception("create student failed: %s", e)
            return jsonify({
                "error": "Сохтани хонанда ноком шуд.",
                "detail": str(e)[:240],
            }), 500

    # Point every existing rule for this path at our handler
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

    log.info("admin students hardened")
    print("[boot] admin students: create/list OK")
