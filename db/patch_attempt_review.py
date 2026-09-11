"""Admin attempt review — plain Python. Uses attempt_answers + answers_json fallback."""
from __future__ import annotations

import json
import logging

log = logging.getLogger("geografia.review")


def _eng():
    try:
        from db.connection import get_engine
        e = get_engine()
        if e is not None:
            return e
    except Exception:
        pass
    try:
        from db import connection as c
        e = getattr(c, "engine", None)
        if e is not None:
            return e
    except Exception:
        pass
    raise RuntimeError("PostgreSQL engine дастнорас")


def _parse(v):
    if v is None:
        return None
    if isinstance(v, (dict, list)):
        return v
    if isinstance(v, (bytes, bytearray)):
        try:
            v = v.decode("utf-8")
        except Exception:
            return None
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return None
        try:
            return json.loads(s)
        except Exception:
            return None
    return None


def _iso(v):
    return v.isoformat() if hasattr(v, "isoformat") else v


def _option_texts(q: dict) -> list:
    opts = q.get("options") or q.get("choices") or []
    out = []
    for o in opts:
        if isinstance(o, dict):
            out.append(str(o.get("text") or o.get("label") or o.get("value") or ""))
        else:
            out.append(str(o))
    return out


def _correct_from_q(q: dict):
    for k in ("correctAnswer", "answerText", "correct_text", "correct"):
        v = q.get(k)
        if v is not None and not isinstance(v, (list, dict)):
            return str(v)
    texts = _option_texts(q)
    ci = q.get("correctIndex")
    if ci is None:
        ci = q.get("correct_index")
    if ci is None:
        ci = q.get("answer")
    try:
        if ci is not None and str(ci).strip().isdigit():
            ci = int(str(ci).strip())
            if 0 <= ci < len(texts):
                return texts[ci]
    except Exception:
        pass
    for o in (q.get("options") or []):
        if isinstance(o, dict) and (o.get("isCorrect") or o.get("is_correct") or o.get("correct")):
            return str(o.get("text") or o.get("label") or "")
    return None


def _student_from_raw(sel, texts: list):
    if sel is None:
        return None
    if isinstance(sel, dict):
        for k in ("t", "text", "selectedText", "answer", "value"):
            if sel.get(k) is not None:
                return str(sel.get(k))
        for k in ("i", "index", "oi", "optionIndex", "selected_idx"):
            if sel.get(k) is not None:
                try:
                    i = int(sel[k])
                    if 0 <= i < len(texts):
                        return texts[i]
                    return str(i)
                except Exception:
                    pass
        return json.dumps(sel, ensure_ascii=False)
    if isinstance(sel, int):
        if 0 <= sel < len(texts):
            return texts[sel]
        return str(sel)
    if isinstance(sel, str):
        return sel
    return str(sel)


