"""Phase 3 — student↔user link and olympiad participant access (schema-safe)."""
from __future__ import annotations

import logging
import uuid

from sqlalchemy import text

from db.connection import get_session
from db.repo import (
    DATA_DIR,
    STUDENTS_FILE,
    _load_json,
    _save_json,
    find_student_by_code,
    use_pg,
)

log = logging.getLogger("geografia.student_access")
PARTICIPANTS_FILE = DATA_DIR / "olympiad_participants.json"


def link_student_to_user(student_code: str, user_id: str) -> dict | None:
    student = find_student_by_code(student_code)
    if not student:
        return None
    if use_pg():
        try:
            with get_session() as s:
                s.execute(
                    text("UPDATE students SET user_id = NULL WHERE user_id::text = :uid"),
                    {"uid": user_id},
                )
                res = s.execute(
                    text(
                        "UPDATE students SET user_id = :uid "
                        "WHERE student_code = :code AND status = 'active' "
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
        except Exception as e:
            log.warning("link_student_to_user: %s", e)
            return None
    students = _load_json(STUDENTS_FILE)
    for st in students:
        if st.get("id") == student_code:
            st["userId"] = user_id
            _save_json(STUDENTS_FILE, students)
            return st
    return None


def find_student_by_user_id(user_id: str) -> dict | None:
    if use_pg():
        try:
            with get_session() as s:
                r = s.execute(
                    text(
                        "SELECT student_code, full_name, class_name, school_name "
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
                }
        except Exception as e:
            log.warning("find_student_by_user_id: %s", e)
            return None
    for st in _load_json(STUDENTS_FILE):
        if str(st.get("userId")) == str(user_id):
            return st
    return None


def list_olympiad_participants(olympiad_id: str) -> list[dict]:
    if use_pg():
        try:
            with get_session() as s:
                rows = s.execute(
                    text(
                        "SELECT s.student_code, s.full_name, s.class_name, s.school_name, "
                        "p.status, p.assigned_at "
                        "FROM olympiad_participants p "
                        "JOIN students s ON s.id = p.student_id "
                        "WHERE p.olympiad_id::text = :oid"
                    ),
                    {"oid": str(olympiad_id)},
                ).mappings().all()
                return [
                    {
                        "id": r["student_code"],
                        "fullName": r["full_name"],
                        "className": r["class_name"],
                        "school": r["school_name"] or "",
                        "status": r.get("status") or "assigned",
                    }
                    for r in rows
                ]
        except Exception as e:
            log.warning("list_olympiad_participants: %s", e)
            return []
    items = _load_json(PARTICIPANTS_FILE)
    return [p for p in items if str(p.get("olympiadId")) == str(olympiad_id)]


def set_olympiad_participants(olympiad_id: str, student_codes: list[str]) -> list[dict]:
    codes = [str(c).strip() for c in student_codes if str(c).strip()]
    if use_pg():
        try:
            with get_session() as s:
                s.execute(
                    text("DELETE FROM olympiad_participants WHERE olympiad_id::text = :oid"),
                    {"oid": str(olympiad_id)},
                )
                for code in codes:
                    sid = s.execute(
                        text("SELECT id FROM students WHERE student_code = :c"),
                        {"c": code},
                    ).scalar()
                    if not sid:
                        continue
                    s.execute(
                        text(
                            "INSERT INTO olympiad_participants (id, olympiad_id, student_id, status) "
                            "VALUES (:id, :oid, :sid, 'assigned')"
                        ),
                        {"id": str(uuid.uuid4()), "oid": olympiad_id, "sid": sid},
                    )
            return list_olympiad_participants(olympiad_id)
        except Exception as e:
            log.error("set_olympiad_participants: %s", e)
            return []
    students = {s.get("id"): s for s in _load_json(STUDENTS_FILE)}
    items = [p for p in _load_json(PARTICIPANTS_FILE) if str(p.get("olympiadId")) != str(olympiad_id)]
    for code in codes:
        st = students.get(code)
        if not st:
            continue
        items.append({
            "olympiadId": olympiad_id,
            "id": code,
            "fullName": st.get("fullName"),
            "status": "assigned",
        })
    _save_json(PARTICIPANTS_FILE, items)
    return [p for p in items if str(p.get("olympiadId")) == str(olympiad_id)]


def student_has_olympiad_access(olympiad_id: str, student_code: str) -> dict:
    """
    Access rules (school-friendly):
    - Valid Student ID required.
    - Empty olympiad_participants list = ALL active students may start
      (admin has students in «Хонандагон»; no per-olympiad assign UI yet).
    - Non-empty list = only those student codes (restriction mode).
    - Gmail synthetic ids are not enough for type=olympiad.
    """
    code = (student_code or "").strip()
    if not code:
        return {"allowed": False, "reason": "student_id_required"}

    is_gmail_synth = code.startswith("g:") or code.startswith("gmail:")

    student = find_student_by_code(code)
    try:
        parts = list_olympiad_participants(olympiad_id)
    except Exception as e:
        log.warning("participants check failed: %s", e)
        parts = []

    oly_type = "olympiad"
    try:
        from db.repo import find_olympiad
        oly = find_olympiad(olympiad_id)
        if oly:
            oly_type = (oly.get("type") or "olympiad").lower()
    except Exception:
        pass

    if is_gmail_synth:
        if oly_type == "olympiad":
            return {"allowed": False, "reason": "student_id_required"}
        # quiz-type: still need real student or open quiz policy
        if parts:
            return {"allowed": False, "reason": "not_assigned"}
        return {"allowed": False, "reason": "student_id_required"}

    if not student:
        return {"allowed": False, "reason": "student_not_found"}

    if not parts:
        # No restriction list → any active Student ID can take the event
        return {"allowed": True, "reason": "open_to_all_students", "student": student}

    ok = any(
        str(p.get("id") or "") == code and p.get("status", "assigned") == "assigned"
        for p in parts
    )
    if ok:
        return {"allowed": True, "reason": "assigned", "student": student}
    return {"allowed": False, "reason": "not_assigned", "student": student}
