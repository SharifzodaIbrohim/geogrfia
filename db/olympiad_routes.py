"""Phase 9–12 — Olympiad exam routes."""
from __future__ import annotations

from flask import jsonify, request

from db import olympiad_engine
from db.repo import find_olympiad
from db.student_access import student_has_olympiad_access
from db import repo


def register_olympiad_engine_routes(app, require_user, olympiad_window_status):
    @app.post("/api/olympiads/<olympiad_id>/start")
    def olympiad_start(olympiad_id: str):
        payload = request.get_json(silent=True) or {}
        student_id = str(payload.get("studentId") or request.headers.get("X-Student-Id") or "").strip()
        if not student_id:
            return jsonify({"error": "studentId лозим аст."}), 400

        olympiad = find_olympiad(olympiad_id)
        if not olympiad:
            return jsonify({"error": "Олимпиада ёфт нашуд."}), 404

        window = olympiad_window_status(olympiad)
        if window != "open":
            msgs = {
                "inactive": "Олимпиада фаъол нест.",
                "not_started": "Ҳанӯз оғоз нашудааст.",
                "ended": "Вақт ба охир расид.",
            }
            return jsonify({"error": msgs.get(window, window), "windowStatus": window}), 403

        user = require_user()
        # Optional: require Google if linked policy later
        fp = request.headers.get("X-Client-Fingerprint", "")[:64]

        try:
            session = olympiad_engine.start_exam(
                olympiad_id,
                student_id,
                user_id=user["id"] if user else None,
                client_fingerprint=fp or None,
            )
        except ValueError as e:
            code = str(e)
            messages = {
                "rate_limited": "Зиёд дархост — каме интизор шавед.",
                "already_submitted": "Шумо аллакай супоридаед (як маротиба).",
                "not_assigned": "Шумо ба ин олимпиада таъин нашудаед.",
                "student_not_found": "ID нодуруст аст.",
                "no_questions": "Саволҳо нестанд.",
                "not_found": "Олимпиада ёфт нашуд.",
            }
            return jsonify({"error": messages.get(code, code), "reason": code}), 403 if code != "not_found" else 404

        return jsonify(session)

    @app.post("/api/olympiads/<olympiad_id>/autosave")
    def olympiad_autosave(olympiad_id: str):
        payload = request.get_json(silent=True) or {}
        session_id = str(payload.get("sessionId") or "").strip()
        session_token = str(payload.get("sessionToken") or "").strip()
        answers = payload.get("answers") or {}
        fp = request.headers.get("X-Client-Fingerprint", "")[:64]
        if not session_id or not session_token:
            return jsonify({"error": "sessionId ва sessionToken лозиманд."}), 400
        try:
            result = olympiad_engine.autosave(
                session_id, session_token, answers, fingerprint=fp or None
            )
        except ValueError as e:
            code = str(e)
            return jsonify({"error": code}), 400
        return jsonify(result)

    @app.post("/api/olympiads/<olympiad_id>/exam-submit")
    def olympiad_exam_submit(olympiad_id: str):
        payload = request.get_json(silent=True) or {}
        session_id = str(payload.get("sessionId") or "").strip()
        session_token = str(payload.get("sessionToken") or "").strip()
        answers = payload.get("answers")
        fp = request.headers.get("X-Client-Fingerprint", "")[:64]
        if not session_id or not session_token:
            return jsonify({"error": "sessionId ва sessionToken лозиманд."}), 400
        try:
            result = olympiad_engine.submit_exam(
                session_id,
                session_token,
                answers if isinstance(answers, dict) else None,
                fingerprint=fp or None,
            )
        except ValueError as e:
            code = str(e)
            messages = {
                "rate_limited": "Зиёд дархост.",
                "invalid_session": "Сессия нодуруст аст.",
                "already_submitted": "Аллакай супорида шудааст.",
                "not_found": "Ёфт нашуд.",
            }
            return jsonify({"error": messages.get(code, code)}), 400
        return jsonify({"result": result})

    @app.patch("/api/admin/olympiads/<olympiad_id>/duration")
    def admin_set_duration(olympiad_id: str):
        # lightweight: store durationSec via update_olympiad if supported
        token = request.headers.get("X-Admin-Token", "")
        from db.auth_tokens import admin_from_token
        from db.admin_role import enrich_admin
        from db.rbac import admin_can, deny_message

        admin = enrich_admin(admin_from_token(token))
        if not admin:
            return jsonify({"error": "Дастрасӣ рад шуд."}), 401
        if not admin_can(admin, "olympiads.write"):
            return jsonify({"error": deny_message("olympiads.write")}), 403
        payload = request.get_json(silent=True) or {}
        try:
            duration = int(payload.get("durationSec"))
        except (TypeError, ValueError):
            return jsonify({"error": "durationSec рақам бошад."}), 400
        if duration < 60 or duration > 86400:
            return jsonify({"error": "durationSec: 60–86400."}), 400
        # JSON/PG patch: use update if field exists; else store in memory via olympiad update title no-op
        olympiad = repo.update_olympiad(olympiad_id, {})
        if not olympiad:
            return jsonify({"error": "Ёфт нашуд."}), 404
        # attach duration on JSON file manually
        if not repo.use_pg():
            items = repo._load_json(repo.OLYMPIADS_FILE)
            for o in items:
                if o.get("id") == olympiad_id:
                    o["durationSec"] = duration
                    repo._save_json(repo.OLYMPIADS_FILE, items)
                    olympiad = o
                    break
        else:
            # column may not exist — try alter + update
            try:
                from db.connection import get_session
                from sqlalchemy import text

                with get_session() as s:
                    s.execute(text(
                        "ALTER TABLE olympiads ADD COLUMN IF NOT EXISTS duration_sec INT"
                    ))
                    s.execute(
                        text("UPDATE olympiads SET duration_sec = :d WHERE id::text = :id"),
                        {"d": duration, "id": olympiad_id},
                    )
            except Exception as e:
                return jsonify({"error": f"DB: {e}"}), 500
            olympiad = find_olympiad(olympiad_id)
        return jsonify({"ok": True, "durationSec": duration, "olympiadId": olympiad_id})
