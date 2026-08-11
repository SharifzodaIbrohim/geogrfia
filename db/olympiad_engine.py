"""P1 Olympiad Engine — P1.10 no answers to client, P1.11 server timer, P1.12 one attempt."""
from __future__ import annotations

import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from db.connection import get_session, is_postgres_enabled
from db.repo import DATA_DIR, _load_json, _save_json, find_olympiad
from db.student_access import student_has_olympiad_access

log = logging.getLogger("geografia.olympiad_engine")
SESSIONS_FILE = DATA_DIR / "exam_sessions.json"

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
    except Exception:
        return None


def _student_uuid(student_code: str):
    if not student_code or not is_postgres_enabled():
        return None
    try:
        with get_session() as s:
            return s.execute(
                text("SELECT id FROM students WHERE student_code = :c AND status = 'active'"),
                {"c": str(student_code).strip()},
            ).scalar()
    except Exception as e:
        log.warning("student uuid lookup: %s", e)
        return None


def _window_ok(oly: dict) -> str:
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


def _compute_expires(oly: dict, started: datetime):
    candidates = []
    try:
        dur = oly.get("durationSec")
        if dur is not None and int(dur) > 0:
            candidates.append(started + timedelta(seconds=int(dur)))
    except (TypeError, ValueError):
        pass
    end = _parse_dt(oly.get("endTime") or oly.get("end_at"))
    if end:
        candidates.append(end)
    return min(candidates) if candidates else None


def _sanitize_options(options) -> list[str]:
    """P1.10: options are plain text only — never is_correct."""
    out = []
    for o in options or []:
        if isinstance(o, dict):
            out.append(str(o.get("text") or o.get("label") or ""))
        else:
            out.append(str(o))
    return out


def _public_questions(qs_src: list) -> list:
    """Client-safe questions: id, text, options only (+ originalIndex for submit mapping)."""
    order = list(range(len(qs_src)))
    secrets.SystemRandom().shuffle(order)
    out = []
    for orig_i in order:
        q = qs_src[orig_i] or {}
        qid = q.get("id")
        if qid is None:
            qid = str(orig_i)
        item = {
            "id": str(qid),
            "text": q.get("text"),
            "options": _sanitize_options(q.get("options")),
            "originalIndex": orig_i,
        }
        for bad in _FORBIDDEN_Q_KEYS:
            item.pop(bad, None)
        out.append(item)
    return out


def has_finished_attempt(olympiad_id: str, student_code: str, user_id: str | None = None) -> bool:
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
                            "AND status IN ('submitted','passed','failed','timeout') LIMIT 1"
                        ),
                        {"oid": str(olympiad_id), "sid": sid},
                    ).first()
                    if row:
                        return True
        except Exception as e:
            log.warning("has_finished_attempt: %s", e)
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


def find_open_attempt(olympiad_id: str, student_code: str) -> dict | None:
    """Return in_progress session if still within expires_at."""
    code = str(student_code).strip()
    now = _now()
    try:
        for s in _load_json(SESSIONS_FILE):
            if str(s.get("olympiadId")) != str(olympiad_id):
                continue
            if str(s.get("studentId") or "") != code:
                continue
            if s.get("status") != "in_progress":
                continue
            exp = _parse_dt(s.get("expiresAt"))
            if exp and now > exp:
                continue
            return s
    except Exception:
        pass
    if is_postgres_enabled():
        try:
            sid = _student_uuid(student_code)
            if not sid:
                return None
            with get_session() as s:
                row = s.execute(
                    text(
                        "SELECT id::text, session_token, started_at, expires_at, pass_score "
                        "FROM attempts WHERE kind = 'olympiad' "
                        "AND olympiad_id::text = :oid AND student_id = :sid "
                        "AND status = 'in_progress' "
                        "AND (expires_at IS NULL OR expires_at > NOW()) "
                        "ORDER BY started_at DESC LIMIT 1"
                    ),
                    {"oid": str(olympiad_id), "sid": sid},
                ).mappings().first()
                if row:
                    return {
                        "sessionId": row["id"],
                        "attemptId": row["id"],
                        "sessionToken": row.get("session_token") or "",
                        "olympiadId": olympiad_id,
                        "studentId": code,
                        "status": "in_progress",
                        "startedAt": row["started_at"].isoformat() if row.get("started_at") else None,
                        "expiresAt": row["expires_at"].isoformat() if row.get("expires_at") else None,
                        "passScore": row.get("pass_score") or 70,
                        "questions": [],
                        "answers": {},
                        "_from_pg": True,
                    }
        except Exception as e:
            log.warning("find_open_attempt: %s", e)
    return None


