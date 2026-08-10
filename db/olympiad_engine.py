"""Phase 9–12 — Olympiad Engine (hardened, attempts-table, no 500 on start/submit)."""
from __future__ import annotations

import logging
import secrets
import uuid
from datetime import datetime, timezone, timedelta

from sqlalchemy import text

from db.connection import get_session, is_postgres_enabled
from db.repo import find_olympiad, DATA_DIR, _load_json, _save_json, _utc_now
from db.student_access import student_has_olympiad_access

log = logging.getLogger("geografia.olympiad_engine")
SESSIONS_FILE = DATA_DIR / "olympiad_sessions.json"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _student_uuid(student_code: str):
    """Resolve students.id UUID from student_code; None if missing."""
    if not student_code or not is_postgres_enabled():
        return None
    try:
        with get_session() as s:
            return s.execute(
                text("SELECT id FROM students WHERE student_code = :c AND status = 'active'"),
                {"c": str(student_code).strip()},
            ).scalar()
    except Exception as e:
        log.warning("student uuid lookup failed: %s", e)
        return None


def has_finished_attempt(
    olympiad_id: str, student_code: str, user_id: str | None = None
) -> bool:
    """True if this student already has a finished olympiad attempt."""
    if not olympiad_id:
        return False
    # Prefer attempts table (production schema)
    if is_postgres_enabled():
        try:
            sid = _student_uuid(student_code)
            with get_session() as s:
                if sid is not None:
                    row = s.execute(
                        text(
                            "SELECT 1 FROM attempts "
                            "WHERE kind = 'olympiad' AND olympiad_id::text = :oid "
                            "AND student_id = :sid "
                            "AND status IN ('submitted','passed','failed','timeout') "
                            "LIMIT 1"
                        ),
                        {"oid": str(olympiad_id), "sid": sid},
                    ).first()
                    if row:
                        return True
                if user_id:
                    row = s.execute(
                        text(
                            "SELECT 1 FROM attempts "
                            "WHERE kind = 'olympiad' AND olympiad_id::text = :oid "
                            "AND user_id::text = :uid "
                            "AND status IN ('submitted','passed','failed','timeout') "
                            "LIMIT 1"
                        ),
                        {"oid": str(olympiad_id), "uid": str(user_id)},
                    ).first()
                    if row:
                        return True
        except Exception as e:
            log.warning("has_finished_attempt PG: %s", e)

    # JSON / legacy sessions fallback
    try:
        keys = {str(student_code).strip()} if student_code else set()
        if user_id:
            keys.add(str(user_id))
            keys.add("g:" + str(user_id)[:40])
        for s in _load_json(SESSIONS_FILE):
            if str(s.get("olympiadId")) != str(olympiad_id):
                continue
            if s.get("status") not in ("submitted", "passed", "failed", "timeout"):
                continue
            if str(s.get("studentId") or "") in keys:
                return True
    except Exception as e:
        log.warning("has_finished_attempt JSON: %s", e)
    return False


def start_exam(
    olympiad_id: str,
    student_code: str,
    user_id: str | None = None,
    client_fingerprint: str | None = None,
) -> dict:
    oly = find_olympiad(olympiad_id)
    if not oly:
        raise ValueError("not_found")

    access = student_has_olympiad_access(olympiad_id, student_code)
    if not access.get("allowed"):
        raise ValueError(access.get("reason") or "not_allowed")

    if has_finished_attempt(olympiad_id, student_code, user_id):
        raise ValueError("already_submitted")

    qs_raw = oly.get("questions") or []
    if not qs_raw:
        raise ValueError("no_questions")

    questions = []
    for i, q in enumerate(qs_raw):
        questions.append({
            "id": q.get("id", i + 1),
            "text": q.get("text"),
            "options": list(q.get("options") or []),
            "originalIndex": i,
        })

    session_id = str(uuid.uuid4())
    token = secrets.token_urlsafe(24)
    duration = oly.get("durationSec") or oly.get("duration_sec")
    ends_at = None
    if duration:
        try:
            ends_at = (_now() + timedelta(seconds=int(duration))).isoformat()
        except (TypeError, ValueError):
            ends_at = None

    student = access.get("student") or {}
    session = {
        "sessionId": session_id,
        "sessionToken": token,
        "olympiadId": olympiad_id,
        "studentId": student_code,
        "studentName": student.get("fullName") or student_code,
        "userId": user_id,
        "title": oly.get("title"),
        "passScore": oly.get("passScore") or 70,
        "questions": questions,
        "questionCount": len(questions),
        "startedAt": _utc_now(),
        "endsAt": ends_at,
        "answers": {},
        "status": "in_progress",
        "source": oly.get("type") or "olympiad",
    }

    # Persist session to JSON (always — works even if PG attempts insert fails)
    try:
        items = _load_json(SESSIONS_FILE)
        items.append(session)
        _save_json(SESSIONS_FILE, items)
    except Exception as e:
        log.error("session save failed: %s", e)
        raise ValueError("session_save_failed") from e

    # Optional: open in-progress row in attempts
    if is_postgres_enabled():
        try:
            sid = _student_uuid(student_code)
            with get_session() as s:
                s.execute(
                    text(
                        "INSERT INTO attempts "
                        "(id, kind, olympiad_id, student_id, user_id, student_name, "
                        " student_class, student_school, status, pass_score, total) "
                        "VALUES (:id, 'olympiad', :oid, :sid, :uid, :name, :cls, :sch, "
                        " 'in_progress', :ps, :total)"
                    ),
                    {
                        "id": session_id,
                        "oid": olympiad_id,
                        "sid": sid,
                        "uid": user_id,
                        "name": student.get("fullName") or student_code,
                        "cls": student.get("className") or "",
                        "sch": student.get("school") or "",
                        "ps": int(oly.get("passScore") or 70),
                        "total": len(questions),
                    },
                )
        except Exception as e:
            log.warning("attempts in_progress insert skipped: %s", e)

    return session


