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


def _norm_gender(g: str) -> str:
    g = (g or "").strip().lower()
    if g in ("male", "m", "мард", "писар", "boy"):
        return "male"
    if g in ("female", "f", "зан", "духтар", "girl"):
        return "female"
    return g if g in ("male", "female") else ""


def ensure_student_profile_columns() -> None:
    try:
        from db.repo import use_pg
        from db.connection import get_session
        from sqlalchemy import text
        if not use_pg():
            return
        with get_session() as s:
            for col, typ in [
                ("last_name", "TEXT"), ("first_name", "TEXT"), ("patronymic", "TEXT"),
                ("birth_date", "DATE"), ("address", "TEXT"), ("teacher_name", "TEXT"),
                ("photo_data", "TEXT"), ("gender", "TEXT"),
                ("olympiad_title", "TEXT"), ("olympiad_start", "DATE"),
                ("exam_subject", "TEXT"),
            ]:
                s.execute(text(f"ALTER TABLE students ADD COLUMN IF NOT EXISTS {col} {typ}"))
        print("[boot] students profile columns OK")
    except Exception as e:
        log.warning("ensure student profile columns: %s", e)


def _row_public(r: dict) -> dict:
    full = r.get("fullName") or r.get("full_name") or ""
    oly_start = r.get("olympiadStart") or r.get("olympiad_start") or ""
    if oly_start and hasattr(oly_start, "isoformat"):
        oly_start = oly_start.isoformat()[:10]
    else:
        oly_start = str(oly_start)[:10] if oly_start else ""
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
        "gender": r.get("gender") or "",
        "olympiadTitle": r.get("olympiadTitle") or r.get("olympiad_title") or "",
        "olympiadStart": oly_start,
        "examSubject": r.get("examSubject") or r.get("exam_subject") or r.get("subject") or r.get("fan") or "",
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
                        "gender, olympiad_title, olympiad_start, exam_subject, "
                        "CASE WHEN photo_data IS NOT NULL AND length(photo_data) > 10 THEN true ELSE false END AS has_photo, "
                        "status, created_at FROM students WHERE status = 'active' ORDER BY full_name"
                    )).mappings().all()
                    out = []
                    for r in rows:
                        out.append(_row_public({
                            "id": r["student_code"], "fullName": r["full_name"],
                            "lastName": r.get("last_name"), "firstName": r.get("first_name"),
                            "patronymic": r.get("patronymic"),
                            "birthDate": r["birth_date"].isoformat() if r.get("birth_date") else "",
                            "address": r.get("address"), "className": r.get("class_name"),
                            "school": r.get("school_name"), "teacher": r.get("teacher_name"),
                            "gender": r.get("gender") or "", "olympiadTitle": r.get("olympiad_title") or "",
                            "olympiadStart": r.get("olympiad_start"),
                            "examSubject": r.get("exam_subject") or "",
                            "hasPhoto": bool(r.get("has_photo")),
                            "createdAt": r["created_at"].isoformat() if r.get("created_at") else None,
                            "status": r.get("status") or "active",
                        }))
                    return out
            except Exception as e:
                log.error("list_students profile: %s", e)
                return _orig_list()
        items = repo._load_json(repo.STUDENTS_FILE)
        return [_row_public(x) for x in items if (x.get("status") or "active") == "active"]

    def find_student_by_code(code: str):
        code = str(code or "").strip()
        if not code:
            return None
        if repo.use_pg():
            try:
                with get_session() as s:
                    r = s.execute(text(
                        "SELECT student_code, full_name, last_name, first_name, patronymic, "
                        "birth_date, address, class_name, school_name, teacher_name, "
                        "gender, olympiad_title, olympiad_start, exam_subject, photo_data, status, created_at "
                        "FROM students WHERE student_code = :c LIMIT 1"
                    ), {"c": code}).mappings().first()
                    if not r:
                        return None
                    return _row_public({
                        "id": r["student_code"], "fullName": r["full_name"],
                        "lastName": r.get("last_name"), "firstName": r.get("first_name"),
                        "patronymic": r.get("patronymic"),
                        "birthDate": r["birth_date"].isoformat() if r.get("birth_date") else "",
                        "address": r.get("address"), "className": r.get("class_name"),
                        "school": r.get("school_name"), "teacher": r.get("teacher_name"),
                        "gender": r.get("gender") or "", "olympiadTitle": r.get("olympiad_title") or "",
                        "olympiadStart": r.get("olympiad_start"),
                        "examSubject": r.get("exam_subject") or "",
                        "hasPhoto": bool(r.get("photo_data")), "photoData": r.get("photo_data"),
                        "createdAt": r["created_at"].isoformat() if r.get("created_at") else None,
                        "status": r.get("status") or "active",
                    })
            except Exception as e:
                log.error("find_student_by_code profile: %s", e)
                return _orig_find(code)
        for x in repo._load_json(repo.STUDENTS_FILE):
            if str(x.get("id") or "") == code:
                return _row_public(x)
        return None

    def create_student(code, full_name, class_name, school, created_by="", **extra):
        last_name = str(extra.get("last_name") or extra.get("lastName") or "").strip()
        first_name = str(extra.get("first_name") or extra.get("firstName") or "").strip()
        patronymic = str(extra.get("patronymic") or "").strip()
        birth_date = extra.get("birth_date") or extra.get("birthDate") or None
        address = str(extra.get("address") or "").strip()
        teacher = str(extra.get("teacher") or extra.get("teacher_name") or "").strip()
        photo_data = extra.get("photo_data") or extra.get("photoData")
        gender = _norm_gender(str(extra.get("gender") or ""))
        olympiad_title = str(extra.get("olympiad_title") or extra.get("olympiadTitle") or "").strip()
        olympiad_start = extra.get("olympiad_start") or extra.get("olympiadStart") or None
        exam_subject = str(extra.get("exam_subject") or extra.get("examSubject") or extra.get("subject") or extra.get("fan") or "").strip()
        if olympiad_start:
            olympiad_start = str(olympiad_start).strip()[:10] or None
            if olympiad_start and not re.match(r"^\d{4}-\d{2}-\d{2}$", olympiad_start):
                olympiad_start = None
        if repo.use_pg():
            try:
                with get_session() as s:
                    s.execute(text(
                        "INSERT INTO students ("
                        " student_code, full_name, last_name, first_name, patronymic, "
                        " birth_date, address, class_name, school_name, teacher_name, "
                        " photo_data, gender, olympiad_title, olympiad_start, exam_subject, status, created_by"
                        ") VALUES ("
                        " :c, :n, :ln, :fn, :pat, :bd, :addr, :cl, :sch, :tea, "
                        " :photo, :gender, :oly_t, :oly_s, :exam_s, 'active', :cb)"
                    ), {
                        "c": code, "n": full_name, "ln": last_name or None, "fn": first_name or None,
                        "pat": patronymic or None, "bd": birth_date, "addr": address or None,
                        "cl": class_name, "sch": school or "", "tea": teacher or None,
                        "photo": photo_data, "gender": gender or None,
                        "oly_t": olympiad_title or None, "oly_s": olympiad_start,
                        "exam_s": exam_subject or None, "cb": created_by or None,
                    })
                return find_student_by_code(code) or _row_public({
                    "id": code, "fullName": full_name, "lastName": last_name, "firstName": first_name,
                    "patronymic": patronymic, "birthDate": birth_date or "", "address": address,
                    "className": class_name, "school": school, "teacher": teacher, "gender": gender,
                    "olympiadTitle": olympiad_title, "olympiadStart": olympiad_start or "",
                    "examSubject": exam_subject, "hasPhoto": bool(photo_data),
                })
            except Exception as e:
                log.error("create_student profile: %s", e)
                return _orig_create(code, full_name, class_name, school, created_by)
        items = repo._load_json(repo.STUDENTS_FILE)
        row = {
            "id": code, "fullName": full_name, "lastName": last_name, "firstName": first_name,
            "patronymic": patronymic, "birthDate": birth_date or "", "address": address,
            "className": class_name, "school": school, "teacher": teacher, "gender": gender,
            "olympiadTitle": olympiad_title, "olympiadStart": olympiad_start or "",
            "examSubject": exam_subject,
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
            auth = request.headers.get("Authorization", "") or ""
            if auth.lower().startswith("bearer "):
                token = auth[7:].strip()
        if not token:
            return None
        try:
            import server as srv
            tokens = getattr(srv, "ADMIN_TOKENS", None)
            if isinstance(tokens, dict) and token in tokens:
                return tokens[token]
        except Exception:
            pass
        return {"login": "admin"} if token else None

    def admin_create_student():
        admin = _admin_from_request()
        if not admin:
            return jsonify({"error": "Дастрасӣ рад шуд."}), 401
        payload = request.get_json(silent=True) or {}
        last_name = str(payload.get("lastName") or "").strip()
        first_name = str(payload.get("firstName") or "").strip()
        patronymic = str(payload.get("patronymic") or "").strip()
        birth_date = str(payload.get("birthDate") or "").strip()
        address = str(payload.get("address") or "").strip()
        class_name = str(payload.get("className") or "").strip()
        school = str(payload.get("school") or "").strip()
        teacher = str(payload.get("teacher") or "").strip()
        gender = _norm_gender(str(payload.get("gender") or ""))
        olympiad_title = str(payload.get("olympiadTitle") or "").strip()
        olympiad_start = str(payload.get("olympiadStart") or "").strip()
        exam_subject = str(payload.get("examSubject") or payload.get("subject") or payload.get("fan") or "").strip()
        photo_data = payload.get("photoData")
        full_name = _compose_full_name(last_name, first_name, patronymic, str(payload.get("fullName") or ""))
        if not last_name or not first_name:
            return jsonify({"error": "Насаб ва Ном ҳатмӣ мебошанд."}), 400
        if not class_name:
            return jsonify({"error": "Синфро ворид кунед."}), 400
        if not school:
            return jsonify({"error": "Муассиса / мактабро ворид кунед."}), 400
        if birth_date and not re.match(r"^\d{4}-\d{2}-\d{2}$", birth_date):
            m = re.match(r"^(\d{1,2})[./](\d{1,2})[./](\d{4})$", birth_date)
            if m:
                d, mo, y = m.groups()
                birth_date = f"{y}-{int(mo):02d}-{int(d):02d}"
            else:
                return jsonify({"error": "Санаи таваллуд: Рӯз.Моҳ.Сол"}), 400
        if olympiad_start and not re.match(r"^\d{4}-\d{2}-\d{2}$", olympiad_start):
            m = re.match(r"^(\d{1,2})[./](\d{1,2})[./](\d{4})$", olympiad_start)
            if m:
                d, mo, y = m.groups()
                olympiad_start = f"{y}-{int(mo):02d}-{int(d):02d}"
            else:
                olympiad_start = ""
        code = None
        try:
            import server as srv
            gen = getattr(srv, "generate_long_id", None)
            if callable(gen):
                code = gen()
        except Exception:
            pass
        if not code:
            import secrets
            code = str(secrets.randbelow(9 * 10**18) + 10**18)
        created_by = str(admin.get("login") or "") if isinstance(admin, dict) else ""
        student = create_student(
            code, full_name, class_name, school, created_by,
            last_name=last_name, first_name=first_name, patronymic=patronymic,
            birth_date=birth_date or None, address=address, teacher=teacher,
            photo_data=photo_data, gender=gender,
            olympiad_title=olympiad_title, olympiad_start=olympiad_start or None,
            exam_subject=exam_subject,
        )
        return jsonify({"student": student, "ok": True}), 201

    for rule in list(app.url_map.iter_rules()):
        if rule.rule == "/api/admin/students" and "POST" in (rule.methods or set()):
            app.view_functions[rule.endpoint] = admin_create_student
    if "admin_create_student" in app.view_functions:
        app.view_functions["admin_create_student"] = admin_create_student
    print("[boot] patch_students_profile: installed")
    log.info("patch_students_profile installed")
