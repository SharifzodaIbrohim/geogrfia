"""Phase 9–12 — Olympiad Engine (hardened, attempts-table, no 500 on start/submit)."""
from __future__ import annotations

import logging
import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy import text

from db.connection import get_session, is_postgres_enabled
from db.repo import DATA_DIR, _load_json, _save_json, find_olympiad, use_pg
from db.student_access import student_has_olympiad_access

log = logging.getLogger("geografia.olympiad_engine")
SESSIONS_FILE = DATA_DIR / "exam_sessions.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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
    if is_postgres_enabled():
        try:
            sid = _student_uuid(student_code)
            with get_session() as s:
                if sid:
                    row = s.execute(
                        text(
                            "SELECT 1 FROM attempts WHERE kind = 'olympiad' "
                            "AND olympiad_id::text = :oid "
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
                            "SELECT 1 FROM attempts WHERE kind = 'olympiad' "
                            "AND olympiad_id::text = :oid "
                            "AND user_id::text = :uid "
                            "AND status IN ('submitted','passed','failed','timeout') "
                            "LIMIT 1"
                        ),
                        {"oid": str(olympiad_id), "uid": str(user_id)},
                    ).first()
                    if row:
                        return True
        except Exception as e:
            log.warning("has_finished_attempt pg: %s", e)
    try:
        sessions = _load_json(SESSIONS_FILE)
        keys = {str(student_code).strip()} if student_code else set()
        for s in sessions:
            if str(s.get("olympiadId")) != str(olympiad_id):
                continue
            if s.get("status") not in ("submitted", "passed", "failed", "timeout"):
                continue
            if str(s.get("studentId") or "") in keys:
                return True
    except Exception:
        pass
    return False


def start_exam(
    olympiad_id: str,
    student_code: str,
    user_id: str | None = None,
    fingerprint: str | None = None,
) -> dict:
    oly = find_olympiad(olympiad_id)
    if not oly:
        raise ValueError("not_found")
    access = student_has_olympiad_access(olympiad_id, student_code)
    if not access.get("allowed"):
        raise ValueError(access.get("reason") or "student_not_found")
    if has_finished_attempt(olympiad_id, student_code, user_id):
        raise ValueError("already_submitted")

    qs_src = list(oly.get("questions") or [])
    # shuffle order for exam presentation
    order = list(range(len(qs_src)))
    secrets.SystemRandom().shuffle(order)
    questions = []
    for disp_i, orig_i in enumerate(order):
        q = qs_src[orig_i]
        opts = list(q.get("options") or [])
        questions.append({
            "id": q.get("id") if q.get("id") is not None else orig_i,
            "text": q.get("text"),
            "options": opts,
            "originalIndex": orig_i,
        })

    session_id = str(uuid.uuid4())
    session_token = secrets.token_urlsafe(24)
    student = access.get("student") or {}
    session = {
        "sessionId": session_id,
        "sessionToken": session_token,
        "olympiadId": olympiad_id,
        "studentId": student_code,
        "studentName": student.get("fullName") or student_code,
        "userId": user_id,
        "status": "in_progress",
        "answers": {},
        "questions": questions,
        "passScore": oly.get("passScore") or 70,
        "startedAt": _utc_now(),
        "fingerprint": fingerprint,
    }
    try:
        items = _load_json(SESSIONS_FILE)
        items.append(session)
        _save_json(SESSIONS_FILE, items)
    except Exception as e:
        log.warning("session save: %s", e)

    if is_postgres_enabled():
        try:
            sid = _student_uuid(student_code)
            with get_session() as s:
                s.execute(
                    text(
                        "INSERT INTO attempts "
                        "(id, kind, olympiad_id, student_id, user_id, student_name, "
                        " student_class, student_school, status, pass_score, total) "
                        "VALUES (:id, 'olympiad', :oid, :sid, :uid, :name, "
                        " :cls, :sch, 'in_progress', :ps, :total)"
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
            log.warning("attempt start persist: %s", e)

    return {
        "sessionId": session_id,
        "sessionToken": session_token,
        "olympiadId": olympiad_id,
        "title": oly.get("title"),
        "passScore": oly.get("passScore") or 70,
        "durationSec": oly.get("durationSec"),
        "questions": questions,
    }


def autosave(
    session_id: str,
    session_token: str,
    answers: dict | None,
    fingerprint: str | None = None,
) -> dict:
    items = _load_json(SESSIONS_FILE)
    for s in items:
        if s.get("sessionId") == session_id and s.get("sessionToken") == session_token:
            if s.get("status") in ("submitted", "passed", "failed"):
                raise ValueError("already_submitted")
            if isinstance(answers, dict):
                s["answers"] = answers
            try:
                _save_json(SESSIONS_FILE, items)
            except Exception as e:
                log.warning("autosave: %s", e)
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
        candidates = [
            str(q.get("originalIndex")) if q.get("originalIndex") is not None else None,
            str(q.get("id")) if q.get("id") is not None else None,
            str(i),
            i,
        ]
        # also accept keys from shuffled session questions
        for sq in session.get("questions") or []:
            if sq.get("originalIndex") == i or str(sq.get("id")) == str(q.get("id")):
                if sq.get("id") is not None:
                    candidates.append(str(sq.get("id")))
                if sq.get("originalIndex") is not None:
                    candidates.append(str(sq.get("originalIndex")))
        sel = None
        for k in candidates:
            if k is None:
                continue
            if k in ans:
                sel = ans[k]
                break
            if str(k) in ans:
                sel = ans[str(k)]
                break
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

    if is_postgres_enabled():
        try:
            sid = _student_uuid(session.get("studentId") or "")
            with get_session() as s:
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
        "ok": True,
        "result": {
            "olympiadId": session.get("olympiadId"),
            "studentId": session.get("studentId"),
            "score": score,
            "correct": correct,
            "total": total,
            "passScore": pass_score,
            "status": status,
            "finishedAt": session.get("finishedAt"),
        },
        # flat fields for older clients
        "olympiadId": session.get("olympiadId"),
        "studentId": session.get("studentId"),
        "score": score,
        "correct": correct,
        "total": total,
        "passScore": pass_score,
        "status": status,
        "finishedAt": session.get("finishedAt"),
    }