def autosave(
    session_id: str,
    session_token: str,
    answers: dict,
    fingerprint: str | None = None,
) -> dict:
    items = _load_json(SESSIONS_FILE)
    for s in items:
        if s.get("sessionId") == session_id and s.get("sessionToken") == session_token:
            if s.get("status") == "submitted":
                raise ValueError("already_submitted")
            s["answers"] = answers if isinstance(answers, dict) else {}
            _save_json(SESSIONS_FILE, items)
            return {"ok": True, "savedAt": _utc_now()}
    raise ValueError("session_not_found")


def submit_exam(
    session_id: str,
    session_token: str,
    answers: dict | None,
    fingerprint: str | None = None,
) -> dict:
    items = _load_json(SESSIONS_FILE)
    session = None
    for s in items:
        if s.get("sessionId") == session_id and s.get("sessionToken") == session_token:
            session = s
            break
    if not session:
        raise ValueError("session_not_found")
    if session.get("status") in ("submitted", "passed", "failed"):
        raise ValueError("already_submitted")

    oly = find_olympiad(session["olympiadId"]) or {}
    qs = oly.get("questions") or []
    ans = answers if isinstance(answers, dict) else (session.get("answers") or {})

    correct = 0
    total = len(qs)
    for i, q in enumerate(qs):
        key = str(q.get("id", i))
        sel = ans.get(key, ans.get(str(i)))
        try:
            if sel is not None and int(sel) == int(q.get("answer", -1)):
                correct += 1
        except (TypeError, ValueError):
            pass

    score = int(round(100 * correct / total)) if total else 0
    pass_score = int(oly.get("passScore") or 70)
    status = "passed" if score >= pass_score else "failed"

    session["status"] = "submitted"
    session["answers"] = ans
    session["score"] = score
    session["finishedAt"] = _utc_now()
    try:
        _save_json(SESSIONS_FILE, items)
    except Exception as e:
        log.warning("session submit save: %s", e)

    # Persist to attempts table
    if is_postgres_enabled():
        try:
            sid = _student_uuid(session.get("studentId") or "")
            with get_session() as s:
                # Update in-progress row if present, else insert
                updated = s.execute(
                    text(
                        "UPDATE attempts SET status = :st, score = :score, correct = :c, "
                        "total = :t, pass_score = :ps, finished_at = NOW() "
                        "WHERE id::text = :id"
                    ),
                    {
                        "st": status,
                        "score": score,
                        "c": correct,
                        "t": total,
                        "ps": pass_score,
                        "id": session_id,
                    },
                )
                if not updated.rowcount:
                    s.execute(
                        text(
                            "INSERT INTO attempts "
                            "(id, kind, olympiad_id, student_id, user_id, student_name, "
                            " score, correct, total, pass_score, status, finished_at) "
                            "VALUES (:id, 'olympiad', :oid, :sid, :uid, :name, "
                            " :score, :c, :t, :ps, :st, NOW())"
                        ),
                        {
                            "id": session_id,
                            "oid": session.get("olympiadId"),
                            "sid": sid,
                            "uid": session.get("userId"),
                            "name": session.get("studentName"),
                            "score": score,
                            "c": correct,
                            "t": total,
                            "ps": pass_score,
                            "st": status,
                        },
                    )
        except Exception as e:
            log.error("attempts submit persist: %s", e)

    return {
        "olympiadId": session.get("olympiadId"),
        "studentId": session.get("studentId"),
        "score": score,
        "correct": correct,
        "total": total,
        "passScore": pass_score,
        "status": status,
        "finishedAt": session.get("finishedAt"),
    }
