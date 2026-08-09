"""
Dual-mode data access: PostgreSQL if DATABASE_URL works, else JSON files.
Keeps the same dict shapes as the existing JSON API.
"""
from __future__ import annotations

import json
import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import text

from db.connection import get_session, is_postgres_enabled, health_check as pg_health

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
    if not is_postgres_enabled():
        return False
    h = pg_health()
    return bool(h.get("ok") and h.get("backend") == "postgresql")


def backend_name() -> str:
    return "postgresql" if use_pg() else "json"


# ---------- Admins ----------

def list_admins() -> list[dict]:
    if use_pg():
        with get_session() as s:
            rows = s.execute(text(
                "SELECT id::text, login, name, created_by, created_at FROM admins ORDER BY created_at"
            )).mappings().all()
            return [
                {
                    "id": r["id"],
                    "login": r["login"],
                    "name": r["name"],
                    "createdBy": r["created_by"],
                    "createdAt": r["created_at"].isoformat() if r["created_at"] else None,
                }
                for r in rows
            ]
    return _load_json(ADMINS_FILE)


def find_admin_by_login(login: str) -> dict | None:
    if use_pg():
        with get_session() as s:
            r = s.execute(
                text(
                    "SELECT id::text, login, name, salt, password_hash, created_by, created_at "
                    "FROM admins WHERE login = :l AND status = 'active'"
                ),
                {"l": login},
            ).mappings().first()
            if not r:
                return None
            return {
                "id": r["id"],
                "login": r["login"],
                "name": r["name"],
                "salt": r["salt"],
                "passwordHash": r["password_hash"],
                "createdBy": r["created_by"],
                "createdAt": r["created_at"].isoformat() if r["created_at"] else None,
            }
    for a in _load_json(ADMINS_FILE):
        if a.get("login") == login:
            return a
    return None


def create_admin(login: str, name: str, salt: str, password_hash: str, created_by: str) -> dict:
    aid = str(uuid.uuid4())
    created = _utc_now()
    if use_pg():
        with get_session() as s:
            s.execute(
                text(
                    "INSERT INTO admins (id, login, name, salt, password_hash, role, created_by) "
                    "VALUES (:id, :login, :name, :salt, :ph, 'super_admin', :cb)"
                ),
                {"id": aid, "login": login, "name": name, "salt": salt, "ph": password_hash, "cb": created_by},
            )
        return {"id": aid, "login": login, "name": name, "createdBy": created_by, "createdAt": created}
    admins = _load_json(ADMINS_FILE)
    row = {
        "id": aid,
        "login": login,
        "name": name,
        "salt": salt,
        "passwordHash": password_hash,
        "createdBy": created_by,
        "createdAt": created,
    }
    admins.append(row)
    _save_json(ADMINS_FILE, admins)
    return {k: row[k] for k in ("id", "login", "name", "createdBy", "createdAt")}


def delete_admin(admin_id: str) -> bool:
    if use_pg():
        with get_session() as s:
            res = s.execute(text("DELETE FROM admins WHERE id::text = :id"), {"id": admin_id})
            return res.rowcount > 0
    admins = _load_json(ADMINS_FILE)
    new_list = [a for a in admins if a.get("id") != admin_id]
    if len(new_list) == len(admins):
        return False
    _save_json(ADMINS_FILE, new_list)
    return True


def count_admins() -> int:
    if use_pg():
        with get_session() as s:
            return int(s.execute(text("SELECT COUNT(*) FROM admins")).scalar() or 0)
    return len(_load_json(ADMINS_FILE))


# ---------- Students ----------

def list_students() -> list[dict]:
    if use_pg():
        with get_session() as s:
            rows = s.execute(text(
                "SELECT student_code, full_name, class_name, school_name, created_by, created_at "
                "FROM students ORDER BY created_at DESC"
            )).mappings().all()
            return [
                {
                    "id": r["student_code"],
                    "fullName": r["full_name"],
                    "className": r["class_name"],
                    "school": r["school_name"] or "",
                    "createdBy": r["created_by"],
                    "createdAt": r["created_at"].isoformat() if r["created_at"] else None,
                }
                for r in rows
            ]
    return _load_json(STUDENTS_FILE)