def build_review(attempt_id):
    attempt_id = str(attempt_id or "").strip()
    if not attempt_id:
        raise ValueError("attempt_not_found")
    from sqlalchemy import text
    eng = _eng()
    att = None
    answers_rows = []
    answers_json = None
    with eng.connect() as conn:
        sqls = [
            """SELECT a.id::text AS id, a.olympiad_id::text AS olympiad_id,
                      COALESCE(NULLIF(TRIM(st.full_name), ''), NULLIF(TRIM(a.student_name), ''), '') AS student_name,
                      COALESCE(NULLIF(TRIM(st.class_name), ''), COALESCE(a.student_class, '')) AS student_class,
                      COALESCE(NULLIF(TRIM(st.school_name), ''), COALESCE(a.student_school, '')) AS student_school,
                      COALESCE(NULLIF(TRIM(st.student_code), ''), '') AS student_code,
                      a.score, a.correct, a.total, a.pass_score,
                      CAST(a.status AS text) AS status,
                      a.finished_at, a.started_at,
                      o.title AS olympiad_title, o.questions_json,
                      a.answers_json
               FROM attempts a
               LEFT JOIN olympiads o ON o.id = a.olympiad_id
               LEFT JOIN students st ON (
                 (a.student_id IS NOT NULL AND st.id = a.student_id)
                 OR (a.student_name IS NOT NULL AND TRIM(a.student_name) ~ '^[0-9]{8,}$' AND st.student_code = TRIM(a.student_name))
               )
               WHERE a.id::text = :id LIMIT 1""",
            """SELECT a.id::text AS id, a.olympiad_id::text AS olympiad_id,
                      COALESCE(a.student_name, '') AS student_name,
                      COALESCE(a.student_class, '') AS student_class,
                      COALESCE(a.student_school, '') AS student_school,
                      '' AS student_code,
                      a.score, a.correct, a.total, a.pass_score,
                      CAST(a.status AS text) AS status,
                      a.finished_at, a.started_at,
                      o.title AS olympiad_title, o.questions_json,
                      a.answers_json
               FROM attempts a
               LEFT JOIN olympiads o ON o.id = a.olympiad_id
               WHERE a.id::text = :id LIMIT 1""",
            """SELECT a.id::text AS id, a.olympiad_id::text AS olympiad_id,
                      COALESCE(a.student_name, '') AS student_name,
                      '' AS student_class, '' AS student_school, '' AS student_code,
                      a.score, a.correct, a.total, a.pass_score,
                      CAST(a.status AS text) AS status,
                      a.finished_at, a.started_at,
                      '' AS olympiad_title, NULL AS questions_json, NULL AS answers_json
               FROM attempts a WHERE a.id::text = :id LIMIT 1""",
        ]
        for sql in sqls:
            try:
                row = conn.execute(text(sql), {"id": attempt_id}).mappings().first()
                if row:
                    att = dict(row)
                    break
            except Exception as e:
                log.warning("review att: %s", e)
                try:
                    conn.rollback()
                except Exception:
                    pass
        if not att:
            raise ValueError("attempt_not_found")

        answers_json = _parse(att.get("answers_json"))
        for sql in [
            """SELECT question_id::text AS qid, answer_text, selected_option, selected_text,
                      selected_idx, is_correct, points, max_score
               FROM attempt_answers WHERE attempt_id::text = :id""",
            """SELECT question_id::text AS qid, answer AS answer_text,
                      NULL AS selected_option, NULL AS selected_text,
                      NULL AS selected_idx, is_correct, NULL AS points, NULL AS max_score
               FROM attempt_answers WHERE attempt_id::text = :id""",
        ]:
            try:
                answers_rows = [dict(r) for r in conn.execute(text(sql), {"id": attempt_id}).mappings().all()]
                if answers_rows:
                    break
            except Exception as e:
                log.warning("review ans: %s", e)
                try:
                    conn.rollback()
                except Exception:
                    pass

    qs = _parse(att.get("questions_json")) or []
    if isinstance(qs, dict):
        qs = qs.get("questions") or qs.get("items") or []
    by_qid = {str(a.get("qid") or ""): a for a in answers_rows}
    items = []
    ok_n = bad_n = blank_n = 0
    for i, q in enumerate(qs or []):
        if not isinstance(q, dict):
            q = {"text": str(q)}
        qid = str(q.get("id") or q.get("questionId") or i)
        text_q = q.get("text") or q.get("question") or q.get("prompt") or ""
        opts = _option_texts(q)
        correct = _correct_from_q(q)
        aa = by_qid.get(qid) or by_qid.get(str(i)) or {}
        student = (
            aa.get("answer_text")
            or aa.get("selected_text")
            or aa.get("selected_option")
        )
        if student is None and isinstance(answers_json, dict):
            student = _student_from_raw(answers_json.get(qid) or answers_json.get(str(i)), opts)
        if student is None and aa.get("selected_idx") is not None:
            try:
                si = int(aa["selected_idx"])
                if 0 <= si < len(opts):
                    student = opts[si]
            except Exception:
                pass
        if isinstance(student, (dict, list)):
            student = json.dumps(student, ensure_ascii=False)
        is_blank = student is None or str(student).strip() in ("", "None")
        is_ok = bool(aa.get("is_correct")) if aa.get("is_correct") is not None else False
        if (not is_blank) and correct is not None:
            is_ok = str(student).strip().lower() == str(correct).strip().lower()
        if is_blank:
            blank_n += 1
            label = "Беҷавоб"
        elif is_ok:
            ok_n += 1
            label = "Дуруст"
        else:
            bad_n += 1
            label = "Нодуруст"
        items.append({
            "index": i + 1,
            "questionId": qid,
            "type": q.get("type") or "single",
            "question": text_q,
            "text": text_q,
            "options": opts,
            "studentAnswer": "" if is_blank else str(student),
            "selectedText": "" if is_blank else str(student),
            "correctAnswer": "" if correct is None else str(correct),
            "correctText": "" if correct is None else str(correct),
            "isCorrect": is_ok,
            "isBlank": is_blank,
            "resultLabel": label,
            "points": aa.get("points"),
            "maxScore": aa.get("max_score") or q.get("maxScore") or 1,
        })
    if not items and answers_rows:
        for i, a in enumerate(answers_rows):
            ok = bool(a.get("is_correct"))
            blank = not (a.get("answer_text") or a.get("selected_text") or a.get("selected_option"))
            items.append({
                "index": i + 1,
                "questionId": a.get("qid"),
                "question": "",
                "options": [],
                "studentAnswer": a.get("answer_text") or a.get("selected_text") or a.get("selected_option") or "",
                "correctAnswer": "",
                "isCorrect": ok,
                "isBlank": blank,
                "resultLabel": "Беҷавоб" if blank else ("Дуруст" if ok else "Нодуруст"),
                "points": a.get("points"),
            })
            if blank:
                blank_n += 1
            elif ok:
                ok_n += 1
            else:
                bad_n += 1
    if not items and isinstance(answers_json, dict) and answers_json:
        for i, (qid, sel) in enumerate(answers_json.items()):
            student = _student_from_raw(sel, [])
            blank = student is None or str(student).strip() in ("", "None")
            items.append({
                "index": i + 1,
                "questionId": str(qid),
                "question": "",
                "options": [],
                "studentAnswer": "" if blank else str(student),
                "correctAnswer": "",
                "isCorrect": False,
                "isBlank": blank,
                "resultLabel": "Беҷавоб" if blank else "Ҷавоб",
            })
            if blank:
                blank_n += 1
    name = (att.get("student_name") or "").strip() or "—"
    return {
        "ok": True,
        "attemptId": att.get("id"),
        "id": att.get("id"),
        "olympiadId": att.get("olympiad_id"),
        "olympiadTitle": att.get("olympiad_title") or "",
        "studentName": name,
        "fullName": name,
        "name": name,
        "className": att.get("student_class") or "",
        "school": att.get("student_school") or "",
        "studentCode": att.get("student_code") or "",
        "studentId": att.get("student_code") or "",
        "score": att.get("score"),
        "correct": att.get("correct"),
        "total": att.get("total"),
        "status": att.get("status"),
        "finishedAt": _iso(att.get("finished_at")),
        "startedAt": _iso(att.get("started_at")),
        "items": items,
        "stats": {"correct": ok_n, "wrong": bad_n, "blank": blank_n, "total": len(items)},
        "earned": att.get("correct"),
        "totalMax": att.get("total"),
    }


def install(app=None):
    if app is None:
        return
    from flask import jsonify

    def admin_attempt_review(attempt_id):
        try:
            return jsonify(build_review(attempt_id))
        except ValueError as e:
            if str(e) == "attempt_not_found":
                return jsonify({"error": "Attempt ёфт нашуд", "code": "not_found"}), 404
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            log.exception("review")
            return jsonify({"error": "Хатои сервер", "detail": str(e)}), 500

    bound = 0
    for rule in list(app.url_map.iter_rules()):
        path = str(rule.rule)
        if "attempt" in path and path.endswith("/review"):
            app.view_functions[rule.endpoint] = admin_attempt_review
            bound += 1
            print("[boot] review rebound", rule.endpoint, path)
    if not bound:
        app.add_url_rule(
            "/api/admin/attempts/<attempt_id>/review",
            "admin_attempt_review_plain",
            admin_attempt_review,
            methods=["GET"],
        )
        print("[boot] review added /api/admin/attempts/<id>/review")
    print("[boot] patch_attempt_review PLAIN OK bound=%s" % bound)
