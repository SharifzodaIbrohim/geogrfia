"""Phase 8 quiz routes. Public /api/quizzes = standalone quizzes only (no olympiads)."""
from __future__ import annotations

from flask import jsonify, request

from db import quiz_api
from db import quiz_bridge
from db.rbac import deny_message
from db.repo import find_student_by_code


def _resolve_quiz(quiz_id: str, include_answers: bool = False):
    """Standalone quiz first; bridged olympiad only if explicitly requested by id."""
    quiz = quiz_api.get_quiz(quiz_id, include_answers=include_answers)
    if quiz and (not quiz.get("status") or quiz.get("status") == "published"):
        quiz["source"] = quiz.get("source") or "quiz"
        return quiz
    # Bridged for direct ID access (student portal / known links) — not for public list
    try:
        bridged = quiz_bridge.get_bridged_quiz(quiz_id, include_answers=include_answers)
        if bridged and (bridged.get("status") == "published" or bridged.get("isActive")):
            return bridged
    except Exception:
        pass
    return None


def _safe_get(app, rule: str, endpoint: str, view_func, **options):
    """Register GET or override existing endpoint without AssertionError."""
    if endpoint in app.view_functions:
        app.view_functions[endpoint] = view_func
        return
    # Check if rule already mapped under another endpoint name
    for r in app.url_map.iter_rules():
        if r.rule == rule and "GET" in (r.methods or set()):
            app.view_functions[r.endpoint] = view_func
            return
    app.add_url_rule(rule, endpoint, view_func, methods=["GET"], **options)


def _safe_post(app, rule: str, endpoint: str, view_func, **options):
    if endpoint in app.view_functions:
        app.view_functions[endpoint] = view_func
        return
    for r in app.url_map.iter_rules():
        if r.rule == rule and "POST" in (r.methods or set()):
            app.view_functions[r.endpoint] = view_func
            return
    app.add_url_rule(rule, endpoint, view_func, methods=["POST"], **options)


def _safe_delete(app, rule: str, endpoint: str, view_func, **options):
    if endpoint in app.view_functions:
        app.view_functions[endpoint] = view_func
        return
    for r in app.url_map.iter_rules():
        if r.rule == rule and "DELETE" in (r.methods or set()):
            app.view_functions[r.endpoint] = view_func
            return
    app.add_url_rule(rule, endpoint, view_func, methods=["DELETE"], **options)


def _safe_patch(app, rule: str, endpoint: str, view_func, **options):
    if endpoint in app.view_functions:
        app.view_functions[endpoint] = view_func
        return
    for r in app.url_map.iter_rules():
        if r.rule == rule and "PATCH" in (r.methods or set()):
            app.view_functions[r.endpoint] = view_func
            return
    app.add_url_rule(rule, endpoint, view_func, methods=["PATCH"], **options)