def find_student_by_code(code: str) -> dict | None:
    if use_pg():
        with get_session() as s:
            r = s.execute(
                text(
                    "SELECT student_code, full_name, class_name, school_name, created_by, created_at "
                    "FROM students WHERE student_code = :c AND status = 'active'"
                ),
                {"c": code},
            ).mappings().first()
            if not r:
                return None
            return {
                "id": r["student_code"],
                "fullName": r["full_name"],
                "className": r["class_name"],
                "school": r["school_name"] or "",
                "createdBy": r["created_by"],
                "createdAt": r["created_at"].isoformat() if r["created_at"] else None,
            }
    for s in _load_json(STUDENTS_FILE):
        if s.get("id") == code:
            return s
    return None


def student_codes_set() -> set[str]:
    if use_pg():
        with get_session() as s:
            rows = s.execute(text("SELECT student_code FROM students")).scalars().all()
            return set(rows)
    return {s.get("id") for s in _load_json(STUDENTS_FILE) if isinstance(s, dict)}


def create_student(code: str, full_name: str, class_name: str, school: str, created_by: str) -> dict:
    created = _utc_now()
    if use_pg():
        with get_session() as s:
            school_id = None
            if school:
                row = s.execute(
                    text("SELECT id FROM schools WHERE lower(name) = lower(:n)"), {"n": school}
                ).first()
                if row:
                    school_id = str(row[0])
                else:
                    school_id = str(uuid.uuid4())
                    s.execute(
                        text("INSERT INTO schools (id, name) VALUES (:id, :n)"),
                        {"id": school_id, "n": school},
                    )
            s.execute(
                text(
                    "INSERT INTO students "
                    "(id, student_code, full_name, class_name, school_id, school_name, created_by) "
                    "VALUES (:id, :code, :fn, :cl, :sid, :sn, :cb)"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "code": code,
                    "fn": full_name,
                    "cl": class_name,
                    "sid": school_id,
                    "sn": school,
                    "cb": created_by,
                },
            )
        return {
            "id": code,
            "fullName": full_name,
            "className": class_name,
            "school": school,
            "createdBy": created_by,
            "createdAt": created,
        }
    students = _load_json(STUDENTS_FILE)
    row = {
        "id": code,
        "fullName": full_name,
        "className": class_name,
        "school": school,
        "createdBy": created_by,
        "createdAt": created,
    }
    students.append(row)
    _save_json(STUDENTS_FILE, students)
    return row


def delete_student(code: str) -> bool:
    if use_pg():
        with get_session() as s:
            res = s.execute(text("DELETE FROM students WHERE student_code = :c"), {"c": code})
            return res.rowcount > 0
    students = _load_json(STUDENTS_FILE)
    new_list = [s for s in students if s.get("id") != code]
    if len(new_list) == len(students):
        return False
    _save_json(STUDENTS_FILE, new_list)
    return True


# ---------- Olympiads (JSON shape with embedded questions) ----------

def _oly_from_pg(session, o_row) -> dict:
    oid = str(o_row["id"])
    qrows = session.execute(
        text(
            "SELECT id::text, sort_order, text FROM olympiad_questions "
            "WHERE olympiad_id = :oid ORDER BY sort_order"
        ),
        {"oid": oid},
    ).mappings().all()
    questions = []
    for i, q in enumerate(qrows):
        opts = session.execute(
            text(
                "SELECT text, is_correct, sort_order FROM olympiad_options "
                "WHERE question_id = :qid ORDER BY sort_order"
            ),
            {"qid": q["id"]},
        ).mappings().all()
        options = [o["text"] for o in opts]
        answer = next((j for j, o in enumerate(opts) if o["is_correct"]), 0)
        questions.append({
            "id": i + 1,
            "text": q["text"],
            "options": options,
            "answer": answer,
            "_uuid": q["id"],
        })
    start = o_row["start_at"].isoformat() if o_row["start_at"] else None
    end = o_row["end_at"].isoformat() if o_row["end_at"] else None
    return {
        "id": oid,
        "title": o_row["title"],
        "type": o_row["type"] or "olympiad",
        "passScore": o_row["pass_score"],
        "isActive": bool(o_row["is_active"]),
        "startTime": start,
        "endTime": end,
        "questions": questions,
        "createdAt": o_row["created_at"].isoformat() if o_row["created_at"] else None,
        "createdBy": None,
    }


