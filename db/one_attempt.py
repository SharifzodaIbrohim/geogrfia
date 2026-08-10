"""Hard one-attempt policy for quizzes and olympiads."""
from __future__ import annotations

import json
from pathlib import Path


def identity_keys(student_code: str | None = None, user_id: str | None = None) -> set[str]:
    keys: set[str] = set()
    if student_code:
        sc = str(student_code).strip()
        keys.add(sc)
        if ":" in sc:
            tail = sc.split(":", 1)[-1]
            keys.add(tail)
            keys.add("g:" + tail)
            keys.add("gmail:" + tail)
    if user_id:
        uid = str(user_id).strip()
        keys.add(uid)
        keys.add("g:" + uid)
        keys.add("gmail:" + uid)
        keys.add("g:" + uid[:40])
    return {k for k in keys if k}


def _data_dirs() -> list[Path]:
    out = []
    for p in [
        Path.cwd() / "data",
        Path("/opt/render/project/src/data"),
        Path(__file__).resolve().parent.parent / "data",
    ]:
        out.append(p)
    return out


def has_finished_olympiad(olympiad_id: str, student_code: str, user_id: str | None = None) -> bool:
    keys = identity_keys(student_code, user_id)
    done = {"passed", "failed", "submitted", "disqualified", "timed_out"}
    oid = str(olympiad_id)

    try:
        from db.repo import list_results
        for r in list_results(olympiad_id) or []:
            rid = str(r.get("studentId") or r.get("studentCode") or "")
            ruid = str(r.get("userId") or "")
            st = str(r.get("status") or "").lower()
            if rid in keys or ruid in keys:
                if st in done or r.get("score") is not None:
                    return True
    except Exception:
        pass

    for base in _data_dirs():
        for name, is_session in (("results.json", False), ("olympiad_sessions.json", True)):
            path = base / name
            if not path.exists():
                continue
            try:
                rows = json.loads(path.read_text(encoding="utf-8")) or []
            except Exception:
                continue
            if not isinstance(rows, list):
                continue
            for r in rows:
                if str(r.get("olympiadId") or "") != oid:
                    continue
                rid = str(r.get("studentId") or r.get("studentCode") or "")
                ruid = str(r.get("userId") or "")
                if rid not in keys and ruid not in keys:
                    continue
                st = str(r.get("status") or "").lower()
                if is_session:
                    if st in done or st == "submitted":
                        return True
                else:
                    return True
    return False


def has_finished_quiz(quiz_id: str, user_id: str | None = None, student_id: str | None = None) -> bool:
    keys = identity_keys(student_id, user_id)
    qid = str(quiz_id)
    if user_id:
        try:
            from db.connection import get_session
            from sqlalchemy import text
            with get_session() as s:
                row = s.execute(
                    text(
                        "SELECT id FROM attempts WHERE kind='quiz' AND quiz_id::text=:qid "
                        "AND user_id::text=:uid AND status IN ('passed','failed','submitted') LIMIT 1"
                    ),
                    {"qid": qid, "uid": str(user_id)},
                ).first()
                if row:
                    return True
        except Exception:
            pass
    for base in _data_dirs():
        path = base / "quiz_attempts.json"
        if not path.exists():
            continue
        try:
            rows = json.loads(path.read_text(encoding="utf-8")) or []
        except Exception:
            continue
        for a in rows or []:
            if str(a.get("quizId")) != qid:
                continue
            st = str(a.get("status") or "").lower()
            if st not in ("passed", "failed", "submitted"):
                continue
            uid = str(a.get("userId") or "")
            sid = str(a.get("studentCode") or a.get("studentId") or "")
            if (user_id and uid == str(user_id)) or sid in keys or uid in keys:
                return True
    return False


def install():
    """Monkey-patch engines so start always enforces one attempt."""
    try:
        from db import olympiad_engine as oe
        _orig = oe.start_exam

        def start_exam(olympiad_id, student_code, *, user_id=None, client_fingerprint=None):
            if has_finished_olympiad(olympiad_id, student_code, user_id=user_id):
                raise ValueError("already_submitted")
            return _orig(
                olympiad_id,
                student_code,
                user_id=user_id,
                client_fingerprint=client_fingerprint,
            )

        oe.start_exam = start_exam
    except Exception:
        pass

    try:
        from db import quiz_api as qa
        _orig_q = qa.start_attempt

        def start_attempt(quiz_id, user_id=None, student_id=None):
            if has_finished_quiz(quiz_id, user_id=user_id, student_id=student_id):
                raise ValueError("already_submitted")
            return _orig_q(quiz_id, user_id=user_id, student_id=student_id)

        qa.start_attempt = start_attempt
    except Exception:
        pass
