"""Phase 8 quiz routes.
/api/quizzes = standalone quizzes + olympiad type=quiz only.
type=olympiad never listed; start requires Student ID for school/olympiad modes.
"""
from __future__ import annotations

import logging

from flask import jsonify, request

from db import quiz_api
from db import quiz_bridge
from db.rbac import deny_message
from db.repo import find_student_by_code, find_olympiad, list_olympiads

log = logging.getLogger("geografia.quiz_routes")


def _resolve_quiz(quiz_id: str, include_answers: bool = False):
    quiz = quiz_api.get_quiz(quiz_id, include_answers=include_answers)
    if quiz and (not quiz.get("status") or quiz.get("status") == "published"):
        quiz["source"] = quiz.get("source") or "quiz"
        return quiz
    # Olympiad row (type=quiz or type=olympiad) by id
    try:
        oly = find_olympiad(quiz_id)
        if oly and oly.get("isActive"):
            qs = oly.get("questions") or []
            if not include_answers:
                qs = [
                    {"id": q.get("id"), "text": q.get("text"), "options": list(q.get("options") or [])}
                    for q in qs
                ]
            return {
                "id": oly["id"],
                "title": oly.get("title"),
                "description": oly.get("description") or "",
                "passScore": oly.get("passScore") or 70,
                "timeLimitSec": oly.get("durationSec"),
                "accessMode": "school",
                "status": "published",
                "questions": qs,
                "questionCount": len(oly.get("questions") or []),
                "source": "olympiad",
                "type": (oly.get("type") or "olympiad").lower(),
                "isActive": True,
            }
    except Exception as e:
        log.warning("resolve olympiad: %s", e)
    try:
        bridged = quiz_bridge.get_bridged_quiz(quiz_id, include_answers=include_answers)
        if bridged and (bridged.get("status") == "published" or bridged.get("isActive")):
            return bridged
    except Exception:
        pass
    return None


def _ensure_rule(app, rule: str, endpoint: str, view_func, methods):
    app.view_functions[endpoint] = view_func
    found = False
    for r in list(app.url_map.iter_rules()):
        if r.rule == rule and set(methods) & (r.methods or set()):
            app.view_functions[r.endpoint] = view_func
            found = True
    if not found:
        try:
            app.add_url_rule(rule, endpoint, view_func, methods=methods)
        except AssertionError:
            app.view_functions[endpoint] = view_func


