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


def _norm_code(student_code) -> str:
    if isinstance(student_code, dict):
        student_code = (
            student_code.get("id")
            or student_code.get("studentId")
            or student_code.get("student_code")
            or ""
        )
    return str(student_code or "").strip()


def _student_uuid(student_code: str):
    student_code = _norm_code(student_code)
    if not student_code or not is_postgres_enabled():
        return None
    try:
        with get_session() as s:
            return s.execute(
                text("SELECT id FROM students WHERE student_code = :c AND status = 'active'"),
                {"c": student_code},
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


def _sanitize_options(options) -> list:
    out = []
    for o in options or []:
        if isinstance(o, dict):
            out.append(str(o.get("text") or o.get("label") or ""))
        else:
            out.append(str(o))
    return out


def _public_questions(qs_src: list) -> list:
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
    student_code = _norm_code(student_code)
    if not olympiad_id or not student_code:
        return False
    if is_postgres_enabled():
        try:
            su = _student_uuid(student_code)
            with get_session() as s:
                if su:
                    row = s.execute(
                        text(
                            "SELECT 1 FROM attempts WHERE olympiad_id = :o AND student_id = :s "
                            "AND status IN ('passed','failed','timeout','submitted') LIMIT 1"
                        ),
                        {"o": olympiad_id, "s": str(su)},
                    ).first()
                else:
                    row = None
                if row:
                    return True
        except Exception as e:
            log.warning("has_finished_attempt pg: %s", e)
    try:
        sessions = _load_json(SESSIONS_FILE, {})
        for sid, sess in (sessions or {}).items():
            if isinstance(sess, dict) and str(sess.get("olympiadId")) == str(olympiad_id) and str(sess.get("studentId")) == str(student_code):
                if sess.get("status") in ("passed", "failed", "timeout", "submitted", "finished"):
                    return True
    except Exception:
        pass
    return False


def find_open_attempt(olympiad_id: str, student_code: str):
    student_code = _norm_code(student_code)
    if is_postgres_enabled():
        try:
            su = _student_uuid(student_code)
            with get_session() as s:
                if su:
                    row = s.execute(
                        text(
                            "SELECT id::text, session_token, expires_at, status FROM attempts "
                            "WHERE olympiad_id = :o AND student_id = :s AND status = 'in_progress' "
                            "ORDER BY started_at DESC LIMIT 1"
                        ),
                        {"o": olympiad_id, "s": str(su)},
                    ).mappings().first()
                else:
                    row = None
                if row:
                    return dict(row)
        except Exception as e:
            log.warning("find_open_attempt: %s", e)
    try:
        sessions = _load_json(SESSIONS_FILE, {})
        for sid, sess in (sessions or {}).items():
            if isinstance(sess, dict) and str(sess.get("olympiadId")) == str(olympiad_id) and str(sess.get("studentId")) == str(student_code):
                if sess.get("status") in (None, "in_progress", "started"):
                    return {"id": sid, **sess}
    except Exception:
        pass
    return None


def _remaining_sec(expires_at) -> int | None:
    exp = _parse_dt(expires_at)
    if not exp:
        return None
    return max(0, int((exp - _now()).total_seconds()))


def _client_session_payload(session: dict, questions: list) -> dict:
    return {
        "ok": True,
        "sessionId": session.get("id") or session.get("sessionId"),
        "sessionToken": session.get("sessionToken") or session.get("session_token"),
        "olympiadId": session.get("olympiadId"),
        "title": session.get("title"),
        "passScore": session.get("passScore"),
        "questions": questions,
        "expiresAt": session.get("expiresAt") or session.get("expires_at"),
        "remainingSec": _remaining_sec(session.get("expiresAt") or session.get("expires_at")),
        "serverNow": _utc_now(),
    }


def start_exam(olympiad_id: str, student_code: str, fingerprint: str | None = None, **kwargs):
    student_code = _norm_code(student_code)
    if not student_code:
        raise ValueError("student_id_required")
    oly = find_olympiad(olympiad_id)
    if not oly:
        raise ValueError("not_found")
    access = student_has_olympiad_access(olympiad_id, student_code)
    if isinstance(access, dict):
        if not access.get("allowed", False):
            raise ValueError(access.get("reason") or "not_assigned")
    elif not access:
        raise ValueError("not_assigned")
    win = _window_ok(oly)
    if win != "open":
        raise ValueError(win if win in ("not_started", "ended") else "not_assigned")
    if has_finished_attempt(olympiad_id, student_code):
        raise ValueError("already_submitted")
    qs_src = oly.get("questions") or []
    if not qs_src:
        raise ValueError("no_questions")
    open_att = find_open_attempt(olympiad_id, student_code)
    if open_att:
        questions = _public_questions(qs_src)
        sess = {
            "id": open_att.get("id"),
            "sessionToken": open_att.get("session_token") or open_att.get("sessionToken"),
            "olympiadId": olympiad_id,
            "title": oly.get("title"),
            "passScore": oly.get("passScore") or 70,
            "expiresAt": str(open_att.get("expires_at") or open_att.get("expiresAt") or ""),
        }
        return _client_session_payload(sess, questions)
    started = _now()
    expires = _compute_expires(oly, started)
    session_id = str(uuid.uuid4())
    token = secrets.token_urlsafe(24)
    questions = _public_questions(qs_src)
    su = _student_uuid(student_code)
    user_id = kwargs.get("user_id")
    # Always JSON session so exam works even if PG schema differs
    sessions = _load_json(SESSIONS_FILE, {})
    if not isinstance(sessions, dict):
        sessions = {}
    sessions[session_id] = {
        "id": session_id,
        "sessionId": session_id,
        "olympiadId": olympiad_id,
        "studentId": student_code,
        "sessionToken": token,
        "status": "in_progress",
        "startedAt": started.isoformat(),
        "expiresAt": expires.isoformat() if expires else None,
        "title": oly.get("title"),
        "passScore": oly.get("passScore") or 70,
        "questions": questions,
    }
    try:
        _save_json(SESSIONS_FILE, sessions)
    except Exception as e:
        log.warning("session json save: %s", e)

    if is_postgres_enabled():
        try:
            with get_session() as s:
                try:
                    s.execute(
                        text(
                            "INSERT INTO attempts "
                            "(id, kind, olympiad_id, student_id, user_id, student_name, "
                            " status, pass_score, total, started_at, expires_at, session_token) "
                            "VALUES (:id, 'olympiad', :oid, :sid, :uid, :name, "
                            " 'in_progress', :ps, :total, :st, :ex, :tok)"
                        ),
                        {
                            "id": session_id, "oid": olympiad_id, "sid": su, "uid": user_id,
                            "name": student_code, "ps": oly.get("passScore") or 70,
                            "total": len(questions), "st": started, "ex": expires, "tok": token,
                        },
                    )
                except Exception as e1:
                    log.warning("attempt insert full: %s", e1)
                    try:
                        s.execute(
                            text(
                                "INSERT INTO attempts "
                                "(id, kind, olympiad_id, student_id, status, started_at) "
                                "VALUES (:id, 'olympiad', :oid, :sid, 'in_progress', NOW())"
                            ),
                            {"id": session_id, "oid": olympiad_id, "sid": su},
                        )
                    except Exception as e2:
                        log.warning("attempt insert minimal: %s", e2)
        except Exception as e:
            log.warning("attempt start persist: %s", e)

    sess = {
        "id": session_id,
        "sessionToken": token,
        "olympiadId": olympiad_id,
        "title": oly.get("title"),
        "passScore": oly.get("passScore") or 70,
        "expiresAt": expires.isoformat() if expires else None,
    }
    return _client_session_payload(sess, questions)


def _load_session(session_id: str):
    # Prefer JSON
    try:
        sessions = _load_json(SESSIONS_FILE, {})
        if isinstance(sessions, dict) and session_id in sessions:
            return sessions[session_id]
        if isinstance(sessions, list):
            for s in sessions:
                if isinstance(s, dict) and (s.get("id") == session_id or s.get("sessionId") == session_id):
                    return s
    except Exception:
        pass
    if is_postgres_enabled():
        try:
            with get_session() as s:
                row = s.execute(
                    text(
                        "SELECT id::text, olympiad_id, student_id, status, session_token, expires_at, started_at "
                        "FROM attempts WHERE id::text = :id"
                    ),
                    {"id": session_id},
                ).mappings().first()
                if row:
                    return {
                        "id": row["id"],
                        "olympiadId": row["olympiad_id"],
                        "studentId": str(row.get("student_id") or ""),
                        "status": row["status"],
                        "sessionToken": row.get("session_token"),
                        "expiresAt": str(row["expires_at"]) if row.get("expires_at") else None,
                    }
        except Exception as e:
            log.warning("_load_session pg: %s", e)
    return None


def autosave(session_id: str, session_token=None, answers=None, fingerprint=None, **kwargs):
    if answers is None and isinstance(session_token, dict):
        answers = session_token
        session_token = kwargs.get("session_token") or kwargs.get("sessionToken")
    session = _load_session(session_id)
    if not session:
        raise ValueError("session not found")
    tok = session.get("sessionToken") or session.get("session_token")
    if session_token and tok and str(session_token) != str(tok):
        raise ValueError("invalid token")
    rem = _remaining_sec(session.get("expiresAt"))
    return {"ok": True, "remainingSec": rem, "expiresAt": session.get("expiresAt"), "serverNow": _utc_now()}


def _resolve_selection(q, selected):
    if selected is None:
        return None, False
    opts = q.get("options") or []
    correct = None
    for i, o in enumerate(opts):
        if isinstance(o, dict) and (o.get("is_correct") or o.get("isCorrect") or o.get("correct")):
            correct = i
            break
    if correct is None:
        correct = q.get("correctIndex")
        if correct is None:
            correct = q.get("correct_index")
        if correct is None and isinstance(q.get("answer"), int):
            correct = q.get("answer")
    try:
        sel = int(selected)
    except (TypeError, ValueError):
        sel = selected
    is_ok = correct is not None and sel == correct
    return sel, bool(is_ok)


def submit_exam(session_id: str, answers=None, session_token: str | None = None, **kwargs):
    if session_token is None:
        session_token = kwargs.get("sessionToken")
    session = _load_session(session_id)
    if not session:
        raise ValueError("session not found")
    if session.get("status") in ("passed", "failed", "timeout", "submitted", "finished"):
        raise ValueError("already_submitted")
    tok = session.get("sessionToken") or session.get("session_token")
    if session_token and tok and str(session_token) != str(tok):
        raise ValueError("invalid token")
    oly = find_olympiad(session.get("olympiadId"))
    qs_src = (oly or {}).get("questions") or []
    answers = answers or {}
    correct = 0
    total = len(qs_src)
    timed_out = False
    rem = _remaining_sec(session.get("expiresAt"))
    if rem is not None and rem <= 0:
        timed_out = True
    for i, q in enumerate(qs_src):
        qid = str(q.get("id") if q.get("id") is not None else i)
        sel = answers.get(qid)
        if sel is None:
            sel = answers.get(str(i))
        _, ok = _resolve_selection(q, sel)
        if ok:
            correct += 1
    score = int(round((correct / total) * 100)) if total else 0
    pass_score = int((oly or {}).get("passScore") or 70)
    status = "timeout" if timed_out else ("passed" if score >= pass_score else "failed")
    session["status"] = status
    session["score"] = score
    session["correct"] = correct
    session["total"] = total
    session["finishedAt"] = _utc_now()
    try:
        sessions = _load_json(SESSIONS_FILE, {})
        if isinstance(sessions, dict) and session_id in sessions:
            sessions[session_id].update(session)
            _save_json(SESSIONS_FILE, sessions)
    except Exception:
        pass
    if is_postgres_enabled():
        try:
            with get_session() as s:
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
            log.error("submit persist: %s", e)
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
