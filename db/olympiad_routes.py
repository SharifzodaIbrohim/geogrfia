"""Phase 9–12 — Olympiad exam routes (no uncaught 500).

P1.12 fix: /api/olympiads/<id>/submit must close the attempt in `attempts`
(status passed|failed|timeout) — legacy submit only wrote client result and
left attempts.in_progress, so resume still worked after "submit".
"""
from __future__ import annotations

import logging

from flask import jsonify, request

from db import olympiad_engine
from db.repo import find_olympiad

log = logging.getLogger("geografia.olympiad_routes")


def _student_id_from_request(payload: dict) -> str:
    return str(
        payload.get("studentId")
        or payload.get("id")
        or request.headers.get("X-Student-Id")
        or ""
    ).strip()


def _fp() -> str | None:
    v = request.headers.get("X-Client-Fingerprint", "")[:64]
    return v or None


def register_olympiad_engine_routes(app, require_user, olympiad_window_status):
    @app.post("/api/olympiads/<olympiad_id>/start")
    def olympiad_start(olympiad_id: str):
        payload = request.get_json(silent=True) or {}
        student_id = _student_id_from_request(payload)
        if not student_id:
            return jsonify({"error": "studentId лозим аст.", "reason": "student_id_required"}), 400

        olympiad = find_olympiad(olympiad_id)
        if not olympiad:
            return jsonify({"error": "Олимпиада ёфт нашуд."}), 404

        try:
            window = olympiad_window_status(olympiad)
        except Exception as e:
            log.warning("window status: %s", e)
            window = "open" if olympiad.get("isActive") else "inactive"

        if window != "open":
            msgs = {
                "inactive": "Олимпиада фаъол нест.",
                "not_started": "Ҳанӯз оғоз нашудааст.",
                "ended": "Вақт ба охир расид.",
            }
            return jsonify({"error": msgs.get(window, window), "windowStatus": window}), 403

        user = None
        try:
            user = require_user()
        except Exception:
            user = None

        try:
            session = olympiad_engine.start_exam(
                olympiad_id,
                student_id,
                user_id=(user or {}).get("id") if isinstance(user, dict) else None,
                client_fingerprint=_fp(),
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
                "session_save_failed": "Сессия захира нашуд — бори дигар кӯшиш кунед.",
            }
            status = 404 if code == "not_found" else 403
            return jsonify({"error": messages.get(code, code), "reason": code}), status
        except Exception as e:
            log.exception("olympiad start failed")
            return jsonify({"error": "Хатои дохилӣ.", "reason": str(e)[:200]}), 500

    @app.post("/api/olympiads/<olympiad_id>/autosave")
    def olympiad_autosave(olympiad_id: str):
        payload = request.get_json(silent=True) or {}
        session_id = str(payload.get("sessionId") or payload.get("attemptId") or "").strip()
        session_token = str(payload.get("sessionToken") or "").strip()
        answers = payload.get("answers") or {}
        if not session_id or not session_token:
            return jsonify({"error": "sessionId ва sessionToken лозиманд."}), 400
        try:
            result = olympiad_engine.autosave(
                session_id, session_token, answers, fingerprint=_fp()
            )
            return jsonify(result)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            log.exception("autosave failed")
            return jsonify({"error": "Хатои дохилӣ.", "reason": str(e)[:200]}), 500

    def _do_submit(olympiad_id: str):
        """Shared submit: always closes attempt via olympiad_engine.submit_exam."""
        payload = request.get_json(silent=True) or {}
        session_id = str(
            payload.get("sessionId") or payload.get("attemptId") or ""
        ).strip()
        session_token = str(payload.get("sessionToken") or "").strip()
        student_id = _student_id_from_request(payload)
        answers = payload.get("answers")

        # Normalize list answers → dict
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

        # Resolve session if token missing (legacy clients / test client)
        if not session_id or not session_token:
            resolved = olympiad_engine.resolve_session_for_submit(
                olympiad_id,
                student_code=student_id or None,
                session_id=session_id or None,
            )
            if not resolved:
                return jsonify({
                    "error": "Сессия ёфт нашуд. Аввал start кунед.",
                    "reason": "session_not_found",
                }), 400
            session_id = resolved["sessionId"]
            session_token = resolved["sessionToken"]

        try:
            result = olympiad_engine.submit_exam(
                session_id,
                session_token,
                answers,
                fingerprint=_fp(),
            )
            body = {
                "ok": True,
                "result": result.get("result") or {
                    "score": result.get("score"),
                    "correct": result.get("correct"),
                    "total": result.get("total"),
                    "passScore": result.get("passScore"),
                    "status": result.get("status"),
                    "finishedAt": result.get("finishedAt"),
                },
            }
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
            log.exception("exam submit failed")
            return jsonify({"error": "Хатои дохилӣ.", "reason": str(e)[:200]}), 500

    @app.post("/api/olympiads/<olympiad_id>/exam-submit")
    def olympiad_exam_submit(olympiad_id: str):
        return _do_submit(olympiad_id)

    @app.post("/api/olympiads/<olympiad_id>/submit")
    def olympiad_submit(olympiad_id: str):
        """Primary submit path — closes attempts row (P1.12)."""
        return _do_submit(olympiad_id)

    # Override any earlier legacy endpoint with the same rule/name
    try:
        app.view_functions["submit_olympiad"] = olympiad_submit
    except Exception as e:
        log.warning("could not override submit_olympiad: %s", e)

    @app.patch("/api/admin/olympiads/<olympiad_id>/duration")
    def admin_set_duration(olympiad_id: str):
        from db.auth_tokens import admin_from_token
        from db.admin_role import enrich_admin
        from db.rbac import admin_can, deny_message
        from db.repo import update_olympiad

        token = request.headers.get("X-Admin-Token") or ""
        admin = enrich_admin(admin_from_token(token))
        if not admin:
            return jsonify({"error": "Дастрасӣ рад шуд."}), 401
        if not admin_can(admin, "olympiads.write"):
            return jsonify({"error": deny_message("olympiads.write")}), 403
        payload = request.get_json(silent=True) or {}
        try:
            duration = int(payload.get("durationSec") or 0) or None
        except (TypeError, ValueError):
            return jsonify({"error": "durationSec нодуруст."}), 400
        oly = update_olympiad(olympiad_id, {"durationSec": duration})
        if not oly:
            return jsonify({"error": "Ёфт нашуд."}), 404
        return jsonify({"olympiad": oly})
