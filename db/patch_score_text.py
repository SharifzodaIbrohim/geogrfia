"""Boot patch: rebuild scoreMap on submit when session file lost (Render ephemeral).
Also grade by option text + optionMap; align answer keys 1/2 vs UUID.
"""
from __future__ import annotations
import logging

log = logging.getLogger("geografia.patch_score_text")


def install(app=None):
    try:
        from db import olympiad_engine as oe
    except Exception as e:
        log.warning("patch_score_text: %s", e)
        return

    def _nt(v):
        return " ".join(str(v or "").strip().split()).lower()

    def _rebuild_score_map(session):
        try:
            from db.repo import find_olympiad
            oid = session.get("olympiadId")
            code = session.get("studentId") or session.get("student_code") or ""
            oly = find_olympiad(oid) if oid else None
            qs = (oly or {}).get("questions") or []
            if not qs:
                return {}, []
            public, smap = oe._build_pack(qs, code, oid)
            return smap or {}, public or []
        except Exception as e:
            log.warning("rebuild scoreMap: %s", e)
            return {}, []

    def _ensure_score_map(session, session_id):
        score_map = (session or {}).get("scoreMap") or {}
        if score_map:
            return session, score_map
        try:
            stored = oe._load_sessions().get(str(session_id)) or {}
            if stored.get("scoreMap"):
                session = dict(session or {})
                session["scoreMap"] = stored["scoreMap"]
                if stored.get("questions") and not session.get("questions"):
                    session["questions"] = stored["questions"]
                return session, session["scoreMap"]
        except Exception:
            pass
        smap, public = _rebuild_score_map(session or {})
        if smap:
            session = dict(session or {})
            session["scoreMap"] = smap
            if public and not session.get("questions"):
                session["questions"] = public
            try:
                sessions = oe._load_sessions()
                if str(session_id) in sessions:
                    sessions[str(session_id)]["scoreMap"] = smap
                    if public:
                        sessions[str(session_id)]["questions"] = public
                    oe._save_sessions(sessions)
            except Exception:
                pass
        return session, smap

    def _grade_one(qid, a, meta, pub_by_id):
        if not meta:
            return False
        qt = str(meta.get("type") or "single").lower()
        cidx = meta.get("correctIndex")
        ctext = meta.get("correctText")
        omap = meta.get("optionMap") or []
        if isinstance(a, dict):
            ci, ct = a.get("i", a.get("index")), a.get("t", a.get("text"))
        else:
            ci, ct = a, None
        if qt in ("short", "text", "number", "numeric", "open", "essay", "written"):
            return _nt(ct if ct is not None else ci) == _nt(meta.get("answer") or ctext)
        if qt in ("matching", "match"):
            expected = meta.get("pairs") or meta.get("answer") or {}
            if not isinstance(expected, dict) or not expected:
                return False
            sel = a if isinstance(a, dict) else {}
            sel = {str(k): v for k, v in sel.items() if str(k) not in ("i", "t", "index", "text")}
            ok_n = 0
            for k, v in expected.items():
                try:
                    if int(sel.get(str(k), sel.get(k, -999))) == int(v):
                        ok_n += 1
                except Exception:
                    continue
            return ok_n == len(expected)
        if ct is not None and ctext is not None and _nt(ct) == _nt(ctext):
            return True
        try:
            ci = int(ci) if ci is not None else None
        except Exception:
            ci = None
        if ci is not None and omap and 0 <= ci < len(omap) and cidx is not None and omap[ci] == cidx:
            return True
        if ci is not None and cidx is not None and ci == cidx and not omap:
            return True
        if ci is not None and pub_by_id.get(str(qid)):
            opts = pub_by_id[str(qid)].get("options") or []
            if 0 <= ci < len(opts) and ctext is not None and _nt(opts[ci]) == _nt(ctext):
                return True
        return False

    _orig = oe.submit_exam

    def submit_exam(session_id, session_token=None, answers=None, fingerprint=None, **kwargs):
        if isinstance(session_token, dict) and answers is None:
            answers = session_token
            session_token = kwargs.get("sessionToken") or kwargs.get("session_token")
        if session_token is None:
            session_token = kwargs.get("sessionToken") or kwargs.get("session_token")

        session = oe._load_session(session_id)
        if not session:
            raise ValueError("session_not_found")

        session, score_map = _ensure_score_map(session, session_id)

        if not score_map:
            log.warning("submit without scoreMap session=%s", session_id)
            return _orig(session_id, session_token, answers, fingerprint=fingerprint, **kwargs)

        if session.get("status") in ("passed", "failed", "timeout", "submitted", "finished"):
            raise ValueError("already_submitted")
        tok = session.get("sessionToken") or session.get("session_token")
        if session_token and tok and str(session_token).strip() and str(tok).strip() and str(session_token) != str(tok):
            raise ValueError("invalid token")

        from db.repo import find_olympiad
        oly = find_olympiad(session.get("olympiadId"))
        answers = answers or {}
        if not isinstance(answers, dict):
            answers = {}
        answers = {str(k): v for k, v in answers.items()}

        pub_qs = session.get("questions") or []
        pub_by_id = {str(q.get("id")): q for q in pub_qs if isinstance(q, dict)}

        smap_keys = list(score_map.keys())
        if answers and smap_keys and not any(str(k) in answers for k in smap_keys):
            aligned = {}
            if pub_qs and len(pub_qs) == len(smap_keys):
                for q in pub_qs:
                    pqid = str(q.get("id"))
                    if pqid in answers and pqid in score_map:
                        aligned[pqid] = answers[pqid]
            if not aligned:
                ordered = sorted(
                    smap_keys,
                    key=lambda k: (score_map[k] or {}).get("originalIndex", 999),
                )
                ans_keys = sorted(
                    answers.keys(),
                    key=lambda x: (not str(x).isdigit(), int(x) if str(x).isdigit() else str(x)),
                )
                for i, sk in enumerate(ordered):
                    if i < len(ans_keys):
                        aligned[str(sk)] = answers[ans_keys[i]]
            if aligned:
                answers = aligned
                log.info("aligned answer keys for session %s", session_id)

        correct = 0
        total = len(score_map)
        timed_out = False
        rem = oe._remaining_sec(session.get("expiresAt"))
        if rem is not None and rem <= 0:
            timed_out = True

        for qid, meta in score_map.items():
            a = answers.get(str(qid))
            if a is None:
                a = answers.get(qid)
            if _grade_one(qid, a, meta, pub_by_id):
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
        print("[boot] patch_score_text: _student_uuid uses student_code")
    except Exception as e:
        log.warning("student_uuid patch: %s", e)

    print("[boot] patch_score_text: rebuild scoreMap + text grade installed")
    log.info("patch_score_text installed")
