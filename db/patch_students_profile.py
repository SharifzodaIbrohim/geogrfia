"""Student profile registration fields + ensure PG columns."""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

from flask import jsonify, request

log = logging.getLogger("geografia.patch_students_profile")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _compose_full_name(last_name: str, first_name: str, patronymic: str, fallback: str = "") -> str:
    parts = [p for p in [last_name.strip(), first_name.strip(), patronymic.strip()] if p]
    if parts:
        return " ".join(parts)
    return (fallback or "").strip()


def ensure_student_profile_columns() -> None:
    try:
        from db.repo import use_pg
        from db.connection import get_session
        from sqlalchemy import text

        if not use_pg():
            return
        with get_session() as s:
            for col, typ in [
                ("last_name", "TEXT"),
                ("first_name", "TEXT"),
                ("patronymic", "TEXT"),
                ("birth_date", "DATE"),
                ("address", "TEXT"),
                ("teacher_name", "TEXT"),
                ("photo_data", "TEXT"),
            ]:
                s.execute(text(f"ALTER TABLE students ADD COLUMN IF NOT EXISTS {col} {typ}"))
        log.info("student profile columns ensured")
        print("[boot] students profile columns OK")
    except Exception as e:
        log.warning("ensure student profile columns: %s", e)


def _row_public(r: dict) -> dict:
    full = r.get("fullName") or r.get("full_name") or ""
    return {
        "id": r.get("id") or r.get("student_code"),
        "fullName": full,
        "lastName": r.get("lastName") or r.get("last_name") or "",
        "firstName": r.get("firstName") or r.get("first_name") or "",
        "patronymic": r.get("patronymic") or "",
        "birthDate": r.get("birthDate") or (str(r.get("birth_date") or "")[:10] if r.get("birth_date") else ""),
        "address": r.get("address") or "",
        "className": r.get("className") or r.get("class_name") or "",
        "school": r.get("school") or r.get("school_name") or "",
        "teacher": r.get("teacher") or r.get("teacher_name") or "",
        "hasPhoto": bool(r.get("photo_data") or r.get("photoData") or r.get("hasPhoto")),
        "photoData": r.get("photoData") if r.get("photoData") else None,
        "createdAt": r.get("createdAt"),
        "status": r.get("status") or "active",
    }


