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

        for qid, meta in score_map.items():
            sel = answers.get(qid)
            if sel is None:
                sel = answers.get(str(qid))
            if sel is None and meta.get("originalIndex") is not None:
                sel = answers.get(str(meta["originalIndex"]))
            if sel is None:
                continue

            oi = meta.get("originalIndex")
            q_orig = qs_src[oi] if isinstance(oi, int) and 0 <= oi < len(qs_src) else {}
            if not q_orig:
                for q in qs_src:
                    if str(q.get("id") if q.get("id") is not None else "") == str(qid):
                        q_orig = q
                        break

            client_i, selected_text = None, None
            if isinstance(sel, dict):
                for k in ("i", "index", "oi"):
                    if sel.get(k) is not None:
                        try: client_i = int(sel[k])
                        except Exception: pass
                        break
                for k in ("t", "text", "label"):
                    if sel.get(k) is not None:
                        selected_text = str(sel[k])
                        break
            else:
                try: client_i = int(sel)
                except (TypeError, ValueError):
                    selected_text = str(sel) if sel is not None else None

            pub = pub_by_id.get(str(qid)) or {}
            opts = pub.get("options") or []
            if selected_text is None and client_i is not None and 0 <= client_i < len(opts):
                o = opts[client_i]
                selected_text = o.get("text") if isinstance(o, dict) else str(o)

            ci = meta.get("correctIndex")
            texts = []
            for o in (q_orig.get("options") or []):
                texts.append(str(o.get("text") if isinstance(o, dict) else o))
            ct = meta.get("correctText")
            if ct is None and ci is not None and 0 <= ci < len(texts):
                ct = texts[ci]

            ok = False
            if selected_text is not None and ct is not None and _nt(selected_text) == _nt(ct):
                ok = True
            elif client_i is not None and meta.get("optionMap"):
                om = meta["optionMap"]
                if 0 <= client_i < len(om):
                    orig_i = om[client_i]
                    if ci is not None and orig_i == ci:
                        ok = True
                    elif ct is not None and 0 <= orig_i < len(texts) and _nt(texts[orig_i]) == _nt(ct):
                        ok = True
            if ok:
                correct += 1

        score = int(round((correct / total) * 100)) if total else 0
        pass_score = int((oly or {}).get("passScore") or 70)
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
        return {"ok": True, "result": result, **result}

    oe.submit_exam = submit_exam
    print("[boot] patch_score_text: text-based shuffle scoring installed")
