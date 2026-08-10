"""Dual-mode data access: PostgreSQL if DATABASE_URL, else JSON."""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text

from db.connection import (
    get_session,
    is_postgres_enabled,
    json_backend_allowed,
)

log = logging.getLogger("geografia.repo")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
ADMINS_FILE = DATA_DIR / "admins.json"
STUDENTS_FILE = DATA_DIR / "students.json"
OLYMPIADS_FILE = DATA_DIR / "olympiads.json"
RESULTS_FILE = DATA_DIR / "results.json"
USERS_FILE = DATA_DIR / "users.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> list:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def _save_json(path: Path, data: list) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def use_pg() -> bool:
    return is_postgres_enabled()


def backend_name() -> str:
    if use_pg():
        return "postgresql"
    if json_backend_allowed():
        return "json"
    return "none"


def list_admins() -> list[dict]:
    """Public list — never includes password fields."""
    if use_pg():
        with get_session() as s:
            rows = s.execute(text(
                "SELECT id::text, login, name, role, created_by, created_at FROM admins "
                "WHERE status = 'active' OR status IS NULL ORDER BY created_at"
            )).mappings().all()
            return [{
                "id": r["id"], "login": r["login"], "name": r["name"],
                "role": r.get("role") or "monitor",
                "createdBy": r.get("created_by"),
                "createdAt": r["created_at"].isoformat() if r.get("created_at") else None,
            } for r in rows]
    out = []
    for a in _load_json(ADMINS_FILE):
        out.append({
            "id": a.get("id"), "login": a.get("login"), "name": a.get("name"),
            "role": a.get("role") or "super_admin",
            "createdBy": a.get("createdBy"), "createdAt": a.get("createdAt"),
        })
    return out


def find_admin_by_login(login: str) -> dict | None:
    """Full admin row including salt/passwordHash for login verification."""
    login_l = (login or "").strip().lower()
    if not login_l:
        return None
    if use_pg():
        try:
            with get_session() as s:
                r = s.execute(text(
                    "SELECT id::text, login, name, role, salt, password_hash, "
                    "created_by, created_at, status "
                    "FROM admins WHERE lower(login) = :login LIMIT 1"
                ), {"login": login_l}).mappings().first()
                if not r:
                    return None
                if r.get("status") and str(r["status"]) not in ("active", "Active"):
                    return None
                return {
                    "id": r["id"],
                    "login": r["login"],
                    "name": r["name"],
                    "role": r.get("role") or "super_admin",
                    "salt": r.get("salt") or "",
                    "passwordHash": r.get("password_hash") or "",
                    "createdBy": r.get("created_by"),
                    "createdAt": r["created_at"].isoformat() if r.get("created_at") else None,
                }
        except Exception as e:
            log.error("find_admin_by_login PG: %s", e)
            return None
    for a in _load_json(ADMINS_FILE):
        if (a.get("login") or "").lower() == login_l:
            return {
                "id": a.get("id"),
                "login": a.get("login"),
                "name": a.get("name"),
                "role": a.get("role") or "super_admin",
                "salt": a.get("salt") or "",
                "passwordHash": a.get("passwordHash") or a.get("password_hash") or "",
                "createdBy": a.get("createdBy"),
                "createdAt": a.get("createdAt"),
            }
    return None


def create_admin(login: str, name: str, salt: str, password_hash: str, created_by: str, role: str = "super_admin") -> dict:
    aid = str(uuid.uuid4())
    if use_pg():
        with get_session() as s:
            s.execute(text(
                "INSERT INTO admins (id, login, name, salt, password_hash, role, status, created_by) "
                "VALUES (:id, :login, :name, :salt, :ph, :role, 'active', :cb)"
            ), {
                "id": aid, "login": login, "name": name, "salt": salt,
                "ph": password_hash, "role": role or "super_admin", "cb": created_by,
            })
        return find_admin_by_login(login) or {
            "id": aid, "login": login, "name": name, "role": role,
        }
    row = {
        "id": aid, "login": login, "name": name, "salt": salt,
        "passwordHash": password_hash, "role": role, "createdBy": created_by,
        "createdAt": _utc_now(),
    }
    items = _load_json(ADMINS_FILE)
    items.append(row)
    _save_json(ADMINS_FILE, items)
    return row


def list_students() -> list[dict]:
    if use_pg():
        with get_session() as s:
            rows = s.execute(text(
                "SELECT student_code, full_name, class_name, school_name, status, created_at "
                "FROM students WHERE status = 'active' ORDER BY full_name"
            )).mappings().all()
            return [{
                "id": r["student_code"], "fullName": r["full_name"],
                "className": r["class_name"], "school": r["school_name"] or "",
                "status": r.get("status") or "active",
                "createdAt": r["created_at"].isoformat() if r.get("created_at") else None,
            } for r in rows]
    return _load_json(STUDENTS_FILE)