def register_quiz_routes(app, require_user, require_perm):
    def public_list_quizzes():
        safe = []
        seen = set()
        try:
            items = quiz_api.list_quizzes(include_draft=False)
        except Exception:
            items = []
        for q in items:
            if q.get("source") == "olympiad":
                continue
            qid = q.get("id")
            if not qid or qid in seen:
                continue
            seen.add(qid)
            safe.append({
                "id": qid,
                "title": q.get("title"),
                "description": q.get("description"),
                "passScore": q.get("passScore"),
                "timeLimitSec": q.get("timeLimitSec"),
                "accessMode": q.get("accessMode") or "public",
                "schoolName": q.get("schoolName"),
                "questionCount": q.get("questionCount") or 0,
                "source": "quiz",
            })
        # Admin "Викторина" stored as olympiad type=quiz
        try:
            for o in list_olympiads():
                if (o.get("type") or "olympiad").lower() != "quiz":
                    continue
                if not o.get("isActive"):
                    continue
                oid = o.get("id")
                if not oid or oid in seen:
                    continue
                seen.add(oid)
                safe.append({
                    "id": oid,
                    "title": o.get("title"),
                    "description": o.get("description") or "",
                    "passScore": o.get("passScore") or 70,
                    "timeLimitSec": o.get("durationSec"),
                    "accessMode": "school",
                    "schoolName": None,
                    "questionCount": o.get("questionCount") or 0,
                    "source": "quiz",
                    "eventKind": "olympiad_quiz",
                })
        except Exception as e:
            log.warning("list type=quiz olympiads: %s", e)
        return jsonify({"quizzes": safe})

    def public_get_quiz(quiz_id: str):
        quiz = _resolve_quiz(quiz_id, include_answers=False)
        if not quiz:
            return jsonify({"error": "Викторина ёфт нашуд."}), 404
        # Pure olympiad must not be opened from /quiz
        if quiz.get("type") == "olympiad" and quiz.get("source") == "olympiad":
            return jsonify({
                "error": "Ин олимпиада аст. Ба /student бо Student ID ворид шавед.",
                "reason": "olympiad_use_student_portal",
            }), 403
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
            "type": quiz.get("type") or "quiz",
            "questions": qs,
        }
        return jsonify({"quiz": out})

    def public_start_quiz(quiz_id: str):
        quiz = _resolve_quiz(quiz_id, include_answers=False)
        if not quiz:
            return jsonify({"error": "Викторина ёфт нашуд."}), 404

        # Pure olympiad → student portal only
        if (quiz.get("type") or "").lower() == "olympiad":
            return jsonify({
                "error": "Ин олимпиада аст. Ба /student бо Student ID ворид шавед.",
                "reason": "olympiad_use_student_portal",
            }), 403

        payload = request.get_json(silent=True) or {}
        student_code = (
            payload.get("studentId") or payload.get("student_code") or ""
        ).strip()

        # type=quiz stored in olympiads table → use olympiad engine + Student ID
        if quiz.get("source") == "olympiad" or quiz.get("eventKind") == "olympiad_quiz":
            if not student_code:
                return jsonify({
                    "error": "Барои иштирок Student ID лозим аст.",
                    "reason": "student_id_required",
                }), 400
            try:
                from db import olympiad_engine
                user = None
                try:
                    user = require_user()
                except Exception:
                    user = None
                uid = (user or {}).get("id") if isinstance(user, dict) else None
                session = olympiad_engine.start_exam(
                    quiz_id, student_code, user_id=uid
                )
                return jsonify({"session": session})
            except ValueError as e:
                code = str(e)
                messages = {
                    "student_not_found": "ID нодуруст аст.",
                    "already_submitted": "Шумо аллакай супоридаед (як маротиба).",
                    "not_assigned": "Шумо ба ин викторина таъин нашудаед.",
                    "no_questions": "Саволҳо нестанд.",
                    "not_found": "Ёфт нашуд.",
                }
                return jsonify({"error": messages.get(code, code), "reason": code}), 403
            except Exception as e:
                log.exception("quiz start via olympiad engine")
                return jsonify({"error": "Хатои дохилӣ.", "reason": str(e)[:200]}), 500

        student = find_student_by_code(student_code) if student_code else None
        user = None
        try:
            user = require_user()
        except Exception:
            user = None
        access = quiz_api.check_access(
            quiz, user if isinstance(user, dict) else None, student
        )
        if not access.get("allowed"):
            return jsonify({"error": "Дастрасӣ рад шуд.", "reason": access.get("reason")}), 403
        try:
            uid = (user or {}).get("id") if isinstance(user, dict) else None
            session = quiz_api.start_attempt(
                quiz_id, user_id=uid, student_id=student_code or None
            )
            return jsonify({"session": session})
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            log.exception("quiz start")
            return jsonify({"error": str(e)}), 500

    def public_submit_quiz(quiz_id: str):
        payload = request.get_json(silent=True) or {}
        attempt_id = payload.get("attemptId") or payload.get("sessionId")
        session_token = payload.get("sessionToken") or ""
        answers = payload.get("answers") or {}
        if not attempt_id:
            return jsonify({"error": "attemptId лозим аст."}), 400

        # If this id is an olympiad (type=quiz), submit via engine
        oly = None
        try:
            oly = find_olympiad(quiz_id)
        except Exception:
            pass
        if oly:
            if not session_token:
                return jsonify({"error": "sessionToken лозим аст."}), 400
            try:
                from db import olympiad_engine
                result = olympiad_engine.submit_exam(
                    attempt_id, session_token,
                    answers if isinstance(answers, dict) else None,
                )
                return jsonify({"result": result})
            except ValueError as e:
                return jsonify({"error": str(e), "reason": str(e)}), 400
            except Exception as e:
                log.exception("quiz submit via olympiad engine")
                return jsonify({"error": "Хатои дохилӣ.", "reason": str(e)[:200]}), 500

        try:
            user = require_user()
        except Exception:
            user = None
        uid = (user or {}).get("id") if isinstance(user, dict) else None
        try:
            result = quiz_api.submit_attempt(quiz_id, attempt_id, answers, user_id=uid)
            return jsonify({"result": result})
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            log.exception("quiz submit")
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

    _ensure_rule(app, "/api/quizzes", "public_list_quizzes", public_list_quizzes, ["GET"])
    _ensure_rule(app, "/api/quizzes/<quiz_id>", "public_get_quiz", public_get_quiz, ["GET"])
    _ensure_rule(app, "/api/quizzes/<quiz_id>/start", "public_start_quiz", public_start_quiz, ["POST"])
    _ensure_rule(app, "/api/quizzes/<quiz_id>/submit", "public_submit_quiz", public_submit_quiz, ["POST"])
    _ensure_rule(app, "/api/me/quiz-history", "me_quiz_history", me_quiz_history, ["GET"])
    _ensure_rule(app, "/api/admin/quizzes", "admin_list_quizzes", admin_list_quizzes, ["GET"])
    _ensure_rule(app, "/api/admin/quizzes", "admin_create_quiz", admin_create_quiz, ["POST"])
    _ensure_rule(app, "/api/admin/quizzes/<quiz_id>", "admin_delete_quiz", admin_delete_quiz, ["DELETE"])
    _ensure_rule(app, "/api/admin/quizzes/<quiz_id>", "admin_patch_quiz", admin_patch_quiz, ["PATCH"])
