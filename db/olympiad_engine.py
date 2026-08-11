"""
P1 — Olympiad Exam Engine

Flow:
  Admin publishes (is_active + start_at/end_at)
    → Student authorized (Student ID + participant rules)
    → server creates attempt (in_progress, expires_at)
    → client autosaves answers (attempt_answers)
    → server scores on submit (correct/total/score/status)

Frontend never calculates score — only displays server result.
"""
from __future__ import annotations

import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import text

from db.connection import get_session, is_postgres_enabled
from db.repo import DATA_DIR, _load_json, _save_json, find_olympiad
from db.student_access import student_has_olympiad_access

log = logging.getLogger("geografia.olympiad_engine")
SESSIONS_FILE = DATA_DIR / "exam_sessions.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_dt(v) -> datetime | None:
    if not v:
        return None
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    try:
        d = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _student_uuid(student_code: str):
    if not student_code or not is_postgres_enabled():
        return None
    try:
        with get_session() as s:
            return s.execute(
                text(
                    "SELECT id FROM students "
                    "WHERE student_code = :c AND status = 'active'"
                ),
                {"c": str(student_code).strip()},
            ).scalar()
    except Exception as e:
        log.warning("student uuid lookup failed: %s", e)
        return None


def _window_ok(oly: dict) -> str:
    """Return 'open' or reason code."""
    if not oly.get("isActive"):
        return "closed"
    now = _now()
    start = _parse_dt(oly.get("startTime") or oly.get("start_at"))
    end = _parse_dt(oly.get("endTime") or oly.get("end_at"))
    if start and now < start:
        return "not_started"
    if end and now > end:
        return "ended"
    return "open"


def _compute_expires(oly: dict, started: datetime) -> datetime | None:
    candidates: list[datetime] = []
    dur = oly.get("durationSec")
    try:
        if dur is not None and int(dur) > 0:
            candidates.append(started + timedelta(seconds=int(dur)))
    except (TypeError, ValueError):
        pass
    end = _parse_dt(oly.get("endTime") or oly.get("end_at"))
    if end:
        candidates.append(end)
    if not candidates:
        return None
    return min(candidates)


def has_finished_attempt(
    olympiad_id: str, student_code: str, user_id: str | None = None
) -> bool:
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
                            "AND olympiad_id::text = :oid AND student_id = :sid "
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
                            "AND olympiad_id::text = :oid AND user_id::text = :uid "
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
        for s in _load_json(SESSIONS_FILE):
            if str(s.get("olympiadId")) != str(olympiad_id):
                continue
            if s.get("status") not in ("submitted", "passed", "failed", "timeout"):
                continue
            if str(s.get("studentId") or "") == str(student_code).strip():
                return True
    except Exception:
        pass
    return False


def _public_questions(qs_src: list[dict]) -> list[dict]:
    """Shuffle presentation; NEVER include correct answer."""
    order = list(range(len(qs_src)))
    secrets.SystemRandom().shuffle(order)
    out = []
    for orig_i in order:
        q = qs_src[orig_i]
        qid = q.get("id")
        if qid is None:
            qid = str(orig_i)
        out.append({
            "id": str(qid),
            "text": q.get("text"),
            "options": list(q.get("options") or []),
            "originalIndex": orig_i,
        })
    return out


