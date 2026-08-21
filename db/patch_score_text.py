"""Boot patch: grade shuffled MCQ by option text (fixes false low scores)."""
from __future__ import annotations
import logging

log = logging.getLogger("geografia.patch_score_text")

def install():
    try:
        from db import olympiad_engine as oe
    except Exception as e:
        log.warning("patch_score_text: %s", e)
        return

    _orig = oe.submit_exam

    def _nt(v):
        return " ".join(str(v or "").strip().split()).lower()

    def submit_exam(session_id, session_token=None, answers=None, fingerprint=None, **kwargs):
        if isinstance(session_token, dict) and answers is None:
            answers = session_token
            session_token = kwargs.get("sessionToken") or kwargs.get("session_token")
        if session_token is None:
            session_token = kwargs.get("sessionToken") or kwargs.get("session_token")

        session = oe._load_session(session_id)
        try:
            stored = oe._load_sessions().get(str(session_id)) or {}
            if stored and session is not None:
                if not session.get("scoreMap") and stored.get("scoreMap"):
                    session["scoreMap"] = stored["scoreMap"]
                if not session.get("questions") and stored.get("questions"):
                    session["questions"] = stored["questions"]
        except Exception:
            pass

        score_map = (session or {}).get("scoreMap") or {}
        if not score_map or not session:
            return _orig(session_id, session_token, answers, fingerprint=fingerprint, **kwargs)

        if session.get("status") in ("passed", "failed", "timeout", "submitted", "finished"):
            raise ValueError("already_submitted")
        tok = session.get("sessionToken") or session.get("session_token")
        if session_token and tok and str(session_token).strip() and str(tok).strip() and str(session_token) != str(tok):
            raise ValueError("invalid token")

        from db.repo import find_olympiad
        oly = find_olympiad(session.get("olympiadId"))
        qs_src = (oly or {}).get("questions") or []
        answers = answers or {}
        if not isinstance(answers, dict):
            answers = {}

        pub_qs = session.get("questions") or []
        pub_by_id = {str(q.get("id")): q for q in pub_qs if isinstance(q, dict)}

        correct = 0
        total = len(qs_src) if qs_src else len(score_map)
        timed_out = False
        rem = oe._remaining_sec(session.get("expiresAt"))
        if rem is not None and rem <= 0:
            timed_out = True

        for qid, meta in (score_map or {}).items():
            a = answers.get(qid) or answers.get(str(qid))
            qt = str((meta or {}).get("type") or "single").lower()
            cidx = (meta or {}).get("correctIndex")
            ctext = (meta or {}).get("correctText")
            omap = (meta or {}).get("optionMap") or []
            ok = False
            if isinstance(a, dict):
                ci, ct = a.get("i", a.get("index")), a.get("t", a.get("text"))
            else:
                ci, ct = a, None
            if qt in ("short", "text", "number", "numeric", "open", "essay", "written"):
                ok = _nt(ct if ct is not None else ci) == _nt((meta or {}).get("answer") or ctext)
            elif qt in ("matching", "match"):
                # accept dict of pairs or list; normalize both sides
                expected = (meta or {}).get("answer") or ctext or {}
                if isinstance(expected, dict) and isinstance(a, dict):
                    ok = all(_nt(a.get(k)) == _nt(v) for k, v in expected.items())
                elif isinstance(a, dict) and isinstance(expected, list):
                    ok = False
                else:
                    ok = _nt(a) == _nt(expected)
            else:
                if ct is not None and ctext is not None and _nt(ct) == _nt(ctext):
                    ok = True
                else:
                    try:
                        ci = int(ci) if ci is not None else None
                    except Exception:
                        ci = None
                    if ci is not None and omap and 0 <= ci < len(omap) and cidx is not None and omap[ci] == cidx:
                        ok = True
                    elif ci is not None and cidx is not None and ci == cidx and not omap:
                        ok = True
                    elif ct is not None and pub_by_id.get(str(qid)):
                        # fallback: match option text on public shuffled options then map
                        opts = pub_by_id[str(qid)].get("options") or []
                        for i, o in enumerate(opts):
                            if _nt(o) == _nt(ct):
                                if omap and 0 <= i < len(omap) and cidx is not None and omap[i] == cidx:
                                    ok = True
                                break
            if ok:
                correct += 1

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
                                "st": status if status in ("passed","failed","timeout","submitted") else "failed",
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
        except Exception as e:
            log.error("patch_score_text persist: %s", e)

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
        # Default hide: only show score when admin enabled showResultsToStudents
        show = False
        if isinstance(oly, dict):
            show = bool(
                oly.get("showResultsToStudents")
                or oly.get("show_results_to_students")
                or oly.get("olyShowResults")
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
    print("[boot] patch_score_text: text-based shuffle scoring installed")
