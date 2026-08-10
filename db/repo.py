"""Dual-mode data access: PostgreSQL if DATABASE_URL, else JSON."""
from __future__ import annotations

import json
import logging
import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import text

from db.connection import (
    get_session,
    is_postgres_enabled,
    json_backend_allowed,
    health_check as pg_health,
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
    if use_pg():
        with get_session() as s:
            rows = s.execute(text(
                "SELECT id::text, login, name, role, created_by, created_at FROM admins ORDER BY created_at"
            )).mappings().all()
            return [{
                "id": r["id"], "login": r["login"], "name": r["name"],
                "role": r.get("role") or "monitor",
                "createdBy": r.get("created_by"), "createdAt": r["created_at"].isoformat() if r.get("created_at") else None,
            } for r in rows]
    return _load_json(ADMINS_FILE)


def find_admin_by_login(login: str) -> dict | None:
    login = (login or "").strip().lower()
    for a in list_admins():
        if (a.get("login") or "").lower() == login:
            return a
    return None


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


def list_olympiads() -> list[dict]:
    if use_pg():
        with get_session() as s:
            rows = s.execute(text(
                "SELECT id::text, title, description, type, pass_score, duration_sec, "
                "start_time, end_time, is_active, questions, created_at "
                "FROM olympiads ORDER BY created_at DESC"
            )).mappings().all()
            out = []
            for r in rows:
                qs = r.get("questions") or []
                if isinstance(qs, str):
                    try:
                        qs = json.loads(qs)
                    except Exception:
                        qs = []
                out.append({
                    "id": r["id"], "title": r["title"], "description": r.get("description") or "",
                    "type": r.get("type") or "olympiad", "passScore": r.get("pass_score") or 70,
                    "durationSec": r.get("duration_sec"),
                    "startTime": r["start_time"].isoformat() if r.get("start_time") else None,
                    "endTime": r["end_time"].isoformat() if r.get("end_time") else None,
                    "isActive": bool(r.get("is_active")),
                    "questions": qs if isinstance(qs, list) else [],
                    "questionCount": len(qs) if isinstance(qs, list) else 0,
                })
            return out
    return _load_json(OLYMPIADS_FILE)


def find_olympiad(olympiad_id: str) -> dict | None:
    for o in list_olympiads():
        if o.get("id") == olympiad_id:
            return o
    return None


def list_results() -> list[dict]:
    if use_pg():
        with get_session() as s:
            rows = s.execute(text(
                "SELECT id::text, olympiad_id::text, student_code, score, status, finished_at, detail "
                "FROM results ORDER BY finished_at DESC NULLS LAST LIMIT 2000"
            )).mappings().all()
            return [{
                "id": r["id"], "olympiadId": r["olympiad_id"], "studentId": r.get("student_code"),
                "score": r.get("score"), "status": r.get("status"),
                "finishedAt": r["finished_at"].isoformat() if r.get("finished_at") else None,
                "detail": r.get("detail"),
            } for r in rows]
    return _load_json(RESULTS_FILE)


def save_result(result: dict) -> dict:
    if use_pg():
        with get_session() as s:
            rid = result.get("id") or str(uuid.uuid4())
            s.execute(text(
                "INSERT INTO results (id, olympiad_id, student_code, score, status, finished_at, detail) "
                "VALUES (:id, :oid, :sc, :score, :st, NOW(), :detail)"
            ), {
                "id": rid, "oid": result.get("olympiadId"), "sc": result.get("studentId"),
                "score": result.get("score"), "st": result.get("status"),
                "detail": json.dumps(result.get("detail") or {}, ensure_ascii=False),
            })
            result["id"] = rid
            return result
    items = _load_json(RESULTS_FILE)
    if not result.get("id"):
        result["id"] = str(uuid.uuid4())
    items.append(result)
    _save_json(RESULTS_FILE, items)
    return result
