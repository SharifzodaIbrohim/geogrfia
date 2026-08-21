"""Force-register olympiad POST routes — override view_functions, never orphan rules."""
from __future__ import annotations

import logging
import traceback

log = logging.getLogger("geografia.force_olympiad_routes")


def install(app=None):
    if app is None:
        print("[boot] force_olympiad_routes: no app")
        return

    from flask import jsonify, request

    try:
        from db import olympiad_engine
        from db.repo import find_olympiad
        print("[boot] force_olympiad_routes: engine import OK")
    except Exception as e:
        log.exception("force routes import failed: %s", e)
        print("[boot] force_olympiad_routes IMPORT FAILED:", e)

        def _diag_start(olympiad_id):
            return jsonify({"error": "engine_import_failed", "reason": str(e)[:400]}), 503

        _bind_start_handlers(app, _diag_start, _diag_start, _diag_start, _diag_start)
        print("[boot] force_olympiad_routes: diagnostic start bound")
        return

    def _student_id(payload):
        return str(
            (payload or {}).get("studentId")
            or (payload or {}).get("id")
            or request.headers.get("X-Student-Id")
            or ""
        ).strip()

    def _fp():
        v = request.headers.get("X-Client-Fingerprint", "")[:64]
        return v or None

    def _window_ok(oly):
        try:
            if not oly.get("isActive"):
                return "inactive"
            from datetime import datetime, timezone

            def _p(v):
                if not v:
                    return None
                try:
                    d = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
                    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
                except Exception:
                    return None

            now = datetime.now(timezone.utc)
            st = _p(oly.get("startTime") or oly.get("start_at"))
            et = _p(oly.get("endTime") or oly.get("end_at"))
            if st and now < st:
                return "not_started"
            if et and now > et:
                return "ended"
            return "open"
        except Exception:
            return "open" if oly.get("isActive") else "inactive"

    def olympiad_start(olympiad_id):
        try:
            payload = request.get_json(silent=True) or {}
            student_id = _student_id(payload)
            if not student_id:
                return jsonify({"error": "studentId лозим аст.", "reason": "student_id_required"}), 400
            oly = find_olympiad(olympiad_id)
            if not oly:
                return jsonify({"error": "Олимпиада ёфт нашуд."}), 404
            win = _window_ok(oly)
            if win != "open":
                msgs = {
                    "inactive": "Олимпиада фаъол нест.",
                    "not_started": "Ҳанӯз оғоз нашудааст.",
                    "ended": "Вақт ба охир расид.",
                }
                return jsonify({"error": msgs.get(win, win), "windowStatus": win}), 403
            try:
                session = olympiad_engine.start_exam(
                    olympiad_id, student_id, client_fingerprint=_fp(), fingerprint=_fp()
                )
            except ValueError as e:
                code = str(e)
                messages = {
                    "rate_limited": "Зиёд дархост — каме интизор шавед.",
                    "already_submitted": "Шумо аллакай супоридаед (як маротиба).",
                    "not_assigned": "Шумо ба ин олимпиада таъин нашудаед.",
                    "student_not_found": "ID нодуруст аст.",
                    "student_id_required": "Student ID лозим аст.",
                    "no_questions": "Саволҳо нестанд.",
                    "not_found": "Олимпиада ёфт нашуд.",
                    "session_save_failed": "Сессия захира нашуд.",
                    "not_started": "Ҳанӯз оғоз нашудааст.",
                    "ended": "Вақт ба охир расид.",
                    "closed": "Олимпиада фаъол нест.",
                }
                status = 404 if code == "not_found" else 403
                return jsonify({"error": messages.get(code, code), "reason": code}), status
            if not isinstance(session, dict):
                return jsonify({"error": "bad_session", "type": str(type(session))}), 500
            safe = {}
            for k, v in session.items():
                try:
                    jsonify({k: v})
                    safe[k] = v
                except Exception:
                    safe[k] = str(v)
            return jsonify(safe)
        except Exception as e:
            log.exception("force start failed")
            return jsonify({
                "error": "Хатои дохилӣ.",
                "reason": str(e)[:400],
                "trace": traceback.format_exc()[-1500:],
            }), 500

    def olympiad_autosave(olympiad_id):
        try:
            payload = request.get_json(silent=True) or {}
            session_id = str(payload.get("sessionId") or payload.get("attemptId") or "").strip()
            session_token = str(payload.get("sessionToken") or "").strip()
            answers = payload.get("answers") or {}
            if not session_id or not session_token:
                return jsonify({"error": "sessionId ва sessionToken лозиманд."}), 400
            return jsonify(
                olympiad_engine.autosave(session_id, session_token, answers, fingerprint=_fp())
            )
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            log.exception("force autosave failed")
            return jsonify({"error": "Хатои дохилӣ.", "reason": str(e)[:300]}), 500

    def _do_submit(olympiad_id):
        try:
            payload = request.get_json(silent=True) or {}
            session_id = str(payload.get("sessionId") or payload.get("attemptId") or "").strip()
            session_token = str(payload.get("sessionToken") or "").strip()
            student_id = _student_id(payload)
            answers = payload.get("answers")
            if isinstance(answers, list):
                amap = {}
                for i, a in enumerate(answers):
                    if isinstance(a, dict):
                        qid = a.get("questionId", a.get("id", i))
                        sel = a.get("selected", a.get("selectedIndex", a.get("answer")))
                        if qid is not None and sel is not None:
                            amap[str(qid)] = sel
                    else:
                        try:
                            amap[str(i)] = int(a)
                        except (TypeError, ValueError):
                            pass
                answers = amap
            if not isinstance(answers, dict):
                answers = {}
            if not session_id or not session_token:
                try:
                    resolved = olympiad_engine.resolve_session_for_submit(
                        olympiad_id, student_code=student_id or None, session_id=session_id or None
                    )
                except Exception:
                    resolved = None
                if not resolved:
                    return jsonify(
                        {"error": "Сессия ёфт нашуд. Аввал start кунед.", "reason": "session_not_found"}
                    ), 400
                session_id = resolved["sessionId"]
                session_token = resolved["sessionToken"]
            result = olympiad_engine.submit_exam(
                session_id, session_token, answers, fingerprint=_fp()
            )
            if isinstance(result, dict) and result.get("hideScore"):
                return jsonify(result)
            body = {"ok": True, "result": result.get("result") if isinstance(result, dict) else result}
            if isinstance(result, dict):
                for k in (
                    "score", "correct", "total", "passScore", "status", "finishedAt",
                    "hideScore", "pendingReview", "message", "showResultsToStudents",
                ):
                    if k in result:
                        body[k] = result[k]
                        if isinstance(body.get("result"), dict) and k not in body["result"]:
                            body["result"][k] = result[k]
            return jsonify(body)
        except ValueError as e:
            code = str(e)
            messages = {
                "already_submitted": "Аллакай супорида шудааст.",
                "session_not_found": "Сессия ёфт нашуд.",
                "not_found": "Ёфт нашуд.",
                "timeout": "Вақт ба охир расид.",
            }
            return jsonify({"error": messages.get(code, code), "reason": code}), 400
        except Exception as e:
            log.exception("force submit failed")
            return jsonify({
                "error": "Хатои дохилӣ.",
                "reason": str(e)[:300],
                "trace": traceback.format_exc()[-800:],
            }), 500

    def olympiad_exam_submit(olympiad_id):
        return _do_submit(olympiad_id)

    def olympiad_submit(olympiad_id):
        return _do_submit(olympiad_id)

    _bind_start_handlers(app, olympiad_start, olympiad_autosave, olympiad_exam_submit, olympiad_submit)

    print("[boot] force_olympiad_routes: POST start/exam-submit/submit/autosave bound")
    log.info("force olympiad routes installed")


