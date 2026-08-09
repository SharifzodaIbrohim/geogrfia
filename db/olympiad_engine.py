"""
Phase 9–12 — Olympiad Engine
- duration countdown from attempt start
- one finished attempt per student per olympiad
- autosave answers
- server scoring (existing submit path enhanced)
- anti-cheat light: question shuffle, rate limit, session binding
"""
from __future__ import annotations

import hashlib
import secrets
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy import text

from db.connection import get_session
from db.repo import use_pg, find_olympiad, DATA_DIR, _load_json, _save_json, _utc_now
from db.student_access import student_has_olympiad_access

SESSIONS_FILE = DATA_DIR / "olympiad_sessions.json"

# in-memory rate limit: key -> list of timestamps
_RATE: dict[str, list[float]] = {}
RATE_WINDOW = 60.0
RATE_MAX = 30  # actions per minute per student+olympiad


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _rate_ok(key: str) -> bool:
    now = time.time()
    bucket = _RATE.setdefault(key, [])
    bucket[:] = [t for t in bucket if now - t < RATE_WINDOW]
    if len(bucket) >= RATE_MAX:
        return False
    bucket.append(now)
    return True


def _shuffle_indices(n: int, seed: str) -> list[int]:
    """Deterministic shuffle from session seed (same order on resume)."""
    idxs = list(range(n))
    # Fisher–Yates with seeded RNG from hash
    h = hashlib.sha256(seed.encode()).digest()
    state = int.from_bytes(h[:8], "big")

    def rnd() -> float:
        nonlocal state
        state = (1103515245 * state + 12345) & 0x7FFFFFFF
        return state / 0x7FFFFFFF

    for i in range(n - 1, 0, -1):
        j = int(rnd() * (i + 1))
        idxs[i], idxs[j] = idxs[j], idxs[i]
    return idxs


def _load_sessions() -> list:
    return _load_json(SESSIONS_FILE)


def _save_sessions(items: list) -> None:
    _save_json(SESSIONS_FILE, items)


def has_finished_attempt(olympiad_id: str, student_code: str) -> bool:
    if use_pg():
        with get_session() as s:
            # results may be in attempts table or legacy results via repo
            n = s.execute(
                text(
                    "SELECT COUNT(*) FROM attempts "
                    "WHERE kind = 'olympiad' AND olympiad_id::text = :oid "
                    "AND student_name IS NOT NULL "
                    "AND status IN ('passed','failed','submitted','disqualified') "
                    "AND ("
                    "  student_id IN (SELECT id FROM students WHERE student_code = :code) "
                    "  OR meta->>'studentCode' = :code"
                    ")"
                ),
                {"oid": olympiad_id, "code": student_code},
            ).scalar()
            # meta column may not exist — fallback simpler check below
            if n and int(n) > 0:
                return True
    # JSON results
    from db.repo import list_results

    for r in list_results(olympiad_id):
        if r.get("studentId") == student_code and r.get("status") in (
            "passed",
            "failed",
            "submitted",
            "disqualified",
        ):
            return True
    return False


def get_open_session(olympiad_id: str, student_code: str) -> dict | None:
    if use_pg():
        # sessions stored as in_progress attempts with session_token in student_name field abuse avoided — use JSON sidecar always for session state
        pass
    for s in _load_sessions():
        if (
            s.get("olympiadId") == olympiad_id
            and s.get("studentCode") == student_code
            and s.get("status") == "in_progress"
        ):
            return s
    return None


