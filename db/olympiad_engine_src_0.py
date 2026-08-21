"""P1 Olympiad Engine - P1.10 no answers to client, P1.11 server timer, P1.12 one attempt."""
from __future__ import annotations

import json
import logging
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from db.connection import get_session, is_postgres_enabled
from db.repo import DATA_DIR, find_olympiad
from db.student_access import student_has_olympiad_access

log = logging.getLogger("geografia.olympiad_engine")
SESSIONS_FILE = DATA_DIR / "exam_sessions.json"


def _load_sessions() -> dict:
    try:
        if not SESSIONS_FILE.exists():
            return {}
        data = json.loads(SESSIONS_FILE.read_text(encoding="utf-8-sig"))
        if isinstance(data, dict):
            return data
        if isinstance(data, list):
            out = {}
            for item in data:
                if isinstance(item, dict):
                    key = item.get("id") or item.get("sessionId")
                    if key:
                        out[str(key)] = item
            return out
    except Exception as e:
        log.warning("load sessions: %s", e)
    return {}


def _save_sessions(data: dict) -> None:
    try:
        DATA_DIR.mkdir(exist_ok=True)
        SESSIONS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        log.warning("save sessions: %s", e)


_FORBIDDEN_Q_KEYS = {
    "answer", "correct", "correctIndex", "correct_index", "is_correct",
    "isCorrect", "solution", "explanation",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_dt(v):
    if not v:
        return None
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    try:
        d = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Excep