"""
Phase 8 — Quiz Platform
- access: public | google | school
- timer via time_limit_sec + attempt.started_at
- score server-side only
- history for Google users (and optional student)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy import text

from db.connection import get_session
from db.repo import use_pg, DATA_DIR, _load_json, _save_json, _utc_now

QUIZZES_FILE = DATA_DIR / "quizzes.json"
QUIZ_ATTEMPTS_FILE = DATA_DIR / "quiz_attempts.json"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def ensure_quiz_columns() -> None:
    """Best-effort migration for access_mode / school filter."""
    if not use_pg():
        return
    with get_session() as s:
        s.execute(text(
            "ALTER TABLE quizzes ADD COLUMN IF NOT EXISTS access_mode TEXT NOT NULL DEFAULT 'public'"
        ))
        s.execute(text(
            "ALTER TABLE quizzes ADD COLUMN IF NOT EXISTS school_name TEXT"
        ))


def list_quizzes(include_draft: bool = False) -> list[dict]:
    ensure_quiz_columns()
    if use_pg():
        with get_session() as s:
            q = (
                "SELECT id::text, title, description, pass_score, time_limit_sec, is_public, "
                "COALESCE(access_mode, 'public') AS access_mode, school_name, status, "
                "created_at, updated_at "
                "FROM quizzes "
            )
            if not include_draft:
                q += "WHERE status = 'published' "
            q += "ORDER BY created_at DESC"
            rows = s.execute(text(q)).mappings().all()
            out = []
            for r in rows:
                out.append(_quiz_row(r, with_questions=False, session=s))
            return out
    items = _load_json(QUIZZES_FILE)
    if not include_draft:
        items = [x for x in items if x.get("status", "published") == "published"]
    return items


def _quiz_row(r, with_questions: bool, session=None, include_answers: bool = False) -> dict:
    qid = r["id"] if isinstance(r["id"], str) else str(r["id"])
    item = {
        "id": qid,
        "title": r["title"],
        "description": r.get("description"),
        "passScore": r.get("pass_score") if "pass_score" in r else r.get("passScore", 70),
        "timeLimitSec": r.get("time_limit_sec") if "time_limit_sec" in r else r.get("timeLimitSec"),
        "isPublic": bool(r.get("is_public", r.get("isPublic", True))),
        "accessMode": r.get("access_mode") or r.get("accessMode") or "public",
        "schoolName": r.get("school_name") or r.get("schoolName"),
        "status": r.get("status") or "published",
        "createdAt": (
            r["created_at"].isoformat()
            if hasattr(r.get("created_at"), "isoformat")
            else r.get("createdAt")
        ),
    }
    if with_questions and session is not None:
        item["questions"] = _load_questions(session, qid, include_answers)
        item["questionCount"] = len(item["questions"])
    elif with_questions:
        item["questions"] = r.get("questions") or []
        item["questionCount"] = len(item["questions"])
    else:
        if session is not None:
            cnt = session.execute(
                text("SELECT COUNT(*) FROM quiz_questions WHERE quiz_id::text = :id"),
                {"id": qid},
            ).scalar()
            item["questionCount"] = int(cnt or 0)
        else:
            item["questionCount"] = len(r.get("questions") or [])
    return item


def _load_questions(session, quiz_id: str, include_answers: bool) -> list[dict]:
    qrows = session.execute(
        text(
            "SELECT id::text, sort_order, text FROM quiz_questions "
            "WHERE quiz_id::text = :id ORDER BY sort_order"
        ),
        {"id": quiz_id},
    ).mappings().all()
    questions = []
    for i, q in enumerate(qrows):
        opts = session.execute(
            text(
                "SELECT id::text, text, is_correct, sort_order FROM quiz_options "
                "WHERE question_id = :qid ORDER BY sort_order"
            ),
            {"qid": q["id"]},
        ).mappings().all()
        options = [{"id": o["id"], "text": o["text"]} for o in opts]
        item = {
            "id": q["id"],
            "sortOrder": q["sort_order"],
            "text": q["text"],
            "options": [o["text"] for o in opts],
            "optionIds": [o["id"] for o in opts],
        }
        if include_answers:
            item["answer"] = next((j for j, o in enumerate(opts) if o["is_correct"]), 0)
        questions.append(item)
    return questions


def get_quiz(quiz_id: str, include_answers: bool = False) -> dict | None:
    ensure_quiz_columns()
    if use_pg():
        with get_session() as s:
            r = s.execute(
                text(
                    "SELECT id::text, title, description, pass_score, time_limit_sec, is_public, "
                    "COALESCE(access_mode, 'public') AS access_mode, school_name, status, created_at "
                    "FROM quizzes WHERE id::text = :id"
                ),
                {"id": quiz_id},
            ).mappings().first()
            if not r:
                return None
            return _quiz_row(r, with_questions=True, session=s, include_answers=include_answers)
    for q in _load_json(QUIZZES_FILE):
        if q.get("id") == quiz_id:
            out = dict(q)
            if not include_answers:
                qs = []
                for qq in out.get("questions") or []:
                    qs.append({
                        "id": qq.get("id"),
                        "text": qq.get("text"),
                        "options": qq.get("options") or [],
                    })
                out["questions"] = qs
            return out
    return None


def create_quiz(data: dict) -> dict:
    ensure_quiz_columns()
    qid = str(uuid.uuid4())
    created = _utc_now()
    title = data["title"]
    description = data.get("description") or ""
    pass_score = int(data.get("passScore") or 70)
    time_limit = data.get("timeLimitSec")
    time_limit = int(time_limit) if time_limit not in (None, "") else None
    access_mode = (data.get("accessMode") or "public").strip().lower()
    if access_mode not in ("public", "google", "school"):
        access_mode = "public"
    school_name = data.get("schoolName") or None
    status = data.get("status") or "published"
    questions = data.get("questions") or []

    if use_pg():
        with get_session() as s:
            s.execute(
                text(
                    "INSERT INTO quizzes "
                    "(id, title, description, pass_score, time_limit_sec, is_public, "
                    " access_mode, school_name, status) "
                    "VALUES (:id, :title, :desc, :ps, :tl, :pub, :am, :sn, :st)"
                ),
                {
                    "id": qid,
                    "title": title,
                    "desc": description,
                    "ps": pass_score,
                    "tl": time_limit,
                    "pub": access_mode == "public",
                    "am": access_mode,
                    "sn": school_name,
                    "st": status,
                },
            )
            for i, q in enumerate(questions):
                qqid = str(uuid.uuid4())
                s.execute(
                    text(
                        "INSERT INTO quiz_questions (id, quiz_id, sort_order, text) "
                        "VALUES (:id, :qid, :ord, :text)"
                    ),
                    {"id": qqid, "qid": qid, "ord": i, "text": q["text"]},
                )
                ans = int(q.get("answer") or 0)
                for j, opt in enumerate(q.get("options") or []):
                    s.execute(
                        text(
                            "INSERT INTO quiz_options "
                            "(id, question_id, sort_order, text, is_correct) "
                            "VALUES (:id, :qid, :ord, :text, :ok)"
                        ),
                        {
                            "id": str(uuid.uuid4()),
                            "qid": qqid,
                            "ord": j,
                            "text": str(opt),
                            "ok": j == ans,
                        },
                    )
        return get_quiz(qid, include_answers=True)

    row = {
        "id": qid,
        "title": title,
        "description": description,
        "passScore": pass_score,
        "timeLimitSec": time_limit,
        "accessMode": access_mode,
        "schoolName": school_name,
        "status": status,
        "isPublic": access_mode == "public",
        "questions": [
            {
                "id": str(uuid.uuid4()),
                "text": q["text"],
                "options": q.get("options") or [],
                "answer": int(q.get("answer") or 0),
            }
            for q in questions
        ],
        "createdAt": created,
    }
    items = _load_json(QUIZZES_FILE)
    items.append(row)
    _save_json(QUIZZES_FILE, items)
    return row


def delete_quiz(quiz_id: str) -> bool:
    if use_pg():
        with get_session() as s:
            res = s.execute(text("DELETE FROM quizzes WHERE id::text = :id"), {"id": quiz_id})
            return res.rowcount > 0
    items = _load_json(QUIZZES_FILE)
    new_list = [x for x in items if x.get("id") != quiz_id]
    if len(new_list) == len(items):
        return False
    _save_json(QUIZZES_FILE, new_list)
    return True


def set_quiz_status(quiz_id: str, status: str) -> dict | None:
    if status not in ("draft", "published", "archived"):
        status = "published"
    if use_pg():
        with get_session() as s:
            s.execute(
                text("UPDATE quizzes SET status = :st, updated_at = now() WHERE id::text = :id"),
                {"st": status, "id": quiz_id},
            )
        return get_quiz(quiz_id, include_answers=True)
    items = _load_json(QUIZZES_FILE)
    for q in items:
        if q.get("id") == quiz_id:
            q["status"] = status
            _save_json(QUIZZES_FILE, items)
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
    if mode == "school":
        if not student:
            return {"allowed": False, "reason": "student_required"}
        want = (quiz.get("schoolName") or "").strip().lower()
        if want and (student.get("school") or "").strip().lower() != want:
            return {"allowed": False, "reason": "wrong_school"}
        return {"allowed": True, "reason": "school"}
    return {"allowed": False, "reason": "unknown_mode"}


def start_attempt(quiz_id: str, user_id: str | None = None, student_id: str | None = None) -> dict:
    quiz = get_quiz(quiz_id, include_answers=False)
    if not quiz:
        raise ValueError("not_found")
    if quiz.get("status") != "published":
        raise ValueError("not_published")

    aid = str(uuid.uuid4())
    started = _now()
    limit = quiz.get("timeLimitSec")
    ends_at = None
    if limit:
        ends_at = started + timedelta(seconds=int(limit))

    if use_pg():
        with get_session() as s:
            s.execute(
                text(
                    "INSERT INTO attempts "
                    "(id, kind, quiz_id, user_id, student_id, status, started_at, pass_score, total) "
                    "VALUES (:id, 'quiz', :qid, :uid, :sid, 'in_progress', :st, :ps, :total)"
                ),
                {
                    "id": aid,
                    "qid": quiz_id,
                    "uid": user_id,
                    "sid": None,  # student UUID optional; we store code in JSON path
                    "st": started,
                    "ps": quiz.get("passScore") or 70,
                    "total": quiz.get("questionCount") or 0,
                },
            )
    else:
        items = _load_json(QUIZ_ATTEMPTS_FILE)
        items.append({
            "id": aid,
            "kind": "quiz",
            "quizId": quiz_id,
            "userId": user_id,
            "studentCode": student_id,
            "status": "in_progress",
            "startedAt": started.isoformat(),
            "endsAt": ends_at.isoformat() if ends_at else None,
            "passScore": quiz.get("passScore") or 70,
        })
        _save_json(QUIZ_ATTEMPTS_FILE, items)

    return {
        "attemptId": aid,
        "quizId": quiz_id,
        "startedAt": started.isoformat(),
        "endsAt": ends_at.isoformat() if ends_at else None,
        "timeLimitSec": limit,
        "questionCount": quiz.get("questionCount") or len(quiz.get("questions") or []),
        "questions": quiz.get("questions") or [],
        "passScore": quiz.get("passScore") or 70,
        "title": quiz.get("title"),
    }


def submit_attempt(
    quiz_id: str,
    attempt_id: str,
    answers: list,
    user_id: str | None = None,
) -> dict:
    quiz = get_quiz(quiz_id, include_answers=True)
    if not quiz:
        raise ValueError("not_found")

    started = None
    if use_pg():
        with get_session() as s:
            row = s.execute(
                text(
                    "SELECT id::text, started_at, status FROM attempts "
                    "WHERE id::text = :id AND kind = 'quiz' AND quiz_id::text = :qid"
                ),
                {"id": attempt_id, "qid": quiz_id},
            ).mappings().first()
            if not row:
                raise ValueError("attempt_not_found")
            if row["status"] not in ("in_progress",):
                raise ValueError("already_submitted")
            started = row["started_at"]
            if started and started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
    else:
        items = _load_json(QUIZ_ATTEMPTS_FILE)
        row = next((a for a in items if a.get("id") == attempt_id and a.get("quizId") == quiz_id), None)
        if not row:
            raise ValueError("attempt_not_found")
        if row.get("status") != "in_progress":
            raise ValueError("already_submitted")
        started = datetime.fromisoformat(row["startedAt"].replace("Z", "+00:00"))

    limit = quiz.get("timeLimitSec")
    if limit and started:
        deadline = started + timedelta(seconds=int(limit) + 15)  # 15s grace
        if _now() > deadline:
            # still score, but mark timed_out
            timed_out = True
        else:
            timed_out = False
    else:
        timed_out = False

    # Server-side scoring
    questions = quiz.get("questions") or []
    selected_map: dict[Any, int] = {}
    if isinstance(answers, list):
        for i, a in enumerate(answers):
            if isinstance(a, dict):
                qkey = a.get("questionId") or a.get("id") or (i + 1)
                try:
                    selected_map[str(qkey)] = int(a.get("selected"))
                except (TypeError, ValueError):
                    continue
            else:
                try:
                    selected_map[str(i + 1)] = int(a)
                except (TypeError, ValueError):
                    continue

    correct = 0
    detail = []
    for i, q in enumerate(questions):
        qid = str(q.get("id") or (i + 1))
        right = int(q.get("answer") or 0)
        sel = selected_map.get(qid)
        if sel is None:
            sel = selected_map.get(str(i + 1))
        is_ok = sel is not None and sel == right
        if is_ok:
            correct += 1
        detail.append({"questionId": qid, "selected": sel, "correct": is_ok})

    total = len(questions) or 1
    score = round((correct / total) * 100) if questions else 0
    pass_score = int(quiz.get("passScore") or 70)
    status = "passed" if score >= pass_score else "failed"
    if timed_out and status == "passed":
        # still allow pass if answers within grace; flag only
        pass
    finished = _now()

    if use_pg():
        with get_session() as s:
            s.execute(
                text(
                    "UPDATE attempts SET score = :sc, correct = :c, total = :t, "
                    "pass_score = :ps, status = :st, finished_at = :fin, user_id = COALESCE(user_id, :uid) "
                    "WHERE id::text = :id"
                ),
                {
                    "sc": score,
                    "c": correct,
                    "t": len(questions),
                    "ps": pass_score,
                    "st": status,
                    "fin": finished,
                    "uid": user_id,
                    "id": attempt_id,
                },
            )
            for d in detail:
                s.execute(
                    text(
                        "INSERT INTO attempt_answers (id, attempt_id, question_id, selected_idx, is_correct) "
                        "VALUES (:id, :aid, :qid, :sel, :ok) "
                        "ON CONFLICT (attempt_id, question_id) DO UPDATE "
                        "SET selected_idx = EXCLUDED.selected_idx, is_correct = EXCLUDED.is_correct"
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "aid": attempt_id,
                        "qid": d["questionId"],
                        "sel": d["selected"],
                        "ok": d["correct"],
                    },
                )
    else:
        items = _load_json(QUIZ_ATTEMPTS_FILE)
        for a in items:
            if a.get("id") == attempt_id:
                a["status"] = status
                a["score"] = score
                a["correct"] = correct
                a["total"] = len(questions)
                a["passScore"] = pass_score
                a["finishedAt"] = finished.isoformat()
                a["timedOut"] = timed_out
                a["answers"] = detail
                if user_id:
                    a["userId"] = user_id
                break
        _save_json(QUIZ_ATTEMPTS_FILE, items)

    return {
        "attemptId": attempt_id,
        "quizId": quiz_id,
        "score": score,
        "correct": correct,
        "total": len(questions),
        "passScore": pass_score,
        "status": status,
        "timedOut": timed_out,
        "finishedAt": finished.isoformat(),
    }


def user_history(user_id: str) -> list[dict]:
    if use_pg():
        with get_session() as s:
            rows = s.execute(
                text(
                    "SELECT a.id::text, a.quiz_id::text, a.score, a.correct, a.total, "
                    "a.pass_score, a.status, a.started_at, a.finished_at, q.title "
                    "FROM attempts a "
                    "LEFT JOIN quizzes q ON q.id = a.quiz_id "
                    "WHERE a.kind = 'quiz' AND a.user_id::text = :uid "
                    "AND a.status IN ('passed', 'failed', 'submitted') "
                    "ORDER BY a.finished_at DESC NULLS LAST LIMIT 50"
                ),
                {"uid": user_id},
            ).mappings().all()
            return [
                {
                    "attemptId": r["id"],
                    "quizId": r["quiz_id"],
                    "title": r["title"],
                    "score": r["score"],
                    "correct": r["correct"],
                    "total": r["total"],
                    "passScore": r["pass_score"],
                    "status": r["status"],
                    "startedAt": r["started_at"].isoformat() if r["started_at"] else None,
                    "finishedAt": r["finished_at"].isoformat() if r["finished_at"] else None,
                }
                for r in rows
            ]
    items = [
        a for a in _load_json(QUIZ_ATTEMPTS_FILE)
        if a.get("userId") == user_id and a.get("status") in ("passed", "failed", "submitted")
    ]
    items.sort(key=lambda x: x.get("finishedAt") or "", reverse=True)
    return items[:50]