def find_student_by_code(code: str) -> dict | None:
    code = (code or "").strip()
    if not code:
        return None
    if use_pg():
        with get_session() as s:
            r = s.execute(text(
                "SELECT student_code, full_name, class_name, school_name, status, user_id, created_at "
                "FROM students WHERE student_code = :c AND status = 'active'"
            ), {"c": code}).mappings().first()
            if not r:
                return None
            return {
                "id": r["student_code"], "fullName": r["full_name"],
                "className": r["class_name"], "school": r["school_name"] or "",
                "status": r.get("status") or "active",
                "userId": str(r["user_id"]) if r.get("user_id") else None,
            }
    for st in _load_json(STUDENTS_FILE):
        if st.get("id") == code:
            return st
    return None


def create_student(code: str, full_name: str, class_name: str, school: str, created_by: str = "") -> dict:
    code = (code or "").strip()
    if use_pg():
        with get_session() as s:
            s.execute(text(
                "INSERT INTO students (student_code, full_name, class_name, school_name, status) "
                "VALUES (:c, :n, :cl, :sch, 'active')"
            ), {"c": code, "n": full_name, "cl": class_name, "sch": school or ""})
        return find_student_by_code(code) or {
            "id": code, "fullName": full_name, "className": class_name, "school": school, "status": "active"
        }
    items = _load_json(STUDENTS_FILE)
    row = {
        "id": code, "fullName": full_name, "className": class_name,
        "school": school, "status": "active", "createdAt": _utc_now(), "createdBy": created_by,
    }
    items.append(row)
    _save_json(STUDENTS_FILE, items)
    return row


def _oly_from_pg(session, o_row) -> dict:
    oid = str(o_row["id"])
    qrows = session.execute(text(
        "SELECT id::text, sort_order, text FROM olympiad_questions "
        "WHERE olympiad_id = :oid ORDER BY sort_order"
    ), {"oid": oid}).mappings().all()
    questions = []
    for q in qrows:
        opts = session.execute(text(
            "SELECT text, is_correct, sort_order FROM olympiad_options "
            "WHERE question_id = :qid ORDER BY sort_order"
        ), {"qid": q["id"]}).mappings().all()
        options = [o["text"] for o in opts]
        answer = 0
        for j, o in enumerate(opts):
            if o.get("is_correct"):
                answer = j
                break
        questions.append({
            "id": q["id"],
            "text": q["text"],
            "options": options,
            "answer": answer,
        })
    start = o_row.get("start_at")
    end = o_row.get("end_at")
    return {
        "id": oid,
        "title": o_row["title"],
        "description": o_row.get("description") or "",
        "type": o_row.get("type") or "olympiad",
        "passScore": o_row.get("pass_score") or 70,
        "durationSec": o_row.get("duration_sec"),
        "startTime": start.isoformat() if start else None,
        "endTime": end.isoformat() if end else None,
        "isActive": bool(o_row.get("is_active")),
        "status": str(o_row.get("status") or "published"),
        "questions": questions,
        "questionCount": len(questions),
        "createdAt": o_row["created_at"].isoformat() if o_row.get("created_at") else None,
    }


def list_olympiads() -> list[dict]:
    if use_pg():
        with get_session() as s:
            rows = s.execute(text(
                "SELECT id, title, description, type, pass_score, duration_sec, "
                "start_at, end_at, is_active, status, created_at "
                "FROM olympiads ORDER BY created_at DESC"
            )).mappings().all()
            return [_oly_from_pg(s, r) for r in rows]
    return _load_json(OLYMPIADS_FILE)


def find_olympiad(olympiad_id: str) -> dict | None:
    if use_pg():
        with get_session() as s:
            r = s.execute(text(
                "SELECT id, title, description, type, pass_score, duration_sec, "
                "start_at, end_at, is_active, status, created_at "
                "FROM olympiads WHERE id::text = :id"
            ), {"id": str(olympiad_id)}).mappings().first()
            if not r:
                return None
            return _oly_from_pg(s, r)
    for o in _load_json(OLYMPIADS_FILE):
        if o.get("id") == olympiad_id:
            return o
    return None


