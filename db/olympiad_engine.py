"""P1 Olympiad Engine — temporary boot-safe stub (restore full after meeting)."""
from __future__ import annotations

import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone

log = logging.getLogger("geografia.olympiad_engine")

def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _now() -> datetime:
    return datetime.now(timezone.utc)

def has_finished_attempt(student_id, olympiad_id):
    return False

def find_open_attempt(student_id, olympiad_id):
    return None

def start_exam(student_id, olympiad_id, **kwargs):
    try:
        from db.repo import find_olympiad
        from db.student_access import student_has_olympiad_access
        oly = find_olympiad(olympiad_id)
        if not oly:
            return {"ok": False, "error": "olympiad not found"}, 404
        if not student_has_olympiad_access(student_id, oly):
            return {"ok": False, "error": "access denied"}, 403
    except Exception as e:
        log.exception("start_exam")
        return {"ok": False, "error": str(e)}, 500
    session_id = str(uuid.uuid4())
    return {
        "ok": True,
        "attemptId": session_id,
        "sessionId": session_id,
        "questions": [],
        "remainingSec": 3600,
        "serverNow": _utc_now(),
        "message": "engine stub — full restore pending",
    }

def autosave(session_id, answers, **kwargs):
    return {"ok": True}

def submit_exam(session_id, answers=None, **kwargs):
    return {
        "ok": True,
        "result": {
            "attemptId": session_id,
            "score": 0,
            "correct": 0,
            "total": 0,
            "status": "submitted",
            "serverNow": _utc_now(),
        },
    }