def list_olympiads() -> list[dict]:
    if use_pg():
        with get_session() as s:
            rows = s.execute(text(
                "SELECT id, title, type, pass_score, is_active, start_at, end_at, created_at "
                "FROM olympiads ORDER BY created_at DESC"
            )).mappings().all()
            return [_oly_from_pg(s, r) for r in rows]
    return _load_json(OLYMPIADS_FILE)


def find_olympiad(olympiad_id: str) -> dict | None:
    if use_pg():
        with get_session() as s:
            r = s.execute(
                text(
                    "SELECT id, title, type, pass_score, is_active, start_at, end_at, created_at "
                    "FROM olympiads WHERE id::text = :id"
                ),
                {"id": olympiad_id},
            ).mappings().first()
            if not r:
                return None
            return _oly_from_pg(s, r)
    for o in _load_json(OLYMPIADS_FILE):
        if o.get("id") == olympiad_id:
            return o
    return None


def create_olympiad(data: dict) -> dict:
    """data: title, type, passScore, isActive, startTime, endTime, questions[{text,options,answer}], createdBy"""
    oid = str(uuid.uuid4())
    created = _utc_now()
    questions = data.get("questions") or []
    if use_pg():
        with get_session() as s:
            s.execute(
                text(
                    "INSERT INTO olympiads "
                    "(id, title, type, pass_score, is_active, start_at, end_at, status) "
                    "VALUES (:id, :title, :type, :ps, :active, :st, :et, 'published')"
                ),
                {
                    "id": oid,
                    "title": data["title"],
                    "type": data.get("type") or "olympiad",
                    "ps": int(data.get("passScore") or 70),
                    "active": bool(data.get("isActive")),
                    "st": data.get("startTime"),
                    "et": data.get("endTime"),
                },
            )
            for i, q in enumerate(questions):
                qid = str(uuid.uuid4())
                s.execute(
                    text(
                        "INSERT INTO olympiad_questions (id, olympiad_id, sort_order, text) "
                        "VALUES (:id, :oid, :ord, :text)"
                    ),
                    {"id": qid, "oid": oid, "ord": i, "text": q["text"]},
                )
                ans = int(q.get("answer") or 0)
                for j, opt in enumerate(q.get("options") or []):
                    s.execute(
                        text(
                            "INSERT INTO olympiad_options "
                            "(id, question_id, sort_order, text, is_correct) "
                            "VALUES (:id, :qid, :ord, :text, :ok)"
                        ),
                        {
                            "id": str(uuid.uuid4()),
                            "qid": qid,
                            "ord": j,
                            "text": str(opt),
                            "ok": j == ans,
                        },
                    )
        return find_olympiad(oid) or {
            "id": oid,
            "title": data["title"],
            "type": data.get("type") or "olympiad",
            "passScore": int(data.get("passScore") or 70),
            "isActive": bool(data.get("isActive")),
            "startTime": data.get("startTime"),
            "endTime": data.get("endTime"),
            "questions": questions,
            "createdAt": created,
            "createdBy": data.get("createdBy"),
        }
    row = {
        "id": oid,
        "title": data["title"],
        "type": data.get("type") or "olympiad",
        "passScore": int(data.get("passScore") or 70),
        "isActive": bool(data.get("isActive")),
        "startTime": data.get("startTime"),
        "endTime": data.get("endTime"),
        "questions": questions,
        "createdBy": data.get("createdBy"),
        "createdAt": created,
    }
    items = _load_json(OLYMPIADS_FILE)
    items.append(row)
    _save_json(OLYMPIADS_FILE, items)
    return row