def start_exam(
    olympiad_id: str,
    student_code: str,
    *,
    user_id: str | None = None,
    client_fingerprint: str | None = None,
) -> dict:
    """
    Start or resume olympiad attempt.
    Access must already be validated by caller.
    """
    rate_key = f"start:{olympiad_id}:{student_code}"
    if not _rate_ok(rate_key):
        raise ValueError("rate_limited")

    olympiad = find_olympiad(olympiad_id)
    if not olympiad:
        raise ValueError("not_found")

    access = student_has_olympiad_access(olympiad_id, student_code)
    if not access.get("allowed"):
        raise ValueError(access.get("reason") or "not_allowed")

    if has_finished_attempt(olympiad_id, student_code):
        raise ValueError("already_submitted")

    existing = get_open_session(olympiad_id, student_code)
    if existing:
        # resume — same order, same token
        return _public_session(existing, olympiad, include_answers=False)

    questions = olympiad.get("questions") or []
    if not questions:
        raise ValueError("no_questions")

    seed = secrets.token_hex(16)
    order = _shuffle_indices(len(questions), seed)
    session_token = secrets.token_urlsafe(24)
    started = _now()

    # duration: prefer durationSec, else endTime - now, else None
    duration = olympiad.get("durationSec") or olympiad.get("duration_sec")
    ends_at = None
    if duration:
        ends_at = started + timedelta(seconds=int(duration))
    else:
        end_raw = olympiad.get("endTime")
        if end_raw:
            try:
                et = datetime.fromisoformat(str(end_raw).replace("Z", "+00:00"))
                if et.tzinfo is None:
                    et = et.replace(tzinfo=timezone.utc)
                ends_at = et
            except ValueError:
                pass

    student = access.get("student") or {}
    session = {
        "id": str(uuid.uuid4()),
        "sessionToken": session_token,
        "olympiadId": olympiad_id,
        "studentCode": student_code,
        "studentName": student.get("fullName"),
        "userId": user_id,
        "seed": seed,
        "order": order,
        "answers": {},  # str(orig_index) -> selected
        "status": "in_progress",
        "startedAt": started.isoformat(),
        "endsAt": ends_at.isoformat() if ends_at else None,
        "fingerprint": (client_fingerprint or "")[:64],
        "lastSaveAt": started.isoformat(),
    }
    items = _load_sessions()
    items.append(session)
    _save_sessions(items)

    return _public_session(session, olympiad, include_answers=False)


def _public_session(session: dict, olympiad: dict, include_answers: bool) -> dict:
    questions = olympiad.get("questions") or []
    order = session.get("order") or list(range(len(questions)))
    ordered = []
    for disp_i, orig_i in enumerate(order):
        if orig_i < 0 or orig_i >= len(questions):
            continue
        q = questions[orig_i]
        item = {
            "id": q.get("id", orig_i + 1),
            "displayIndex": disp_i,
            "originalIndex": orig_i,
            "text": q.get("text"),
            "options": list(q.get("options") or []),
        }
        # shuffle options lightly with seed+index
        opt_order = _shuffle_indices(len(item["options"]), session["seed"] + f":opt:{orig_i}")
        item["options"] = [item["options"][j] for j in opt_order]
        item["optionOrder"] = opt_order
        if include_answers:
            item["answer"] = q.get("answer")
        # restore saved selection mapped to shuffled options
        saved = session.get("answers", {}).get(str(orig_i))
        if saved is not None and "optionOrder" in item:
            # saved is original option index; map to display index
            try:
                item["selected"] = item["optionOrder"].index(int(saved))
            except (ValueError, TypeError):
                item["selected"] = None
        else:
            item["selected"] = None
        ordered.append(item)

    return {
        "sessionId": session["id"],
        "sessionToken": session["sessionToken"],
        "olympiadId": session["olympiadId"],
        "title": olympiad.get("title"),
        "passScore": olympiad.get("passScore") or 70,
        "startedAt": session.get("startedAt"),
        "endsAt": session.get("endsAt"),
        "status": session.get("status"),
        "questionCount": len(ordered),
        "questions": ordered,
        "savedCount": len(session.get("answers") or {}),
    }


def _find_session(session_id: str, session_token: str) -> dict | None:
    for s in _load_sessions():
        if s.get("id") == session_id and secrets.compare_digest(
            str(s.get("sessionToken") or ""), str(session_token or "")
        ):
            return s
    return None