def _remaining_sec(expires_at) -> int | None:
    exp = _parse_dt(expires_at)
    if not exp:
        return None
    return max(0, int((exp - _now()).total_seconds()))


def _client_session_payload(session: dict, oly: dict | None = None) -> dict:
    qs = session.get("questions") or []
    # Re-sanitize every time
    safe_qs = []
    for q in qs:
        safe_qs.append({
            "id": str(q.get("id")),
            "text": q.get("text"),
            "options": _sanitize_options(q.get("options")),
            "originalIndex": q.get("originalIndex"),
        })
    remaining = _remaining_sec(session.get("expiresAt"))
    return {
        "sessionId": session.get("sessionId") or session.get("attemptId"),
        "attemptId": session.get("attemptId") or session.get("sessionId"),
        "sessionToken": session.get("sessionToken"),
        "olympiadId": session.get("olympiadId"),
        "title": (oly or {}).get("title") if oly else session.get("title"),
        "passScore": session.get("passScore") or 70,
        "durationSec": (oly or {}).get("durationSec"),
        "startedAt": session.get("startedAt"),
        "expiresAt": session.get("expiresAt"),
        "endsAt": session.get("expiresAt"),
        "serverNow": _utc_now(),
        "remainingSec": remaining,
        "questions": safe_qs,
        "status": "in_progress",
        "resumed": bool(session.get("_resumed")),
    }


def start_exam(
    olympiad_id: str,
    student_code: str,
    user_id: str | None = None,
    fingerprint: str | None = None,
    client_fingerprint: str | None = None,
    **_kwargs,
) -> dict:
    fingerprint = fingerprint or client_fingerprint
    oly = find_olympiad(olympiad_id)
    if not oly:
        raise ValueError("not_found")
    window = _window_ok(oly)
    if window != "open":
        raise ValueError(window)
    access = student_has_olympiad_access(olympiad_id, student_code)
    if not access.get("allowed"):
        raise ValueError(access.get("reason") or "student_not_found")

    # P1.12: finished → reject; in_progress → resume same attempt
    if has_finished_attempt(olympiad_id, student_code, user_id):
        raise ValueError("already_submitted")

    open_sess = find_open_attempt(olympiad_id, student_code)
    if open_sess and open_sess.get("sessionToken"):
        open_sess["_resumed"] = True
        # Prefer JSON session questions if present
        if not open_sess.get("questions"):
            # cannot resume questions from PG-only without session file — reject new start? keep resume with empty and force client error
            pass
        return _client_session_payload(open_sess, oly)

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
                try:
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
                            "id": attempt_id, "oid": olympiad_id, "sid": sid, "uid": user_id,
                            "name": student.get("fullName") or student_code,
                            "cls": student.get("className") or "", "sch": student.get("school") or "",
                            "ps": pass_score, "total": len(questions), "st": started,
                            "ex": expires, "tok": session_token,
                        },
                    )
                except Exception:
                    s.execute(
                        text(
                            "INSERT INTO attempts "
                            "(id, kind, olympiad_id, student_id, user_id, student_name, "
                            " student_class, student_school, status, pass_score, total) "
                            "VALUES (:id, 'olympiad', :oid, :sid, :uid, :name, "
                            " :cls, :sch, 'in_progress', :ps, :total)"
                        ),
                        {
                            "id": attempt_id, "oid": olympiad_id, "sid": sid, "uid": user_id,
                            "name": student.get("fullName") or student_code,
                            "cls": student.get("className") or "", "sch": student.get("school") or "",
                            "ps": pass_score, "total": len(questions),
                        },
                    )
        except Exception as e:
            log.warning("attempt start persist: %s", e)

    return _client_session_payload(session, oly)