def start_exam(
    olympiad_id: str,
    student_code: str,
    user_id: str | None = None,
    fingerprint: str | None = None,
) -> dict:
    oly = find_olympiad(olympiad_id)
    if not oly:
        raise ValueError("not_found")

    window = _window_ok(oly)
    if window != "open":
        raise ValueError(window)

    access = student_has_olympiad_access(olympiad_id, student_code)
    if not access.get("allowed"):
        raise ValueError(access.get("reason") or "student_not_found")

    if has_finished_attempt(olympiad_id, student_code, user_id):
        raise ValueError("already_submitted")

    qs_src = list(oly.get("questions") or [])
    if not qs_src:
        raise ValueError("no_questions")

    questions = _public_questions(qs_src)
    started = _now()
    expires = _compute_expires(oly, started)
    attempt_id = str(uuid.uuid4())
    session_token = secrets.token_urlsafe(24)
    student = access.get("student") or {}
    pass_score = int(oly.get("passScore") or 70)

    session = {
        "sessionId": attempt_id,
        "attemptId": attempt_id,
        "sessionToken": session_token,
        "olympiadId": olympiad_id,
        "studentId": student_code,
        "studentName": student.get("fullName") or student_code,
        "userId": user_id,
        "status": "in_progress",
        "answers": {},
        "questions": questions,
        "passScore": pass_score,
        "startedAt": started.isoformat(),
        "expiresAt": expires.isoformat() if expires else None,
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
                        " student_class, student_school, status, pass_score, total, "
                        " started_at, expires_at, session_token) "
                        "VALUES (:id, 'olympiad', :oid, :sid, :uid, :name, "
                        " :cls, :sch, 'in_progress', :ps, :total, :st, :ex, :tok)"
                    ),
                    {
                        "id": attempt_id,
                        "oid": olympiad_id,
                        "sid": sid,
                        "uid": user_id,
                        "name": student.get("fullName") or student_code,
                        "cls": student.get("className") or "",
                        "sch": student.get("school") or "",
                        "ps": pass_score,
                        "total": len(questions),
                        "st": started,
                        "ex": expires,
                        "tok": session_token,
                    },
                )
        except Exception as e:
            # Fallback without new columns if migration not applied yet
            log.warning("attempt start persist (retry minimal): %s", e)
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
                            "id": attempt_id,
                            "oid": olympiad_id,
                            "sid": sid,
                            "uid": user_id,
                            "name": student.get("fullName") or student_code,
                            "cls": student.get("className") or "",
                            "sch": student.get("school") or "",
                            "ps": pass_score,
                            "total": len(questions),
                        },
                    )
            except Exception as e2:
                log.warning("attempt start persist failed: %s", e2)

    return {
        "sessionId": attempt_id,
        "attemptId": attempt_id,
        "sessionToken": session_token,
        "olympiadId": olympiad_id,
        "title": oly.get("title"),
        "passScore": pass_score,
        "durationSec": oly.get("durationSec"),
        "startedAt": session["startedAt"],
        "expiresAt": session["expiresAt"],
        "endsAt": session["expiresAt"],
        "questions": questions,  # no correct answers
        "status": "in_progress",
    }


def _load_session(session_id: str, session_token: str) -> tuple[dict, list]:
    items = _load_json(SESSIONS_FILE)
    for s in items:
        if s.get("sessionId") == session_id and s.get("sessionToken") == session_token:
            return s, items
    raise ValueError("session_not_found")


def _persist_answers_pg(attempt_id: str, answers: dict, questions: list[dict]) -> None:
    if not is_postgres_enabled() or not answers:
        return
    # Map question keys → UUID when possible
    try:
        with get_session() as s:
            for q in questions:
                qid = str(q.get("id"))
                sel = None
                for k in (qid, str(q.get("originalIndex")), q.get("originalIndex")):
                    if k is None:
                        continue
                    if k in answers:
                        sel = answers[k]
                        break
                    if str(k) in answers:
                        sel = answers[str(k)]
                        break
                if sel is None:
                    continue
                try:
                    sel_i = int(sel)
                except (TypeError, ValueError):
                    continue
                # question_id must be UUID in schema — skip non-uuid
                try:
                    uuid.UUID(str(qid))
                except Exception:
                    continue
                s.execute(
                    text(
                        "INSERT INTO attempt_answers "
                        "(id, attempt_id, question_id, selected_idx, saved_at) "
                        "VALUES (:id, :aid, :qid, :sel, NOW()) "
                        "ON CONFLICT (attempt_id, question_id) DO UPDATE SET "
                        "selected_idx = EXCLUDED.selected_idx, saved_at = NOW()"
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "aid": attempt_id,
                        "qid": qid,
                        "sel": sel_i,
                    },
                )
    except Exception as e:
        log.warning("persist answers: %s", e)


def autosave(
    session_id: str,
    session_token: str,
    answers: dict | None,
    fingerprint: str | None = None,
) -> dict:
    session, items = _load_session(session_id, session_token)
    if session.get("status") in ("submitted", "passed", "failed", "timeout"):
        raise ValueError("already_submitted")

    # Timeout check
    exp = _parse_dt(session.get("expiresAt"))
    if exp and _now() > exp:
        session["status"] = "timeout"
        try:
            _save_json(SESSIONS_FILE, items)
        except Exception:
            pass
        raise ValueError("timeout")

    if isinstance(answers, dict):
        session["answers"] = answers
        _persist_answers_pg(session_id, answers, session.get("questions") or [])
    try:
        _save_json(SESSIONS_FILE, items)
    except Exception as e:
        log.warning("autosave: %s", e)
    return {"ok": True, "savedAt": _utc_now(), "attemptId": session_id}


def _resolve_selection(ans: dict, q: dict, session_questions: list[dict], index: int):
    candidates = [
        str(q.get("id")) if q.get("id") is not None else None,
        str(index),
        index,
        str(q.get("originalIndex")) if q.get("originalIndex") is not None else None,
    ]
    for sq in session_questions:
        if sq.get("originalIndex") == index or str(sq.get("id")) == str(q.get("id")):
            if sq.get("id") is not None:
                candidates.append(str(sq.get("id")))
            if sq.get("originalIndex") is not None:
                candidates.append(str(sq.get("originalIndex")))
    for k in candidates:
        if k is None:
            continue
        if k in ans:
            return ans[k]
        if str(k) in ans:
            return ans[str(k)]
    return None


