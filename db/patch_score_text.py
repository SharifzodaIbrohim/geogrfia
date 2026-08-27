"""Boot patch: grade by question text + selected option text (shuffle-safe)."""
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

    def _opts(q):
        raw = (q or {}).get("options") or []
        out = []
        for o in raw:
            if isinstance(o, dict):
                out.append(str(o.get("text") or o.get("label") or o.get("value") or ""))
            else:
                out.append(str(o) if o is not None else "")
        return out

    def _src_correct_text(q):
        if not isinstance(q, dict):
            return None
        opts = _opts(q)
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

    def _sel_text(a, opts):
        if a is None:
            return None
        if isinstance(a, dict):
            t = a.get("t") or a.get("text")
            if t is not None:
                return str(t)
            try:
                ci = int(a.get("i", a.get("index")))
                if 0 <= ci < len(opts):
                    return opts[ci]
            except Exception:
                return None
        try:
            ci = int(a)
            if 0 <= ci < len(opts):
                return opts[ci]
        except Exception:
            return str(a)
        return None

    def _q_max(src):
        try:
            ms = float((src or {}).get("maxScore") or (src or {}).get("points") or 1)
        except (TypeError, ValueError):
            ms = 1.0
        if ms <= 0:
            ms = 1.0
        return ms

    def _grade_answers(session, answers, oly):
        """Return (correct_count, question_count, earned_points, total_max_score)."""
        qs_src = (oly or {}).get("questions") or []
        if not qs_src:
            return 0, 0, 0.0, 0.0

        answers = {str(k): v for k, v in (answers or {}).items()} if isinstance(answers, dict) else {}

        pub_qs = list(session.get("questions") or [])
        if not pub_qs:
            try:
                code = _student_code_from_session(session)
                oid = session.get("olympiadId")
                pub_qs, _ = oe._build_pack(qs_src, code, oid)
            except Exception as e:
                log.warning("rebuild public qs: %s", e)
                pub_qs = []

        pub_by_text = {}
        pub_by_id = {}
        for pq in pub_qs:
            if isinstance(pq, dict):
                pub_by_text[_nt(pq.get("text"))] = pq
                pub_by_id[str(pq.get("id"))] = pq

        correct = 0
        total = len(qs_src)
        earned = 0.0
        total_max = 0.0
        used_keys = set()

        for idx, src in enumerate(qs_src):
            if not isinstance(src, dict):
                continue
            qtype = str(src.get("type") or src.get("qtype") or "single").lower().strip()
            if qtype in ("choice", "mcq", "single_choice"):
                qtype = "single"
            if qtype in ("match",):
                qtype = "matching"

            max_s = _q_max(src)
            total_max += max_s

            pq = pub_by_text.get(_nt(src.get("text"))) or pub_by_id.get(str(src.get("id")))
            pqid = str((pq or src).get("id") if (pq or src) else idx)
            sel = None
            if pqid in answers:
                sel = answers.get(pqid)
            elif str(src.get("id")) in answers:
                sel = answers.get(str(src.get("id")))
            elif str(idx) in answers:
                sel = answers.get(str(idx))

            if qtype in ("short", "text", "number", "numeric", "open"):
                expected = src.get("correctText") or src.get("correctAnswer") or src.get("answerText")
                if expected is None and not isinstance(src.get("answer"), (list, dict)):
                    expected = src.get("answer")
                if expected is None or str(expected).strip() == "":
                    continue
                got = sel
                if isinstance(sel, dict):
                    got = sel.get("t") or sel.get("text") or sel.get("value")
                if got is None:
                    continue
                ok = False
                if qtype == "text" or "|" in str(expected):
                    keys = [x.strip() for x in str(expected).split("|") if x.strip()]
                    if any(_nt(k) in _nt(got) or _nt(got) == _nt(k) for k in keys):
                        ok = True
                else:
                    if _nt(got) == _nt(expected):
                        ok = True
                if ok:
                    correct += 1
                    earned += max_s
                    used_keys.add(pqid)
                continue

            if qtype == "matching":
                pairs = src.get("pairs") or src.get("correctPairs") or src.get("answer") or {}
                if not isinstance(pairs, dict) or not pairs:
                    continue
                if not isinstance(sel, dict):
                    continue
                pair_total = len(pairs) or 1
                ok_n = 0
                for k, v in pairs.items():
                    try:
                        if int(sel.get(str(k), sel.get(k))) == int(v):
                            ok_n += 1
                    except (TypeError, ValueError):
                        continue
                frac = ok_n / pair_total if pair_total else 0.0
                if frac > 0:
                    earned += frac * max_s
                if frac >= 1.0:
                    correct += 1
                    used_keys.add(pqid)
                continue

            ctext = _src_correct_text(src)
            if not ctext:
                log.warning("no correct text for q: %s", (src.get("text") or "")[:50])
                continue
            if not pq:
                continue
            opts = _opts(pq)
            matched = False
            if pqid in answers and pqid not in used_keys:
                st = _sel_text(answers.get(pqid), opts)
                if st is not None and _nt(st) == _nt(ctext):
                    matched = True
                    used_keys.add(pqid)
            if not matched:
                for ak, aval in answers.items():
                    if ak in used_keys:
                        continue
                    st = _sel_text(aval, opts)
                    if st is not None and _nt(st) == _nt(ctext):
                        matched = True
                        used_keys.add(ak)
                        break
            if matched:
                correct += 1
                earned += max_s

        return correct, total, earned, total_max

    def submit_exam(session_id, session_token=None, answers=None, fingerprint=None, **kwargs):
        if isinstance(session_token, dict) and answers is None:
            answers = session_token
            session_token = kwargs.get("sessionToken") or kwargs.get("session_token")
        if session_token is None:
            session_token = kwargs.get("sessionToken") or kwargs.get("session_token")

        session = oe._load_session(session_id)
        if not session:
            try:
                session = (oe._load_sessions() or {}).get(str(session_id))
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

        if not isinstance(answers, dict):
            answers = {}

        grade = _grade_answers(session, answers, oly)
        correct, total = grade[0], grade[1]
        earned = float(grade[2]) if len(grade) > 2 else float(correct)
        total_max = float(grade[3]) if len(grade) > 3 else float(total)

        timed_out = False
        rem = oe._remaining_sec(session.get("expiresAt"))
        if rem is not None and rem <= 0:
            timed_out = True

        if total_max > 0:
            score = int(round(100.0 * earned / total_max))
        elif total:
            score = int(round(100.0 * correct / total))
        else:
            score = 0
        pass_score = int((oly or {}).get("passScore") or (oly or {}).get("pass_score") or 50)
        status = "timeout" if timed_out else ("passed" if score >= pass_score else "failed")
        finished = oe._utc_now()

        for k, v in (("status", status), ("score", score), ("correct", correct), ("total", total),
                     ("earned", earned), ("totalMax", total_max), ("finishedAt", finished)):
            session[k] = v
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
                            {"st": status if status in ("passed", "failed", "timeout", "submitted") else "failed",
                             "score": score, "c": correct, "t": total, "ps": pass_score, "id": session_id},
                        )
                    except Exception:
                        s.execute(
                            text(
                                "UPDATE attempts SET status = :st, score = :score, correct = :c, "
                                "total = :t, pass_score = :ps, finished_at = NOW() WHERE id::text = :id"
                            ),
                            {"st": "passed" if status == "passed" else "failed",
                             "score": score, "c": correct, "t": total, "ps": pass_score, "id": session_id},
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
            "earned": earned,
            "totalMax": total_max,
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
                "result": {"hideScore": True, "pendingReview": True, "status": "submitted", "attemptId": session_id},
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
                        text("SELECT id FROM students WHERE student_code = :c OR id::text = :c LIMIT 1"),
                        {"c": code},
                    ).fetchone()
                    return str(row[0]) if row else None
            except Exception as e:
                log.warning("student_uuid: %s", e)
                return None
        oe._student_uuid = _student_uuid
    except Exception as e:
        log.warning("student_uuid patch: %s", e)

    print("[boot] patch_score_text: weighted maxScore grading installed")
    log.info("patch_score_text installed")