def update_olympiad(olympiad_id: str, patch: dict) -> dict | None:
    if use_pg():
        fields = []
        params: dict[str, Any] = {"id": olympiad_id}
        if "isActive" in patch:
            fields.append("is_active = :active")
            params["active"] = bool(patch["isActive"])
        if "passScore" in patch:
            fields.append("pass_score = :ps")
            params["ps"] = int(patch["passScore"])
        if "title" in patch and str(patch["title"]).strip():
            fields.append("title = :title")
            params["title"] = str(patch["title"]).strip()
        if "startTime" in patch:
            fields.append("start_at = :st")
            params["st"] = patch.get("startTime")
        if "endTime" in patch:
            fields.append("end_at = :et")
            params["et"] = patch.get("endTime")
        if not fields:
            return find_olympiad(olympiad_id)
        with get_session() as s:
            s.execute(
                text(f"UPDATE olympiads SET {', '.join(fields)}, updated_at = now() WHERE id::text = :id"),
                params,
            )
        return find_olympiad(olympiad_id)
    items = _load_json(OLYMPIADS_FILE)
    for o in items:
        if o.get("id") == olympiad_id:
            o.update({k: v for k, v in patch.items() if k in ("isActive", "passScore", "title", "startTime", "endTime")})
            _save_json(OLYMPIADS_FILE, items)
            return o
    return None


def delete_olympiad(olympiad_id: str) -> bool:
    if use_pg():
        with get_session() as s:
            res = s.execute(text("DELETE FROM olympiads WHERE id::text = :id"), {"id": olympiad_id})
            return res.rowcount > 0
    items = _load_json(OLYMPIADS_FILE)
    new_list = [o for o in items if o.get("id") != olympiad_id]
    if len(new_list) == len(items):
        return False
    _save_json(OLYMPIADS_FILE, new_list)
    return True


# ---------- Results / attempts ----------

def list_results(olympiad_id: str | None = None) -> list[dict]:
    if use_pg():
        with get_session() as s:
            if olympiad_id:
                rows = s.execute(
                    text(
                        "SELECT id::text, olympiad_id::text, student_id, student_name, student_class, "
                        "student_school, score, correct, total, pass_score, status, finished_at "
                        "FROM attempts WHERE kind = 'olympiad' AND olympiad_id::text = :oid "
                        "ORDER BY finished_at DESC NULLS LAST"
                    ),
                    {"oid": olympiad_id},
                ).mappings().all()
            else:
                rows = s.execute(
                    text(
                        "SELECT id::text, olympiad_id::text, student_id, student_name, student_class, "
                        "student_school, score, correct, total, pass_score, status, finished_at "
                        "FROM attempts WHERE kind = 'olympiad' "
                        "ORDER BY finished_at DESC NULLS LAST LIMIT 200"
                    )
                ).mappings().all()
            out = []
            for r in rows:
                code = None
                if r["student_id"]:
                    code = s.execute(
                        text("SELECT student_code FROM students WHERE id = :id"),
                        {"id": str(r["student_id"])},
                    ).scalar()
                out.append({
                    "id": r["id"],
                    "studentId": code or "",
                    "studentName": r["student_name"],
                    "studentClass": r["student_class"],
                    "studentSchool": r["student_school"],
                    "olympiadId": r["olympiad_id"],
                    "score": r["score"],
                    "correct": r["correct"],
                    "total": r["total"],
                    "passScore": r["pass_score"],
                    "status": r["status"] if isinstance(r["status"], str) else str(r["status"]),
                    "finishedAt": r["finished_at"].isoformat() if r["finished_at"] else None,
                })
            return out
    results = _load_json(RESULTS_FILE)
    if olympiad_id:
        results = [r for r in results if r.get("olympiadId") == olympiad_id]
    return results


