"""Phase 9–12 — Olympiad Engine (boot-safe minimal)."""
from __future__ import annotations

import hashlib
import secrets
import time
import uuid
from datetime import datetime, timezone, timedelta

from db.repo import find_olympiad, DATA_DIR, _load_json, _save_json, _utc_now, list_results, save_result
from db.student_access import student_has_olympiad_access

SESSIONS_FILE = DATA_DIR / "olympiad_sessions.json"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def has_finished_attempt(olympiad_id: str, student_code: str, user_id: str | None = None) -> bool:
    keys = {str(student_code).strip()} if student_code else set()
    if user_id:
        keys.add(str(user_id))
        keys.add("g:" + str(user_id)[:40])
    for r in list_results():
        if str(r.get("olympiadId")) != str(olympiad_id):
            continue
        if r.get("status") not in ("passed", "failed", "submitted", "timeout"):
            continue
        sid = str(r.get("studentId") or r.get("student_code") or "")
        if sid in keys:
            return True
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
        ends_at = (_now() + timedelta(seconds=int(duration))).isoformat()
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
    }
    items = _load_json(SESSIONS_FILE)
    items.append(session)
    _save_json(SESSIONS_FILE, items)
    return session


def submit_exam(
    session_id: str,
    session_token: str,
    answers: dict,
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
    if session.get("status") == "submitted":
        raise ValueError("already_submitted")
    oly = find_olympiad(session["olympiadId"]) or {}
    qs = oly.get("questions") or []
    correct = 0
    total = len(qs)
    for i, q in enumerate(qs):
        sel = answers.get(str(i))
        try:
            if sel is not None and int(sel) == int(q.get("answer", -1)):
                correct += 1
        except (TypeError, ValueError):
            pass
    score = int(round(100 * correct / total)) if total else 0
    pass_score = int(oly.get("passScore") or 70)
    status = "passed" if score >= pass_score else "failed"
    session["status"] = "submitted"
    _save_json(SESSIONS_FILE, items)
    result = {
        "olympiadId": session["olympiadId"],
        "studentId": session.get("studentId"),
        "score": score,
        "correct": correct,
        "total": total,
        "passScore": pass_score,
        "status": status,
        "finishedAt": _utc_now(),
    }
    try:
        save_result(result)
    except Exception:
        pass
    return result