def install(app=None) -> None:
    ensure_student_profile_columns()

    from db import repo
    from db.connection import get_session
    from sqlalchemy import text

    _orig_list = repo.list_students
    _orig_create = repo.create_student
    _orig_find = repo.find_student_by_code

    def list_students() -> list:
        if repo.use_pg():
            try:
                with get_session() as s:
                    rows = s.execute(text(
                        "SELECT student_code, full_name, last_name, first_name, patronymic, "
                        "birth_date, address, class_name, school_name, teacher_name, "
                        "CASE WHEN photo_data IS NOT NULL AND length(photo_data) > 10 THEN true ELSE false END AS has_photo, "
                        "status, created_at "
                        "FROM students WHERE status = 'active' ORDER BY full_name"
                    )).mappings().all()
                    out = []
                    for r in rows:
                        out.append(_row_public({
                            "id": r["student_code"],
                            "fullName": r["full_name"],
                            "lastName": r.get("last_name"),
                            "firstName": r.get("first_name"),
                            "patronymic": r.get("patronymic"),
                            "birthDate": r["birth_date"].isoformat() if r.get("birth_date") else "",
                            "address": r.get("address"),
                            "className": r.get("class_name"),
                            "school": r.get("school_name") or "",
                            "teacher": r.get("teacher_name") or "",
                            "hasPhoto": bool(r.get("has_photo")),
                            "createdAt": r["created_at"].isoformat() if r.get("created_at") else None,
                            "status": r.get("status") or "active",
                        }))
                    return out
            except Exception as e:
                log.warning("list_students profile: %s", e)
                return [_row_public(x) for x in _orig_list()]
        return [_row_public(x) for x in _orig_list()]

    def find_student_by_code(code: str):
        code = (code or "").strip()
        if not code:
            return None
        if repo.use_pg():
            try:
                with get_session() as s:
                    r = s.execute(text(
                        "SELECT student_code, full_name, last_name, first_name, patronymic, "
                        "birth_date, address, class_name, school_name, teacher_name, photo_data, "
                        "status, user_id, created_at "
                        "FROM students WHERE student_code = :c AND status = 'active'"
                    ), {"c": code}).mappings().first()
                    if not r:
                        return None
                    return _row_public({
                        "id": r["student_code"],
                        "fullName": r["full_name"],
                        "lastName": r.get("last_name"),
                        "firstName": r.get("first_name"),
                        "patronymic": r.get("patronymic"),
                        "birthDate": r["birth_date"].isoformat() if r.get("birth_date") else "",
                        "address": r.get("address"),
                        "className": r.get("class_name"),
                        "school": r.get("school_name") or "",
                        "teacher": r.get("teacher_name") or "",
                        "photoData": r.get("photo_data"),
                        "hasPhoto": bool(r.get("photo_data")),
                        "status": r.get("status") or "active",
                        "userId": str(r["user_id"]) if r.get("user_id") else None,
                    })
            except Exception as e:
                log.warning("find_student profile: %s", e)
                st = _orig_find(code)
                return _row_public(st) if st else None
        st = _orig_find(code)
        return _row_public(st) if st else None

    def create_student(code: str, full_name: str, class_name: str, school: str, created_by: str = "", **extra) -> dict:
        last_name = (extra.get("last_name") or extra.get("lastName") or "").strip()
        first_name = (extra.get("first_name") or extra.get("firstName") or "").strip()
        patronymic = (extra.get("patronymic") or "").strip()
        birth_date = (extra.get("birth_date") or extra.get("birthDate") or "").strip() or None
        address = (extra.get("address") or "").strip()
        teacher = (extra.get("teacher") or extra.get("teacher_name") or "").strip()
        photo_data = extra.get("photo_data") or extra.get("photoData") or None
        if photo_data and isinstance(photo_data, str) and len(photo_data) > 2_500_000:
            photo_data = photo_data[:2_500_000]
        full_name = _compose_full_name(last_name, first_name, patronymic, full_name)
        code = (code or "").strip()

        if repo.use_pg():
            try:
                with get_session() as s:
                    s.execute(text(
                        "INSERT INTO students ("
                        " student_code, full_name, last_name, first_name, patronymic, "
                        " birth_date, address, class_name, school_name, teacher_name, "
                        " photo_data, status, created_by"
                        ") VALUES ("
                        " :c, :n, :ln, :fn, :pat, "
                        " :bd, :addr, :cl, :sch, :tea, "
                        " :photo, 'active', :cb"
                        ")"
                    ), {
                        "c": code, "n": full_name, "ln": last_name or None, "fn": first_name or None,
                        "pat": patronymic or None, "bd": birth_date, "addr": address or None,
                        "cl": class_name, "sch": school or "", "tea": teacher or None,
                        "photo": photo_data, "cb": created_by or None,
                    })
                st = find_student_by_code(code)
                return st or _row_public({
                    "id": code, "fullName": full_name, "lastName": last_name,
                    "firstName": first_name, "patronymic": patronymic, "birthDate": birth_date or "",
                    "address": address, "className": class_name, "school": school,
                    "teacher": teacher, "hasPhoto": bool(photo_data),
                })
            except Exception as e:
                log.error("create_student profile: %s", e)
                return _orig_create(code, full_name, class_name, school, created_by)

        items = repo._load_json(repo.STUDENTS_FILE)
        row = {
            "id": code, "fullName": full_name, "lastName": last_name, "firstName": first_name,
            "patronymic": patronymic, "birthDate": birth_date or "", "address": address,
            "className": class_name, "school": school, "teacher": teacher,
            "photoData": photo_data, "hasPhoto": bool(photo_data), "status": "active",
            "createdAt": _utc_now(), "createdBy": created_by,
        }
        items.append(row)
        repo._save_json(repo.STUDENTS_FILE, items)
        return _row_public(row)

    repo.list_students = list_students
    repo.create_student = create_student
    repo.find_student_by_code = find_student_by_code

    if app is None:
        print("[boot] patch_students_profile: repo only")
        return

    def _admin_from_request():
        token = request.headers.get("X-Admin-Token", "") or ""
        if not token:
            return None
        try:
            import server as srv
            tok_map = getattr(srv, "ADMIN_TOKENS", None) or {}
            if token in tok_map:
                return tok_map[token]
        except Exception:
            pass
        try:
            from db.auth_tokens import admin_from_token
            return admin_from_token(token)
        except Exception:
            return None

    def admin_create_student():
        admin = _admin_from_request()
        if not admin:
            return jsonify({"error": "Дастрасӣ рад шуд."}), 401

        payload = request.get_json(silent=True) or {}
        last_name = str(payload.get("lastName") or payload.get("last_name") or "").strip()
        first_name = str(payload.get("firstName") or payload.get("first_name") or "").strip()
        patronymic = str(payload.get("patronymic") or "").strip()
        birth_date = str(payload.get("birthDate") or payload.get("birth_date") or "").strip()
        address = str(payload.get("address") or "").strip()
        class_name = str(payload.get("className") or payload.get("class_name") or "").strip()
        school = str(payload.get("school") or payload.get("school_name") or "").strip()
        teacher = str(payload.get("teacher") or payload.get("teacher_name") or "").strip()
        photo_data = payload.get("photoData") or payload.get("photo_data")
        full_name = str(payload.get("fullName") or "").strip()
        full_name = _compose_full_name(last_name, first_name, patronymic, full_name)

        if not last_name or not first_name:
            return jsonify({"error": "Насаб ва Ном ҳатмӣ мебошанд."}), 400
        if not class_name:
            return jsonify({"error": "Синфро ворид кунед."}), 400
        if not school:
            return jsonify({"error": "Муассиса / мактабро ворид кунед."}), 400
        if birth_date:
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", birth_date):
                m = re.match(r"^(\d{1,2})[./](\d{1,2})[./](\d{4})$", birth_date)
                if m:
                    d, mo, y = m.groups()
                    birth_date = f"{y}-{int(mo):02d}-{int(d):02d}"
                else:
                    return jsonify({"error": "Санаи таваллуд: Рӯз.Моҳ.Сол (масалан 05.03.2012)"}), 400

        code = None
        try:
            import server as srv
            gen = getattr(srv, "generate_long_id", None)
            if callable(gen):
                code = gen()
        except Exception:
            code = None
        if not code:
            import secrets
            code = str(secrets.randbelow(9 * 10**18) + 10**18)

        created_by = ""
        if isinstance(admin, dict):
            created_by = str(admin.get("login") or admin.get("name") or "")

        student = create_student(
            code, full_name, class_name, school, created_by,
            last_name=last_name, first_name=first_name, patronymic=patronymic,
            birth_date=birth_date or None, address=address, teacher=teacher,
            photo_data=photo_data,
        )
        return jsonify({"student": student, "ok": True}), 201

    for rule in list(app.url_map.iter_rules()):
        if rule.rule == "/api/admin/students" and "POST" in (rule.methods or set()):
            app.view_functions[rule.endpoint] = admin_create_student
    if "admin_create_student" in app.view_functions:
        app.view_functions["admin_create_student"] = admin_create_student

    print("[boot] patch_students_profile: installed")
    log.info("patch_students_profile installed")
