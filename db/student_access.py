"""Phase 3 — student↔user link and olympiad participant access."""
from __future__ import annotations

import uuid

from sqlalchemy import text

from db.connection import get_session
from db.repo import (
    DATA_DIR,
    STUDENTS_FILE,
    _load_json,
    _save_json,
    _utc_now,
    find_student_by_code,
    use_pg,
)


def link_student_to_user(student_code: str, user_id: str) -> dict | None:
    student = find_student_by_code(student_code)
    if not student:
        return None
    if use_pg():
        with get_session() as s:
            s.execute(text("UPDATE students SET user_id = NULL WHERE user_id::text = :uid"), {"uid": user_id})
            res = s.execute(
                text(
                    "UPDATE students SET user_id = :uid WHERE student_code = :code AND status = 'active' "
                    "RETURNING student_code, full_name, class_name, school_name"
                ),
                {"uid": user_id, "code": student_code},
            ).mappings().first()
            if not res:
                return None
            return {
                "id": res["student_code"],
                "fullName": res["full_name"],
                "className": res["class_name"],
                "school": res["school_name"] or "",
            }
    students = _load_json(STUDENTS_FILE)
    for st in students:
        if st.get("userId") == user_id:
            st.pop("userId", None)
        if st.get("id") == student_code:
            st["userId"] = user_id
            _save_json(STUDENTS_FILE, students)
            return st
    return None


def find_student_by_user_id(user_id: str) -> dict | None:
    if use_pg():
        with get_session() as s:
            r = s.execute(
                text(
                    "SELECT student_code, full_name, class_name, school_name, created_by, created_at "
                    "FROM students WHERE user_id::text = :uid AND status = 'active'"
                ),
                {"uid": user_id},
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
    for st in _load_json(STUDENTS_FILE):
        if st.get("userId") == user_id:
            return st
    return None


def list_olympiad_participants(olympiad_id: str) -> list[dict]:
    if use_pg():
        with get_session() as s:
            rows = s.execute(
                text(
                    "SELECT s.student_code, s.full_name, s.class_name, s.school_name, p.status, p.assigned_at "
                    "FROM olympiad_participants p "
                    "JOIN students s ON s.id = p.student_id "
                    "WHERE p.olympiad_id::text = :oid ORDER BY s.full_name"
                ),
                {"oid": olympiad_id},
            ).mappings().all()
            return [
                {
                    "id": r["student_code"],
                    "fullName": r["full_name"],
                    "className": r["class_name"],
                    "school": r["school_name"] or "",
                    "status": r["status"],
                    "assignedAt": r["assigned_at"].isoformat() if r["assigned_at"] else None,
                }
                for r in rows
            ]
    path = DATA_DIR / "participants.json"
    items = _load_json(path)
    return [p for p in items if p.get("olympiadId") == olympiad_id]


def set_olympiad_participants(olympiad_id: str, student_codes: list[str]) -> list[dict]:
    codes = [str(c).strip() for c in student_codes if str(c).strip()]
    if use_pg():
        with get_session() as s:
            s.execute(text("DELETE FROM olympiad_participants WHERE olympiad_id::text = :oid"), {"oid": olympiad_id})
            for code in codes:
                sid = s.execute(text("SELECT id FROM students WHERE student_code = :c"), {"c": code}).scalar()
                if not sid:
                    continue
                s.execute(
                    text(
                        "INSERT INTO olympiad_participants (id, olympiad_id, student_id, status) "
                        "VALUES (:id, :oid, :sid, 'assigned')"
                    ),
                    {"id": str(uuid.uuid4()), "oid": olympiad_id, "sid": str(sid)},
                )
        return list_olympiad_participants(olympiad_id)
    path = DATA_DIR / "participants.json"
    items = [p for p in _load_json(path) if p.get("olympiadId") != olympiad_id]
    students = {s.get("id"): s for s in _load_json(STUDENTS_FILE)}
    for code in codes:
        st = students.get(code)
        if not st:
            continue
        items.append({
            "olympiadId": olympiad_id,
            "id": code,
            "fullName": st.get("fullName"),
            "className": st.get("className"),
            "school": st.get("school"),
            "status": "assigned",
            "assignedAt": _utc_now(),
        })
    _save_json(path, items)
    return [p for p in items if p.get("olympiadId") == olympiad_id]


def student_has_olympiad_access(olympiad_id: str, student_code: str) -> dict:
    student = find_student_by_code(student_code)
    parts = list_olympiad_participants(olympiad_id)

    # Gmail ordinary users: synthetic code g:<userId> — only when olympiad is open (no participant list)
    if not student and student_code and (
        student_code.startswith("g:") or student_code.startswith("gmail:")
    ):
        if parts:
            return {"allowed": False, "reason": "not_assigned"}
        return {
            "allowed": True,
            "reason": "gmail_open",
            "student": {
                "id": student_code,
                "fullName": "Gmail user",
                "className": "",
                "school": "",
            },
        }

    if not student:
        return {"allowed": False, "reason": "student_not_found"}
    if not parts:
        return {"allowed": True, "reason": "open_to_all_students", "student": student}
    ok = any(p.get("id") == student_code and p.get("status", "assigned") == "assigned" for p in parts)
    if ok:
        return {"allowed": True, "reason": "assigned", "student": student}
    return {"allowed": False, "reason": "not_assigned"}