def _load_session(session_id: str, session_token: str):
    items = _load_json(SESSIONS_FILE)
    for s in items:
        if s.get("sessionId") == session_id and s.get("sessionToken") == session_token:
            return s, items
    raise ValueError("session_not_found")


def _persist_answers_pg(attempt_id: str, answers: dict, questions: list) -> None:
    if not is_postgres_enabled() or not answers:
        return
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
                    {"id": str(uuid.uuid4()), "aid": attempt_id, "qid": qid, "sel": sel_i},
                )
    except Exception as e:
        log.warning("persist answers: %s", e)


def autosave(session_id: str, session_token: str, answers: dict | None, fingerprint: str | None = None, **_kwargs) -> dict:
    session, items = _load_session(session_id, session_token)
    if session.get("status") in ("submitted", "passed", "failed", "timeout"):
        raise ValueError("already_submitted")
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
    return {
        "ok": True,
        "savedAt": _utc_now(),
        "attemptId": session_id,
        "serverNow": _utc_now(),
        "remainingSec": _remaining_sec(session.get("expiresAt")),
        "expiresAt": session.get("expiresAt"),
    }


def _resolve_selection(ans: dict, q: dict, session_questions: list, index: int):
    candidates = [
        str(q.get("id")) if q.get("id") is not None else None,
        str(index), index,
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


def submit_exam(session_id: str, session_token: str, answers: dict | None, fingerprint: str | None = None, **_kwargs) -> dict:
    """Server scores; expires_at is authoritative (P1.11)."""
    session, items = _load_session(session_id, session_token)
    if session.get("status") in ("submitted", "passed", "failed", "timeout"):
        raise ValueError("already_submitted")

    timed_out = False
    exp = _parse_dt(session.get("expiresAt"))
    if exp and _now() > exp:
        timed_out = True

    oly = find_olympiad(session["olympiadId"]) or {}
    qs = oly.get("questions") or []  # full questions WITH answers — server only
    ans = dict(session.get("answers") or {})
    if isinstance(answers, dict):
        ans.update(answers)

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
    if timed_out:
        status = "timeout" if score < pass_score else "passed"
    else:
        status = "passed" if score >= pass_score else "failed"

    session["status"] = status
    session["answers"] = ans
    session["score"] = score
    session["correct"] = correct
    session["total"] = total
    session["finishedAt"] = _utc_now()
    try:
        _save_json(SESSIONS_FILE, items)
    except Exception as e:
        log.warning("submit save: %s", e)

    _persist_answers_pg(session_id, ans, session.get("questions") or [])

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
                            "id": str(uuid.uuid4()), "aid": session_id,
                            "qid": row["questionId"], "sel": row["selected"], "ok": row["isCorrect"],
                        },
                    )
                st = status if status in ("passed", "failed", "timeout", "submitted") else "failed"
                try:
                    s.execute(
                        text(
                            "UPDATE attempts SET status = CAST(:st AS attempt_status), "
                            "score = :score, correct = :c, total = :t, pass_score = :ps, "
                            "finished_at = NOW() WHERE id::text = :id"
                        ),
                        {"st": st, "score": score, "c": correct, "t": total, "ps": pass_score, "id": session_id},
                    )
                except Exception:
                    s.execute(
                        text(
                            "UPDATE attempts SET status = :st, score = :score, correct = :c, "
                            "total = :t, pass_score = :ps, finished_at = NOW() WHERE id::text = :id"
                        ),
                        {
                            "st": "passed" if status == "passed" else "failed",
                            "score": score, "c": correct, "t": total, "ps": pass_score, "id": session_id,
                        },
                    )
        except Exception as e:
            log.error("attempts submit persist: %s", e)

    # P1.10: result has scores only — never per-question correct keys to client
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
        "serverNow": _utc_now(),
    }
    return {"ok": True, "result": result, **result}