def autosave(
    session_id: str,
    session_token: str,
    answers: dict,
    *,
    fingerprint: str | None = None,
) -> dict:
    """answers: { originalIndex or questionId: selectedDisplayIndex } — we store original option idx."""
    rate_key = f"save:{session_id}"
    if not _rate_ok(rate_key):
        raise ValueError("rate_limited")

    items = _load_sessions()
    session = None
    for s in items:
        if s.get("id") == session_id:
            session = s
            break
    if not session or not secrets.compare_digest(
        str(session.get("sessionToken") or ""), str(session_token or "")
    ):
        raise ValueError("invalid_session")
    if session.get("status") != "in_progress":
        raise ValueError("not_in_progress")

    # optional binding check (soft — warn only if both set and mismatch)
    if fingerprint and session.get("fingerprint") and session["fingerprint"] != fingerprint[:64]:
        # still allow save but mark
        session["fingerprintMismatch"] = True

    olympiad = find_olympiad(session["olympiadId"])
    if not olympiad:
        raise ValueError("not_found")

    questions = olympiad.get("questions") or []
    order = session.get("order") or []
    saved = dict(session.get("answers") or {})

    for key, disp_sel in (answers or {}).items():
        try:
            # key may be originalIndex
            orig_i = int(key)
        except (TypeError, ValueError):
            continue
        if orig_i < 0 or orig_i >= len(questions):
            continue
        opt_order = _shuffle_indices(
            len(questions[orig_i].get("options") or []),
            session["seed"] + f":opt:{orig_i}",
        )
        try:
            disp_sel_i = int(disp_sel)
            orig_opt = opt_order[disp_sel_i]
        except (TypeError, ValueError, IndexError):
            continue
        saved[str(orig_i)] = orig_opt

    session["answers"] = saved
    session["lastSaveAt"] = _utc_now()
    _save_sessions(items)
    return {"ok": True, "savedCount": len(saved), "lastSaveAt": session["lastSaveAt"]}


def submit_exam(
    session_id: str,
    session_token: str,
    answers: dict | None = None,
    *,
    fingerprint: str | None = None,
) -> dict:
    rate_key = f"submit:{session_id}"
    if not _rate_ok(rate_key):
        raise ValueError("rate_limited")

    items = _load_sessions()
    session = None
    idx = None
    for i, s in enumerate(items):
        if s.get("id") == session_id:
            session = s
            idx = i
            break
    if not session or not secrets.compare_digest(
        str(session.get("sessionToken") or ""), str(session_token or "")
    ):
        raise ValueError("invalid_session")
    if session.get("status") != "in_progress":
        raise ValueError("already_submitted")

    if has_finished_attempt(session["olympiadId"], session["studentCode"]):
        raise ValueError("already_submitted")

    # merge final answers
    if answers:
        autosave(session_id, session_token, answers, fingerprint=fingerprint)
        items = _load_sessions()
        session = items[idx]

    olympiad = find_olympiad(session["olympiadId"])
    if not olympiad:
        raise ValueError("not_found")

    timed_out = False
    ends = session.get("endsAt")
    if ends:
        try:
            et = datetime.fromisoformat(str(ends).replace("Z", "+00:00"))
            if et.tzinfo is None:
                et = et.replace(tzinfo=timezone.utc)
            if _now() > et + timedelta(seconds=20):
                timed_out = True
        except ValueError:
            pass

    questions = olympiad.get("questions") or []
    saved = session.get("answers") or {}
    correct = 0
    detail = []
    for i, q in enumerate(questions):
        right = int(q.get("answer") or 0)
        sel = saved.get(str(i))
        try:
            sel_i = int(sel) if sel is not None else None
        except (TypeError, ValueError):
            sel_i = None
        ok = sel_i is not None and sel_i == right
        if ok:
            correct += 1
        detail.append({"questionId": q.get("id", i + 1), "selected": sel_i, "correct": ok})

    total = len(questions) or 1
    score = round((correct / total) * 100) if questions else 0
    pass_score = int(olympiad.get("passScore") or 70)
    status = "passed" if score >= pass_score else "failed"
    finished = _utc_now()

    student = session
    result = {
        "id": str(uuid.uuid4()),
        "studentId": session["studentCode"],
        "studentName": session.get("studentName"),
        "studentClass": None,
        "studentSchool": None,
        "olympiadId": session["olympiadId"],
        "olympiadTitle": olympiad.get("title"),
        "score": score,
        "correct": correct,
        "total": len(questions),
        "passScore": pass_score,
        "status": status,
        "answers": detail,
        "timedOut": timed_out,
        "sessionId": session_id,
        "finishedAt": finished,
    }
    # enrich class/school from student record
    from db.repo import find_student_by_code, save_result

    st = find_student_by_code(session["studentCode"])
    if st:
        result["studentName"] = st.get("fullName") or result["studentName"]
        result["studentClass"] = st.get("className")
        result["studentSchool"] = st.get("school")

    save_result(result)

    session["status"] = "submitted"
    session["finishedAt"] = finished
    session["score"] = score
    items[idx] = session
    _save_sessions(items)

    return {
        "score": score,
        "correct": correct,
        "total": len(questions),
        "passScore": pass_score,
        "status": status,
        "timedOut": timed_out,
        "finishedAt": finished,
    }