def register_quiz_routes(app, require_user, require_perm):
    def public_list_quizzes():
        # STRICT: public /quiz and /api/quizzes = standalone quizzes only
        items = quiz_api.list_quizzes(include_draft=False)
        safe = []
        for q in items:
            if q.get("source") == "olympiad":
                continue
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
        return jsonify({"quizzes": safe})

    def public_get_quiz(quiz_id: str):
        quiz = _resolve_quiz(quiz_id, include_answers=False)
        if not quiz:
            return jsonify({"error": "Викторина ёфт нашуд."}), 404
        # Strip answers if any leaked
        qs = []
        for item in (quiz.get("questions") or []):
            qs.append({
                "id": item.get("id"),
                "text": item.get("text"),
                "options": list(item.get("options") or []),
            })
        out = {
            "id": quiz.get("id"),
            "title": quiz.get("title"),
            "description": quiz.get("description"),
            "passScore": quiz.get("passScore"),
            "timeLimitSec": quiz.get("timeLimitSec"),
            "accessMode": quiz.get("accessMode") or "public",
            "schoolName": quiz.get("schoolName"),
            "questionCount": len(qs),
            "source": quiz.get("source") or "quiz",
            "questions": qs,
        }
        return jsonify({"quiz": out})

    def public_start_quiz(quiz_id: str):
        quiz = _resolve_quiz(quiz_id, include_answers=False)
        if not quiz:
            return jsonify({"error": "Викторина ёфт нашуд."}), 404
        # Block olympiad source on public quiz start — use /student
        if quiz.get("source") == "olympiad" or quiz.get("type") == "olympiad":
            return jsonify({
                "error": "Ин олимпиада аст. Ба /student бо Student ID ворид шавед.",
                "reason": "olympiad_use_student_portal",
            }), 403
        payload = request.get_json(silent=True) or {}
        student_code = (payload.get("studentId") or payload.get("student_code") or "").strip()
        student = find_student_by_code(student_code) if student_code else None
        user = None
        try:
            user = require_user()
        except Exception:
            user = None
        access = quiz_api.check_access(quiz, user if isinstance(user, dict) else None, student)
        if not access.get("allowed"):
            return jsonify({"error": "Дастрасӣ рад шуд.", "reason": access.get("reason")}), 403
        try:
            uid = (user or {}).get("id") if isinstance(user, dict) else None
            session = quiz_api.start_attempt(
                quiz_id,
                user_id=uid,
                student_id=student_code or None,
            )
            return jsonify({"session": session})
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    def public_submit_quiz(quiz_id: str):
        payload = request.get_json(silent=True) or {}
        attempt_id = payload.get("attemptId") or payload.get("sessionId")
        answers = payload.get("answers") or {}
        if not attempt_id:
            return jsonify({"error": "attemptId лозим аст."}), 400
        try:
            user = require_user()
        except Exception:
            user = None
        uid = (user or {}).get("id") if isinstance(user, dict) else None
        try:
            result = quiz_api.submit_attempt(
                quiz_id, attempt_id, answers, user_id=uid
            )
            return jsonify({"result": result})
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    def me_quiz_history():
        user = require_user()
        if not user:
            return jsonify({"error": "Логин лозим аст."}), 401
        hist = quiz_api.user_history(user.get("id") or "")
        return jsonify({"history": hist})

    def admin_list_quizzes():
        admin = require_perm("quizzes.read")
        if admin is None:
            return jsonify({"error": "Дастрасӣ рад шуд."}), 401
        if admin is False:
            return jsonify({"error": deny_message("quizzes.read")}), 403
        items = quiz_api.list_quizzes(include_draft=True)
        return jsonify({"quizzes": items})

    def admin_create_quiz():
        admin = require_perm("quizzes.write")
        if admin is None:
            return jsonify({"error": "Дастрасӣ рад шуд."}), 401
        if admin is False:
            return jsonify({"error": deny_message("quizzes.write")}), 403
        payload = request.get_json(silent=True) or {}
        title = str(payload.get("title") or "").strip()
        if not title:
            return jsonify({"error": "Унвон лозим аст."}), 400
        raw_q = payload.get("questions") or []
        if len(raw_q) < 1:
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

    def admin_delete_quiz(quiz_id: str):
        admin = require_perm("quizzes.write")
        if admin is None:
            return jsonify({"error": "Дастрасӣ рад шуд."}), 401
        if admin is False:
            return jsonify({"error": deny_message("quizzes.write")}), 403
        if not quiz_api.delete_quiz(quiz_id):
            return jsonify({"error": "Ёфт нашуд."}), 404
        return jsonify({"ok": True})

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

    _safe_get(app, "/api/quizzes", "public_list_quizzes", public_list_quizzes)
    _safe_get(app, "/api/quizzes/<quiz_id>", "public_get_quiz", public_get_quiz)
    _safe_post(app, "/api/quizzes/<quiz_id>/start", "public_start_quiz", public_start_quiz)
    _safe_post(app, "/api/quizzes/<quiz_id>/submit", "public_submit_quiz", public_submit_quiz)
    _safe_get(app, "/api/me/quiz-history", "me_quiz_history", me_quiz_history)
    _safe_get(app, "/api/admin/quizzes", "admin_list_quizzes", admin_list_quizzes)
    _safe_post(app, "/api/admin/quizzes", "admin_create_quiz", admin_create_quiz)
    _safe_delete(app, "/api/admin/quizzes/<quiz_id>", "admin_delete_quiz", admin_delete_quiz)
    _safe_patch(app, "/api/admin/quizzes/<quiz_id>", "admin_patch_quiz", admin_patch_quiz)