def create_olympiad(data: dict) -> dict:
    oid = str(uuid.uuid4())
    created = _utc_now()
    questions = data.get("questions") or []
    title = data.get("title") or ""
    oly_type = data.get("type") or "olympiad"
    pass_score = int(data.get("passScore") or 70)
    is_active = bool(data.get("isActive"))
    start_time = data.get("startTime") or None
    end_time = data.get("endTime") or None
    duration = data.get("durationSec")
    duration = int(duration) if duration not in (None, "") else None

    if use_pg():
        with get_session() as s:
            s.execute(text(
                "INSERT INTO olympiads "
                "(id, title, type, pass_score, is_active, start_at, end_at, duration_sec, status) "
                "VALUES (:id, :title, :type, :ps, :active, :st, :et, :dur, 'published')"
            ), {
                "id": oid, "title": title, "type": oly_type, "ps": pass_score,
                "active": is_active, "st": start_time, "et": end_time, "dur": duration,
            })
            for i, q in enumerate(questions):
                qid = str(uuid.uuid4())
                s.execute(text(
                    "INSERT INTO olympiad_questions (id, olympiad_id, sort_order, text) "
                    "VALUES (:id, :oid, :ord, :text)"
                ), {"id": qid, "oid": oid, "ord": i, "text": q.get("text") or ""})
                ans = int(q.get("answer") or 0)
                for j, opt in enumerate(q.get("options") or []):
                    s.execute(text(
                        "INSERT INTO olympiad_options "
                        "(id, question_id, sort_order, text, is_correct) "
                        "VALUES (:id, :qid, :ord, :text, :ok)"
                    ), {
                        "id": str(uuid.uuid4()), "qid": qid, "ord": j,
                        "text": str(opt), "ok": j == ans,
                    })
        found = find_olympiad(oid)
        if found:
            return found

    row = {
        "id": oid, "title": title, "type": oly_type, "passScore": pass_score,
        "isActive": is_active, "startTime": start_time, "endTime": end_time,
        "durationSec": duration, "questions": questions, "questionCount": len(questions),
        "createdAt": created, "createdBy": data.get("createdBy"),
    }
    items = _load_json(OLYMPIADS_FILE)
    items.append(row)
    _save_json(OLYMPIADS_FILE, items)
    return row


def update_olympiad(olympiad_id: str, patch: dict) -> dict | None:
    if use_pg():
        fields = []
        params = {"id": str(olympiad_id)}
        mapping = {
            "title": "title", "type": "type", "passScore": "pass_score",
            "isActive": "is_active", "startTime": "start_at", "endTime": "end_at",
            "durationSec": "duration_sec", "status": "status",
        }
        for k, col in mapping.items():
            if k in patch:
                fields.append(f"{col} = :{k}")
                params[k] = patch[k]
        if fields:
            with get_session() as s:
                s.execute(text(
                    f"UPDATE olympiads SET {', '.join(fields)}, updated_at = NOW() WHERE id::text = :id"
                ), params)
        return find_olympiad(olympiad_id)
    items = _load_json(OLYMPIADS_FILE)
    for o in items:
        if o.get("id") == olympiad_id:
            o.update({k: v for k, v in patch.items() if v is not None})
            _save_json(OLYMPIADS_FILE, items)
            return o
    return None


def delete_olympiad(olympiad_id: str) -> bool:
    if use_pg():
        with get_session() as s:
            res = s.execute(text("DELETE FROM olympiads WHERE id::text = :id"), {"id": str(olympiad_id)})
            return res.rowcount > 0
    items = _load_json(OLYMPIADS_FILE)
    new = [o for o in items if o.get("id") != olympiad_id]
    if len(new) == len(items):
        return False
    _save_json(OLYMPIADS_FILE, new)
    return True


def list_results(olympiad_id: str | None = None) -> list[dict]:
    if use_pg():
        try:
            with get_session() as s:
                if olympiad_id:
                    rows = s.execute(text(
                        "SELECT id::text, olympiad_id::text, student_name, student_class, "
                        "student_school, score, status, finished_at "
                        "FROM attempts WHERE kind = 'olympiad' AND olympiad_id::text = :oid "
                        "ORDER BY finished_at DESC NULLS LAST"
                    ), {"oid": str(olympiad_id)}).mappings().all()
                else:
                    rows = s.execute(text(
                        "SELECT id::text, olympiad_id::text, student_name, student_class, "
                        "student_school, score, status, finished_at "
                        "FROM attempts WHERE status IN ('passed','failed','submitted') "
                        "ORDER BY finished_at DESC NULLS LAST LIMIT 2000"
                    )).mappings().all()
                return [{
                    "id": r["id"], "olympiadId": r.get("olympiad_id"),
                    "studentName": r.get("student_name"),
                    "className": r.get("student_class"),
                    "school": r.get("student_school"),
                    "score": r.get("score"), "status": r.get("status"),
                    "finishedAt": r["finished_at"].isoformat() if r.get("finished_at") else None,
                } for r in rows]
        except Exception as e:
            log.warning("list_results: %s", e)
            return []
    return _load_json(RESULTS_FILE)


def save_result(result: dict) -> dict:
    items = _load_json(RESULTS_FILE)
    if not result.get("id"):
        result["id"] = str(uuid.uuid4())
    items.append(result)
    _save_json(RESULTS_FILE, items)
    return result
