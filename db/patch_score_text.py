"""Boot patch: grade olympiad by option TEXT against source answers.
Works even when scoreMap/session file is lost on Render.
"""
from __future__ import annotations
import logging

log = logging.getLogger("geografia.patch_score_text")


def install(app=None):
    try:
        from db import olympiad_engine as oe
    except Exception as e:
        log.warning("patch_score_text import: %s", e)
        return

    def _nt(v):
        return " ".join(str(v or "").strip().split()).lower()

    def _student_code_from_session(session):
        code = str((session or {}).get("studentId") or (session or {}).get("student_code") or "").strip()
        if code.isdigit() and len(code) >= 10:
            return code
        try:
            from sqlalchemy import text
            if oe.is_postgres_enabled() and code:
                with oe.get_session() as s:
                    row = s.execute(
                        text(
                            "SELECT student_code FROM students "
                            "WHERE id::text = :c OR student_code = :c LIMIT 1"
                        ),
                        {"c": code},
                    ).fetchone()
                    if row and row[0]:
                        return str(row[0]).strip()
        except Exception as e:
            log.warning("resolve student_code: %s", e)
        return code

    def _src_correct_text(q):
        if not isinstance(q, dict):
            return None
        opts = q.get("options") or []
        opts = [str(o.get("text") if isinstance(o, dict) else o) for o in opts]
        for k in ("correctIndex", "correct_index", "answerIndex", "answer"):
            v = q.get(k)
            if v is None:
                continue
            try:
                i = int(v)
                if 0 <= i < len(opts):
                    return opts[i]
            except Exception:
                s = str(v).strip()
                if s and not s.isdigit():
                    return s
        for k in ("correctText", "answerText", "correct"):
            if q.get(k) is not None and str(q.get(k)).strip() != "":
                return str(q.get(k))
        return None

    def _grade_answers(session, answers, oly):
        qs_src = (oly or {}).get("questions") or []
        if not qs_src:
            return 0, 0

        answers = answers or {}
        if not isinstance(answers, dict):
            answers = {}
        answers = {str(k): v for k, v in answers.items()}

        pub_qs = list(session.get("questions") or [])
        if not pub_qs:
            try:
                code = _student_code_from_session(session)
                oid = session.get("olympiadId")
                pub_qs, _smap = oe._build_pack(qs_src, code, oid)
            except Exception as e:
                log.warning("rebuild public qs: %s", e)
                pub_qs = []

        src_by_text = {}
        src_by_id = {}
        for q in qs_src:
            if not isinstance(q, dict):
                continue
            src_by_id[str(q.get("id"))] = q
            t = _nt(q.get("text"))
            if t:
                src_by_text[t] = q

        correct = 0
        total = len(qs_src)
        graded_src_ids = set()

        for pq in pub_qs:
            if not isinstance(pq, dict):
                continue
            pqid = str(pq.get("id"))
            a = answers.get(pqid)
            if a is None:
                continue
            opts = pq.get("options") or []
            sel_text = None
            if isinstance(a, dict):
                sel_text = a.get("t") or a.get("text")
                try:
                    ci = int(a.get("i", a.get("index")))
                    if sel_text is None and 0 <= ci < len(opts):
                        sel_text = opts[ci]
                except Exception:
                    pass
            else:
                try:
                    ci = int(a)
                    if 0 <= ci < len(opts):
                        sel_text = opts[ci]
                except Exception:
                    sel_text = str(a) if a is not None else None
            if sel_text is None:
                continue

            src = src_by_id.get(pqid) or src_by_text.get(_nt(pq.get("text")))
            if not src:
                continue
            ctext = _src_correct_text(src)
            if ctext is None:
                continue
            sid = str(src.get("id"))
            if sid in graded_src_ids:
                continue
            if _nt(sel_text) == _nt(ctext):
                correct += 1
                graded_src_ids.add(sid)

        if correct == 0 and answers and pub_qs:
            ans_items = sorted(
                answers.items(),
                key=lambda kv: (not str(kv[0]).isdigit(), int(kv[0]) if str(kv[0]).isdigit() else str(kv[0])),
            )
            for i, pq in enumerate(pub_qs):
                if i >= len(ans_items):
                    break
                a = ans_items[i][1]
                opts = (pq or {}).get("options") or []
                try:
                    ci = int(a) if not isinstance(a, dict) else int(a.get("i", a.get("index")))
                except Exception:
                    continue
                if not (0 <= ci < len(opts)):
                    continue
                sel_text = opts[ci]
                src = src_by_text.get(_nt((pq or {}).get("text")))
                if not src:
                    continue
                ctext = _src_correct_text(src)
                if ctext and _nt(sel_text) == _nt(ctext):
                    correct += 1

        return correct, total

    _orig = oe.submit_exam

    def submit_exam(session_id, session_token=None, answers=None, fingerprint=None, **kwargs):
        if isinstance(session_token, dict) and answers is None:
            answers = session_token
            session_token = kwargs.get("sessionToken") or kwargs.get("session_token")
        if session_token is None:
            session_token = kwargs.get("sessionToken") or kwargs.get("session_token")

        session = oe._load_session(session_id)
        if not session:
            try:
                session = oe._load_sessions().get(str(session_id))
            except Exception:
                session = None
        if not session:
            raise ValueError("session_not_found")

        if session.get("status") in ("passed", "failed", "timeout", "submitted", "finished"):
            raise ValueError("already_submitted")

        tok = session.get("sessionToken") or session.get("session_token")
        if session_token and tok and str(session_token).strip() and str(tok).strip():
            if str(session_token) != str(tok):
                raise ValueError("invalid token")

        from db.repo import find_olympiad
        oly = find_olympiad(session.get("olympiadId"))

        answers = answers or {}
        if not isinstance(answers, dict):
            answers = {}

        correct, total = _grade_answers(session, answers, oly)

        timed_out = False
        rem = oe._remaining_sec(session.get("expiresAt"))
        if rem is not None and rem <= 0:
            timed_out = True

        score = int(round(100.0 * correct / total)) if total else 0
        pass_score = int((oly or {}).get("passScore") or (oly or {}).get("pass_score") or 50)
        status = "timeout" if timed_out else ("passed" if score >= pass_score else "failed")
        finished = oe._utc_now()

        session["status"] = status
        session["score"] = score
        session["correct"] = correct
        session["total"] = total
        session["finishedAt"] = finished
        try:
            sessions = oe._load_sessions()
            if str(session_id) in sessions:
                sessions[str(session_id)].update(session)
                oe._save_sessions(sessions)
        except Exception:
            pass

        try:
            if oe.is_postgres_enabled():
                from sqlalchemy import text
                with oe.get_session() as s:
                    try:
                        s.execute(
                            text(
                                "UPDATE attempts SET status = CAST(:st AS attempt_status), "
                                "score = :score, correct = :c, total = :t, pass_score = :ps, "
                                "finished_at = NOW() WHERE id::text = :id"
                            ),
                            {
                                "st": status if status in ("passed", "failed", "timeout", "submitted") else "failed",
                                "score": score, "c": correct, "t": total, "ps": pass_score, "id": session_id,
                            },
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
                    try:
                        s.commit()
                    except Exception:
                        pass
        except Exception as e:
            log.error("persist score: %s", e)

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
            "finishedAt": finished,
            "serverNow": oe._utc_now(),
        }
        show = bool(
            (oly or {}).get("showResultsToStudents")
            or (oly or {}).get("show_results_to_students")
            or (oly or {}).get("olyShowResults")
        )
        result["showResultsToStudents"] = show
        if not show:
            return {
                "ok": True,
                "hideScore": True,
                "pendingReview": True,
                "message": "Шумо бо муваффақият супоридед. Натиҷа баъдтар аз ҷониби админ эълон мешавад.",
                "status": "submitted",
                "attemptId": session_id,
                "olympiadId": session.get("olympiadId"),
                "finishedAt": finished,
                "serverNow": result["serverNow"],
                "showResultsToStudents": False,
                "result": {
                    "hideScore": True,
                    "pendingReview": True,
                    "status": "submitted",
                    "attemptId": session_id,
                },
            }
        return {"ok": True, "result": result, **result}

    oe.submit_exam = submit_exam

    try:
        def _student_uuid(code):
            code = oe._norm_code(code)
            if not code or not oe.is_postgres_enabled():
                return None
            try:
                from sqlalchemy import text
                with oe.get_session() as s:
                    row = s.execute(
                        text(
                            "SELECT id FROM students WHERE student_code = :c OR id::text = :c LIMIT 1"
                        ),
                        {"c": code},
                    ).fetchone()
                    return str(row[0]) if row else None
            except Exception as e:
                log.warning("student_uuid: %s", e)
                return None
        oe._student_uuid = _student_uuid
    except Exception as e:
        log.warning("student_uuid patch: %s", e)

    print("[boot] patch_score_text: TEXT-based grading (shuffle-safe) installed")
    log.info("patch_score_text text-grade installed")
