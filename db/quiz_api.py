"""Phase 8 — Quiz API (minimal boot-safe)."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text

from db.connection import get_session, is_postgres_enabled
from db.repo import DATA_DIR, _load_json, _save_json, use_pg

QUIZZES_FILE = DATA_DIR / "quizzes.json"
ATTEMPTS_FILE = DATA_DIR / "quiz_attempts.json"


def list_quizzes(include_draft: bool = False) -> list[dict]:
    if use_pg():
        try:
            with get_session() as s:
                rows = s.execute(text(
                    "SELECT id::text, title, description, pass_score, time_limit_sec, "
                    "COALESCE(access_mode, 'public') AS access_mode, school_name, status, "
                    "questions, created_at FROM quizzes ORDER BY created_at DESC"
                )).mappings().all()
                out = []
                for r in rows:
                    if not include_draft and (r.get("status") or "published") != "published":
                        continue
                    qs = r.get("questions") or []
                    if isinstance(qs, str):
                        try:
                            qs = json.loads(qs)
                        except Exception:
                            qs = []
                    out.append({
                        "id": r["id"], "title": r["title"], "description": r.get("description") or "",
                        "passScore": r.get("pass_score") or 70,
                        "timeLimitSec": r.get("time_limit_sec"),
                        "accessMode": r.get("access_mode") or "public",
                        "schoolName": r.get("school_name"),
                        "status": r.get("status") or "published",
                        "questions": qs if isinstance(qs, list) else [],
                        "questionCount": len(qs) if isinstance(qs, list) else 0,
                    })
                return out
        except Exception:
            pass
    items = _load_json(QUIZZES_FILE)
    if not include_draft:
        items = [q for q in items if (q.get("status") or "published") == "published"]
    return items


def get_quiz(quiz_id: str, include_answers: bool = False) -> dict | None:
    for q in list_quizzes(include_draft=True):
        if q.get("id") == quiz_id:
            if not include_answers:
                qs = []
                for item in (q.get("questions") or []):
                    qs.append({
                        "id": item.get("id"),
                        "text": item.get("text"),
                        "options": list(item.get("options") or []),
                    })
                q = dict(q)
                q["questions"] = qs
            return q
    return None


def check_access(quiz: dict, user: dict | None, student: dict | None) -> dict:
    mode = (quiz.get("accessMode") or "public").lower()
    if quiz.get("status") and quiz["status"] != "published":
        return {"allowed": False, "reason": "not_published"}
    if mode == "public":
        return {"allowed": True, "reason": "public"}
    if mode == "google":
        if user:
            return {"allowed": True, "reason": "google"}
        return {"allowed": False, "reason": "google_required"}
    if mode in ("school", "olympiad"):
        if not student:
            return {"allowed": False, "reason": "student_required"}
        return {"allowed": True, "reason": "school"}
    return {"allowed": False, "reason": "unknown_mode"}


def start_attempt(quiz_id: str, user_id: str | None = None, student_id: str | None = None) -> dict:
    quiz = get_quiz(quiz_id, include_answers=False)
    if not quiz:
        raise ValueError("not_found")
    attempt_id = str(uuid.uuid4())
    return {
        "attemptId": attempt_id,
        "sessionId": attempt_id,
        "quizId": quiz_id,
        "title": quiz.get("title"),
        "questions": quiz.get("questions") or [],
        "passScore": quiz.get("passScore") or 70,
        "timeLimitSec": quiz.get("timeLimitSec"),
        "source": "quiz",
    }


def submit_attempt(quiz_id: str, attempt_id: str, answers, user_id: str | None = None) -> dict:
    quiz = get_quiz(quiz_id, include_answers=True)
    if not quiz:
        raise ValueError("not_found")
    qs = quiz.get("questions") or []
    correct = 0
    total = len(qs)
    ans_map = {}
    if isinstance(answers, dict):
        ans_map = answers
    elif isinstance(answers, list):
        for i, a in enumerate(answers):
            if isinstance(a, dict):
                key = a.get("questionId", a.get("originalIndex", i))
                ans_map[str(key)] = a.get("selected")
            else:
                ans_map[str(i)] = a
    for i, q in enumerate(qs):
        sel = ans_map.get(str(q.get("id"), ans_map.get(str(i))))
        try:
            if sel is not None and int(sel) == int(q.get("answer", -1)):
                correct += 1
        except (TypeError, ValueError):
            pass
    score = int(round(100 * correct / total)) if total else 0
    pass_score = int(quiz.get("passScore") or 70)
    return {
        "score": score,
        "correct": correct,
        "total": total,
        "passScore": pass_score,
        "status": "passed" if score >= pass_score else "failed",
    }


def user_history(user_id: str) -> list:
    return []


def create_quiz(data: dict) -> dict:
    quiz = {
        "id": str(uuid.uuid4()),
        "title": data.get("title"),
        "description": data.get("description") or "",
        "passScore": data.get("passScore") or 70,
        "timeLimitSec": data.get("timeLimitSec"),
        "accessMode": data.get("accessMode") or "public",
        "schoolName": data.get("schoolName"),
        "status": data.get("status") or "published",
        "questions": data.get("questions") or [],
        "questionCount": len(data.get("questions") or []),
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    items = _load_json(QUIZZES_FILE)
    items.append(quiz)
    _save_json(QUIZZES_FILE, items)
    return quiz


def delete_quiz(quiz_id: str) -> bool:
    items = _load_json(QUIZZES_FILE)
    new = [q for q in items if q.get("id") != quiz_id]
    if len(new) == len(items):
        return False
    _save_json(QUIZZES_FILE, new)
    return True


def set_quiz_status(quiz_id: str, status: str) -> dict | None:
    items = _load_json(QUIZZES_FILE)
    for q in items:
        if q.get("id") == quiz_id:
            q["status"] = status
            _save_json(QUIZZES_FILE, items)
            return q
    return None