def submit_exam(
    session_id: str,
    session_token: str,
    answers: dict | None,
    fingerprint: str | None = None,
) -> dict:
    """Server-side scoring only. Client answers are selections, never scores."""
    session, items = _load_session(session_id, session_token)
    if session.get("status") in ("submitted", "passed", "failed", "timeout"):
        raise ValueError("already_submitted")

    timed_out = False
    exp = _parse_dt(session.get("expiresAt"))
    if exp and _now() > exp:
        timed_out = True

    oly = find_olympiad(session["olympiadId"]) or {}
    qs = oly.get("questions") or []
    ans = answers if isinstance(answers, dict) else {}
    # merge last autosaved
    merged = dict(session.get("answers") or {})
    merged.update(ans)
    ans = merged

    correct = 0
    total = len(qs)
    detail_rows = []
    for i, q in enumerate(qs):
        sel = _resolve_selection(ans, q, session.get("questions") or [], i)
        ok = False
        try:
            if sel is not None and int(sel) == int(q.get("answer", -1)):
                correct += 1
                ok = True
        except (TypeError, ValueError):
            pass
        detail_rows.append({
            "questionId": str(q.get("id") if q.get("id") is not None else i),
            "selected": int(sel) if sel is not None else None,
            "isCorrect": ok,
        })

    score = int(round(100 * correct / total)) if total else 0
    pass_score = int(oly.get("passScore") or session.get("passScore") or 70)
    if timed_out and score < pass_score:
        status = "timeout"
    else:
        status = "passed" if score >= pass_score else "failed"

    session["status"] = status if status != "timeout" else "timeout"
    session["answers"] = ans
    session["score"] = score
    session["correct"] = correct
    session["total"] = total
    session["finishedAt"] = _utc_now()
    try:
        _save_json(SESSIONS_FILE, items)
    except Exception as e:
        log.warning("session submit save: %s", e)

    _persist_answers_pg(session_id, ans, session.get("questions") or [])

    # Update is_correct flags + attempt row
    if is_postgres_enabled():
        try:
            with get_session() as s:
                for row in detail_rows:
                    try:
                        uuid.UUID(row["questionId"])
                    except Exception:
                        continue
                    if row["selected"] is None:
                        continue
                    s.execute(
                        text(
                            "INSERT INTO attempt_answers "
                            "(id, attempt_id, question_id, selected_idx, is_correct, saved_at) "
                            "VALUES (:id, :aid, :qid, :sel, :ok, NOW()) "
                            "ON CONFLICT (attempt_id, question_id) DO UPDATE SET "
                            "selected_idx = EXCLUDED.selected_idx, "
                            "is_correct = EXCLUDED.is_correct, saved_at = NOW()"
                        ),
                        {
                            "id": str(uuid.uuid4()),
                            "aid": session_id,
                            "qid": row["questionId"],
                            "sel": row["selected"],
                            "ok": row["isCorrect"],
                        },
                    )
                s.execute(
                    text(
                        "UPDATE attempts SET status = CAST(:st AS attempt_status), "
                        "score = :score, correct = :c, total = :t, pass_score = :ps, "
                        "finished_at = NOW() WHERE id::text = :id"
                    ),
                    {
                        "st": status if status in ("passed", "failed", "timeout", "submitted") else "failed",
                        "score": score,
                        "c": correct,
                        "t": total,
                        "ps": pass_score,
                        "id": session_id,
                    },
                )
        except Exception as e:
            log.error("attempts submit persist: %s", e)
            try:
                with get_session() as s:
                    s.execute(
                        text(
                            "UPDATE attempts SET status = :st, score = :score, correct = :c, "
                            "total = :t, pass_score = :ps, finished_at = NOW() "
                            "WHERE id::text = :id"
                        ),
                        {
                            "st": "passed" if status == "passed" else "failed",
                            "score": score,
                            "c": correct,
                            "t": total,
                            "ps": pass_score,
                            "id": session_id,
                        },
                    )
            except Exception as e2:
                log.error("attempts submit fallback: %s", e2)

    result = {
        "attemptId": session_id,
        "olympiadId": session.get("olympiadId"),
        "studentId": session.get("studentId"),
        "score": score,
        "correct": correct,
        "total": total,
        "passScore": pass_score,
        "status": status,
        "timedOut": timed_out,
        "finishedAt": session.get("finishedAt"),
    }
    return {
        "ok": True,
        "result": result,
        **result,  # flat for older client
    }
