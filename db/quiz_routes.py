"""Phase 8 quiz routes + bridge to olympiad type=quiz."""
from __future__ import annotations

from flask import jsonify, request

from db import quiz_api
from db import quiz_bridge
from db import student_access
from db import olympiad_engine
from db.rbac import deny_message
from db.repo import find_student_by_code


def _resolve_quiz(quiz_id: str, include_answers: bool = False):
    quiz = quiz_api.get_quiz(quiz_id, include_answers=include_answers)
    if quiz and (not quiz.get("status") or quiz.get("status") == "published"):
        quiz["source"] = quiz.get("source") or "quiz"
        return quiz
    bridged = quiz_bridge.get_bridged_quiz(quiz_id, include_answers=include_answers)
    if bridged and (bridged.get("status") == "published" or bridged.get("isActive")):
        return bridged
    return None


def register_quiz_routes(app, require_user, require_perm):
    @app.get("/api/quizzes")
    def public_list_quizzes():
        items = quiz_api.list_quizzes(include_draft=False)
        safe = []
        seen = set()
        for q in items:
            seen.add(q["id"])
            safe.append({
                "id": q["id"],
                "title": q.get("title"),
                "description": q.get("description"),
                "passScore": q.get("passScore"),
                "timeLimitSec": q.get("timeLimitSec"),
                "accessMode": q.get("accessMode") or "public",
                "schoolName": q.get("schoolName"),
                "questionCount": q.get("questionCount") or 0,
                "source": "quiz",
            })
        for q in quiz_bridge.list_bridged_quizzes(include_inactive=False):
            if q["id"] in seen:
                continue
            safe.append({
                "id": q["id"],
                "title": q.get("title"),
                "description": q.get("description"),
                "passScore": q.get("passScore"),
                "timeLimitSec": q.get("timeLimitSec"),
                "accessMode": q.get("accessMode") or "google",
                "schoolName": q.get("schoolName"),
                "questionCount": q.get("questionCount") or 0,
                "source": "olympiad",
                "windowStatus": q.get("windowStatus"),
            })
        return jsonify({"quizzes": safe})

    @app.get("/api/quizzes/<quiz_id>")
    def public_get_quiz(quiz_id: str):
        quiz = _resolve_quiz(quiz_id, include_answers=False)
        if not quiz:
            return jsonify({"error": "Викторина ёфт нашуд."}), 404
        user = require_user()
        student = None
        student_id = request.headers.get("X-Student-Id", "").strip()
        if student_id:
            student = find_student_by_code(student_id)
        if user and not student:
            student = student_access.find_student_by_user_id(user["id"])
        if quiz.get("source") == "olympiad":
            code = (student or {}).get("id") if student else None
            if not code and user:
                code = "g:" + str(user["id"])[:40]
            if not code:
                return jsonify({
                    "error": "Аввал бо Google ворид шавед ё Student ID ворид кунед.",
                    "reason": "google_or_student_required",
                }), 403
            access = student_access.student_has_olympiad_access(quiz_id, code)
            if not access.get("allowed"):
                return jsonify({"error": "Дастрасӣ рад шуд.", "reason": access.get("reason")}), 403
        else:
            access = quiz_api.check_access(quiz, user, student)
            if not access.get("allowed"):
                return jsonify({"error": "Дастрасӣ рад шуд.", "reason": access.get("reason")}), 403
        return jsonify({
            "quiz": {
                "id": quiz["id"],
                "title": quiz.get("title"),
                "description": quiz.get("description"),
                "passScore": quiz.get("passScore"),
                "timeLimitSec": quiz.get("timeLimitSec"),
                "accessMode": quiz.get("accessMode"),
                "questionCount": quiz.get("questionCount"),
                "source": quiz.get("source"),
                "questions": quiz.get("questions") or [],
            }
        })

    @app.post("/api/quizzes/<quiz_id>/start")
    def quiz_start(quiz_id: str):
        quiz = _resolve_quiz(quiz_id, include_answers=False)
        if not quiz:
            return jsonify({"error": "Викторина ёфт нашуд."}), 404
        user = require_user()
        payload = request.get_json(silent=True) or {}
        student_code = str(
            payload.get("studentId") or request.headers.get("X-Student-Id") or ""
        ).strip() or None
        student = find_student_by_code(student_code) if student_code else None
        if user and not student:
            student = student_access.find_student_by_user_id(user["id"])
            if student:
                student_code = student.get("id")

        fp = request.headers.get("X-Client-Fingerprint", "")[:64]

        if quiz.get("source") == "olympiad":
            if not student_code:
                if user and user.get("id"):
                    student_code = "g:" + str(user["id"])[:40]
                else:
                    return jsonify({
                        "error": "Аввал бо Google ворид шавед ё Student ID ворид кунед.",
                        "reason": "google_or_student_required",
                    }), 403
            try:
                session = olympiad_engine.start_exam(
                    quiz_id,
                    student_code,
                    user_id=user["id"] if user else None,
                    client_fingerprint=fp or None,
                )
            except ValueError as e:
                code = str(e)
                msgs = {
                    "rate_limited": "Зиёд дархост.",
                    "already_submitted": "Аллакай супоридаед.",
                    "not_assigned": "Ба ин викторина таъин нашудаед.",
                    "student_not_found": "ID нодуруст.",
                    "not_found": "Ёфт нашуд.",
                }
                return jsonify({"error": msgs.get(code, code), "reason": code}), 403
            return jsonify({
                "attemptId": session["sessionId"],
                "sessionId": session["sessionId"],
                "sessionToken": session["sessionToken"],
                "quizId": quiz_id,
                "title": session.get("title"),
                "startedAt": session.get("startedAt"),
                "endsAt": session.get("endsAt"),
                "timeLimitSec": quiz.get("timeLimitSec"),
                "questionCount": session.get("questionCount"),
                "questions": session.get("questions") or [],
                "passScore": session.get("passScore"),
                "source": "olympiad",
            })

        access = quiz_api.check_access(quiz, user, student)
        if not access.get("allowed"):
            return jsonify({"error": "Дастрасӣ рад шуд.", "reason": access.get("reason")}), 403
        try:
            attempt = quiz_api.start_attempt(
                quiz_id,
                user_id=user["id"] if user else None,
                student_id=student_code,
            )
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        attempt["source"] = "quiz"
        return jsonify(attempt)

    @app.post("/api/quizzes/<quiz_id>/submit")
    def quiz_submit(quiz_id: str):
        payload = request.get_json(silent=True) or {}
        attempt_id = str(payload.get("attemptId") or payload.get("sessionId") or "").strip()
        session_token = str(payload.get("sessionToken") or "").strip()
        answers = payload.get("answers") or []
        if not attempt_id:
            return jsonify({"error": "attemptId лозим аст."}), 400

        quiz = _resolve_quiz(quiz_id, include_answers=False)
        fp = request.headers.get("X-Client-Fingerprint", "")[:64]

        if quiz and quiz.get("source") == "olympiad":
            if not session_token:
                return jsonify({"error": "sessionToken лозим аст."}), 400
            ans_map = {}
            if isinstance(answers, dict):
                ans_map = answers
            elif isinstance(answers, list):
                for i, a in enumerate(answers):
                    if isinstance(a, dict):
                        key = a.get("originalIndex", a.get("questionId", i))
                        sel = a.get("selected")
                        if sel is not None:
                            ans_map[str(key)] = sel
                    else:
                        try:
                            ans_map[str(i)] = int(a)
                        except (TypeError, ValueError):
                            pass
            try:
                result = olympiad_engine.submit_exam(
                    attempt_id,
                    session_token,
                    ans_map,
                    fingerprint=fp or None,
                )
            except ValueError as e:
                return jsonify({"error": str(e)}), 400
            return jsonify({"result": result})

        user = require_user()
        try:
            result = quiz_api.submit_attempt(
                quiz_id,
                attempt_id,
                answers,
                user_id=user["id"] if user else None,
            )
        except ValueError as e:
            code = str(e)
            status = 404 if "not_found" in code else 400
            return jsonify({"error": code}), status
        return jsonify({"result": result})

    @app.get("/api/me/quiz-history")
    def quiz_history():
        user = require_user()
        if not user:
            return jsonify({"error": "Аввал бо Google ворид шавед."}), 401
        return jsonify({"history": quiz_api.user_history(user["id"])})

    @app.get("/api/admin/quizzes")
    def admin_list_quizzes():
        admin = require_perm("quizzes.read", "quizzes.write")
        if admin is None:
            return jsonify({"error": "Дастрасӣ рад шуд."}), 401
        if admin is False:
            return jsonify({"error": deny_message("quizzes.read")}), 403
        items = quiz_api.list_quizzes(include_draft=True)
        bridged = quiz_bridge.list_bridged_quizzes(include_inactive=True)
        return jsonify({"quizzes": items, "fromOlympiads": bridged})

    @app.post("/api/admin/quizzes")
    def admin_create_quiz():
        admin = require_perm("quizzes.write")
        if admin is None:
            return jsonify({"error": "Дастрасӣ рад шуд."}), 401
        if admin is False:
            return jsonify({"error": deny_message("quizzes.write")}), 403
        payload = request.get_json(silent=True) or {}
        title = str(payload.get("title", "")).strip()
        raw_q = payload.get("questions") or []
        if not title:
            return jsonify({"error": "Унвон лозим аст."}), 400
        if not isinstance(raw_q, list) or len(raw_q) < 1:
            return jsonify({"error": "Камаш 1 савол лозим аст."}), 400
        questions = []
        for i, q in enumerate(raw_q):
            text = str(q.get("text", "")).strip()
            options = [str(o).strip() for o in (q.get("options") or []) if str(o).strip()]
            try:
                answer = int(q.get("answer", 0))
            except (TypeError, ValueError):
                answer = 0
            if not text or len(options) < 2:
                return jsonify({"error": f"Саволи {i+1} нодуруст аст."}), 400
            questions.append({"text": text, "options": options, "answer": answer})
        try:
            time_limit = payload.get("timeLimitSec")
            time_limit = int(time_limit) if time_limit not in (None, "") else None
        except (TypeError, ValueError):
            time_limit = None
        quiz = quiz_api.create_quiz({
            "title": title,
            "description": str(payload.get("description") or ""),
            "passScore": int(payload.get("passScore") or 70),
            "timeLimitSec": time_limit,
            "accessMode": payload.get("accessMode") or "public",
            "schoolName": payload.get("schoolName") or None,
            "status": payload.get("status") or "published",
            "questions": questions,
        })
        return jsonify({"quiz": quiz}), 201

    @app.delete("/api/admin/quizzes/<quiz_id>")
    def admin_delete_quiz(quiz_id: str):
        admin = require_perm("quizzes.write")
        if admin is None:
            return jsonify({"error": "Дастрасӣ рад шуд."}), 401
        if admin is False:
            return jsonify({"error": deny_message("quizzes.write")}), 403
        if not quiz_api.delete_quiz(quiz_id):
            return jsonify({"error": "Ёфт нашуд."}), 404
        return jsonify({"ok": True})

    @app.patch("/api/admin/quizzes/<quiz_id>")
    def admin_patch_quiz(quiz_id: str):
        admin = require_perm("quizzes.write")
        if admin is None:
            return jsonify({"error": "Дастрасӣ рад шуд."}), 401
        if admin is False:
            return jsonify({"error": deny_message("quizzes.write")}), 403
        payload = request.get_json(silent=True) or {}
        if "status" in payload:
            quiz = quiz_api.set_quiz_status(quiz_id, str(payload["status"]))
            if not quiz:
                return jsonify({"error": "Ёфт нашуд."}), 404
            return jsonify({"quiz": quiz})
        return jsonify({"error": "Ҳеҷ тағйир нест."}), 400