def _bind_start_handlers(app, start_fn, autosave_fn, exam_submit_fn, submit_fn):
    """Override existing endpoints in place — never orphan a Rule without a view."""
    for rule in list(app.url_map.iter_rules()):
        rule_s = str(rule).rstrip("/")
        if "/olympiads/" not in rule_s:
            continue
        if rule_s.endswith("/start"):
            app.view_functions[rule.endpoint] = start_fn
            log.info("override endpoint %s -> start", rule.endpoint)
        elif rule_s.endswith("/autosave"):
            app.view_functions[rule.endpoint] = autosave_fn
        elif rule_s.endswith("/exam-submit"):
            app.view_functions[rule.endpoint] = exam_submit_fn
        elif rule_s.endswith("/submit"):
            app.view_functions[rule.endpoint] = submit_fn

    for name, fn in (
        ("olympiad_start", start_fn),
        ("oe_force_start", start_fn),
        ("start_olympiad", start_fn),
        ("olympiad_autosave", autosave_fn),
        ("oe_force_autosave", autosave_fn),
        ("olympiad_exam_submit", exam_submit_fn),
        ("oe_force_exam_submit", exam_submit_fn),
        ("olympiad_submit", submit_fn),
        ("oe_force_submit", submit_fn),
        ("submit_olympiad", submit_fn),
    ):
        app.view_functions[name] = fn

    existing = {str(r).rstrip("/") for r in app.url_map.iter_rules()}
    pairs = [
        ("/api/olympiads/<olympiad_id>/start", "oe_force_start", start_fn),
        ("/api/olympiads/<olympiad_id>/autosave", "oe_force_autosave", autosave_fn),
        ("/api/olympiads/<olympiad_id>/exam-submit", "oe_force_exam_submit", exam_submit_fn),
        ("/api/olympiads/<olympiad_id>/submit", "oe_force_submit", submit_fn),
    ]
    for path, endpoint, fn in pairs:
        if path.rstrip("/") not in existing:
            try:
                app.add_url_rule(path, endpoint=endpoint, view_func=fn, methods=["POST"])
            except Exception as e:
                log.warning("add_url_rule %s: %s", path, e)
                app.view_functions[endpoint] = fn