def save_result(result: dict) -> None:
    if use_pg():
        with get_session() as s:
            stu_uuid = None
            code = result.get("studentId")
            if code:
                stu_uuid = s.execute(
                    text("SELECT id FROM students WHERE student_code = :c"), {"c": code}
                ).scalar()
            # remove previous finished attempt
            if stu_uuid and result.get("olympiadId"):
                s.execute(
                    text(
                        "DELETE FROM attempts WHERE kind = 'olympiad' "
                        "AND olympiad_id::text = :oid AND student_id = :sid"
                    ),
                    {"oid": result["olympiadId"], "sid": str(stu_uuid)},
                )
            status = result.get("status") or "submitted"
            s.execute(
                text(
                    "INSERT INTO attempts "
                    "(id, kind, olympiad_id, student_id, student_name, student_class, student_school, "
                    " score, correct, total, pass_score, status, finished_at, started_at) "
                    "VALUES (:id, 'olympiad', :oid, :sid, :sn, :sc, :ss, "
                    " :score, :correct, :total, :ps, :status, :fin, :fin)"
                ),
                {
                    "id": result.get("id") or str(uuid.uuid4()),
                    "oid": result["olympiadId"],
                    "sid": str(stu_uuid) if stu_uuid else None,
                    "sn": result.get("studentName"),
                    "sc": result.get("studentClass"),
                    "ss": result.get("studentSchool"),
                    "score": result.get("score"),
                    "correct": result.get("correct"),
                    "total": result.get("total"),
                    "ps": result.get("passScore"),
                    "status": status,
                    "fin": result.get("finishedAt"),
                },
            )
        return
    results = _load_json(RESULTS_FILE)
    results = [
        r for r in results
        if not (r.get("studentId") == result.get("studentId") and r.get("olympiadId") == result.get("olympiadId"))
    ]
    results.append(result)
    _save_json(RESULTS_FILE, results)


# ---------- Users (legacy + Google) ----------

def find_user_by_email(email: str) -> dict | None:
    email = email.lower().strip()
    if use_pg():
        with get_session() as s:
            r = s.execute(
                text(
                    "SELECT id::text, google_id, email, name, avatar_url, salt, password_hash, created_at "
                    "FROM users WHERE lower(email) = :e"
                ),
                {"e": email},
            ).mappings().first()
            if not r:
                return None
            return {
                "id": r["id"],
                "googleId": r["google_id"],
                "email": r["email"],
                "name": r["name"],
                "avatar": r["avatar_url"],
                "salt": r["salt"],
                "passwordHash": r["password_hash"],
                "createdAt": r["created_at"].isoformat() if r["created_at"] else None,
            }
    for u in _load_json(USERS_FILE):
        if (u.get("email") or "").lower() == email:
            return u
    return None


def upsert_google_user(google_id: str, email: str, name: str, avatar: str | None) -> dict:
    email = email.lower().strip()
    if use_pg():
        with get_session() as s:
            r = s.execute(
                text("SELECT id::text FROM users WHERE google_id = :g OR lower(email) = :e"),
                {"g": google_id, "e": email},
            ).first()
            if r:
                s.execute(
                    text(
                        "UPDATE users SET google_id = :g, email = :e, name = :n, "
                        "avatar_url = COALESCE(:a, avatar_url), last_login_at = now() "
                        "WHERE id::text = :id"
                    ),
                    {"g": google_id, "e": email, "n": name, "a": avatar, "id": str(r[0])},
                )
                uid = str(r[0])
            else:
                uid = str(uuid.uuid4())
                s.execute(
                    text(
                        "INSERT INTO users (id, google_id, email, name, avatar_url, last_login_at) "
                        "VALUES (:id, :g, :e, :n, :a, now())"
                    ),
                    {"id": uid, "g": google_id, "e": email, "n": name, "a": avatar},
                )
            return {"id": uid, "email": email, "name": name, "avatar": avatar, "googleId": google_id}
    users = _load_json(USERS_FILE)
    for u in users:
        if u.get("googleId") == google_id or (u.get("email") or "").lower() == email:
            u["googleId"] = google_id
            u["email"] = email
            u["name"] = name
            if avatar:
                u["avatar"] = avatar
            _save_json(USERS_FILE, users)
            return u
    row = {
        "id": str(uuid.uuid4()),
        "googleId": google_id,
        "email": email,
        "name": name,
        "avatar": avatar,
        "createdAt": _utc_now(),
    }
    users.append(row)
    _save_json(USERS_FILE, users)
    return row
