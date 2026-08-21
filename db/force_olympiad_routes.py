"""Force-register olympiad exam POST routes after boot.

Production returned 405 on POST /api/olympiads/<id>/start (Allow: GET,HEAD only).
This patch drops any existing rules for those paths and re-binds POST handlers.
"""
from __future__ import annotations

import logging

log = logging.getLogger("geografia.force_olympiad_routes")


def install(app=None):
    if app is None:
        print("[boot] force_olympiad_routes: no app")
        return

    from flask import jsonify, request

    try:
        from db import olympiad_engine
        from db.repo import find_olympiad
    except Exception as e:
        log.exception("force routes import failed: %s", e)
        print("[boot] force_olympiad_routes IMPORT FAILED:", e)
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
            return jsonify(session)
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
            }
            status = 404 if code == "not_found" else 403
            return jsonify({"error": messages.get(code, code), "reason": code}), status
        except Exception as e:
            log.exception("force start failed")
            return jsonify({"error": "Хатои дохилӣ.", "reason": str(e)[:200]}), 500

    def olympiad_autosave(olympiad_id):
        payload = request.get_json(silent=True) or {}
        session_id = str(payload.get("sessionId") or payload.get("attemptId") or "").strip()
        session_token = str(payload.get("sessionToken") or "").strip()
        answers = payload.get("answers") or {}
        if not session_id or not session_token:
            return jsonify({"error": "sessionId ва sessionToken лозиманд."}), 400
        try:
            return jsonify(
                olympiad_engine.autosave(session_id, session_token, answers, fingerprint=_fp())
            )
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            log.exception("force autosave failed")
            return jsonify({"error": "Хатои дохилӣ.", "reason": str(e)[:200]}), 500

    def _do_submit(olympiad_id):
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
        try:
            result = olympiad_engine.submit_exam(
                session_id, session_token, answers, fingerprint=_fp()
            )
            if isinstance(result, dict) and result.get("hideScore"):
                return jsonify(result)
            body = {"ok": True, "result": result.get("result") if isinstance(result, dict) else result}
            if isinstance(result, dict):
                for k in (
                    "score",
                    "correct",
                    "total",
                    "passScore",
                    "status",
                    "finishedAt",
                    "hideScore",
                    "pendingReview",
                    "message",
                    "showResultsToStudents",
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
            return jsonify({"error": "Хатои дохилӣ.", "reason": str(e)[:200]}), 500

    def olympiad_exam_submit(olympiad_id):
        return _do_submit(olympiad_id)

    def olympiad_submit(olympiad_id):
        return _do_submit(olympiad_id)

    # Drop existing rules so POST is not shadowed
    rules_to_drop = []
    for rule in list(app.url_map.iter_rules()):
        rule_s = str(rule)
        if rule_s in (
            "/api/olympiads/<olympiad_id>/start",
            "/api/olympiads/<olympiad_id>/exam-submit",
            "/api/olympiads/<olympiad_id>/autosave",
            "/api/olympiads/<olympiad_id>/submit",
        ):
            rules_to_drop.append(rule)
    for rule in rules_to_drop:
        try:
            app.url_map._rules.remove(rule)
            if rule.endpoint in app.url_map._rules_by_endpoint:
                app.url_map._rules_by_endpoint[rule.endpoint] = [
                    r for r in app.url_map._rules_by_endpoint[rule.endpoint] if r is not rule
                ]
            app.view_functions.pop(rule.endpoint, None)
        except Exception as e:
            log.warning("drop rule %s: %s", rule, e)

    app.add_url_rule(
        "/api/olympiads/<olympiad_id>/start",
        endpoint="oe_force_start",
        view_func=olympiad_start,
        methods=["POST"],
    )
    app.add_url_rule(
        "/api/olympiads/<olympiad_id>/autosave",
        endpoint="oe_force_autosave",
        view_func=olympiad_autosave,
        methods=["POST"],
    )
    app.add_url_rule(
        "/api/olympiads/<olympiad_id>/exam-submit",
        endpoint="oe_force_exam_submit",
        view_func=olympiad_exam_submit,
        methods=["POST"],
    )
    app.add_url_rule(
        "/api/olympiads/<olympiad_id>/submit",
        endpoint="oe_force_submit",
        view_func=olympiad_submit,
        methods=["POST"],
    )
    try:
        app.view_functions["submit_olympiad"] = olympiad_submit
    except Exception:
        pass

    print("[boot] force_olympiad_routes: POST start/exam-submit/submit/autosave bound")
    log.info("force olympiad routes installed")
