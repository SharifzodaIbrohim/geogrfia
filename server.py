"""Geografia server entry — loads stable core then profile/content/i18n assets."""
from __future__ import annotations

import urllib.request

from flask import send_from_directory

_url = (
    "https://raw.githubusercontent.com/SharifzodaIbrohim/geogrfia/"
    "12d743039abdc42c572a1f09d9d7f71572ee9035/server.py"
)
_src = urllib.request.urlopen(_url, timeout=90).read()
exec(compile(_src, "server_12d7430.py", "exec"), globals())

try:
    PUBLIC_PATHS.update({
        "profile.html",
        "courses.html",
        "css/profile.css",
        "js/profile.js",
        "js/admin-gmail.js",
        "js/i18n.js",
        "js/admin-content.js",
    })
except Exception:
    pass

try:
    from db.profile_routes import register_profile_routes
    register_profile_routes(app, _jwt_require_user, require_perm, require_admin)
except Exception:
    try:
        register_profile_routes(app, require_user, require_perm, require_admin)
    except Exception:
        pass

try:
    from db.content_routes import register_content_routes
    register_content_routes(app, require_perm, require_admin)
except Exception:
    pass

@app.route("/profile")
@app.route("/profile.html")
@app.route("/Profile")
def _profile_page():
    return send_from_directory(BASE_DIR, "profile.html")

@app.route("/courses")
@app.route("/courses.html")
def _courses_page():
    return send_from_directory(BASE_DIR, "courses.html")

try:
    @app.route("/books/<path:filename>")
    def _books(filename):
        return send_from_directory(BASE_DIR / "books", filename)
except Exception:
    pass

# Gmail open-quiz access (no recursion)
try:
    from db import student_access as _sa
    from db import quiz_bridge as _qb
    _orig_access = _sa.student_has_olympiad_access
    _orig_as_quiz = _qb.olympiad_as_quiz

    def _gmail_access(olympiad_id, student_code):
        student = None
        try:
            from db.repo import find_student_by_code
            student = find_student_by_code(student_code)
        except Exception:
            pass
        parts = _sa.list_olympiad_participants(olympiad_id)
        if not student and student_code and str(student_code).startswith(("g:", "gmail:")):
            if parts:
                return {"allowed": False, "reason": "not_assigned"}
            return {
                "allowed": True,
                "reason": "gmail_open",
                "student": {"id": student_code, "fullName": "Gmail user", "className": "", "school": ""},
            }
        return _orig_access(olympiad_id, student_code)

    def _olympiad_as_quiz_google(o):
        item = _orig_as_quiz(o)
        item["accessMode"] = "google"
        return item

    _sa.student_has_olympiad_access = _gmail_access
    _qb.olympiad_as_quiz = _olympiad_as_quiz_google
except Exception:
    pass

try:
    from flask import jsonify, request as _req
    from db import olympiad_engine as _oe
    from db import quiz_api as _qa
    from db.repo import find_student_by_code as _fsc

    def _patched_quiz_start(quiz_id: str):
        from db.quiz_routes import _resolve_quiz
        quiz = _resolve_quiz(quiz_id, include_answers=False)
        if not quiz:
            return jsonify({"error": "Викторина ёфт нашуд."}), 404
        try:
            user = require_user()
        except Exception:
            user = _jwt_require_user()
        payload = _req.get_json(silent=True) or {}
        student_code = str(
            payload.get("studentId") or _req.headers.get("X-Student-Id") or ""
        ).strip() or None
        student = _fsc(student_code) if student_code else None
        if user and not student:
            student = _sa.find_student_by_user_id(user["id"])
            if student:
                student_code = student.get("id")
        fp = (_req.headers.get("X-Client-Fingerprint") or "")[:64]
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
                session = _oe.start_exam(
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
                "attemptId": session.get("sessionId") or session.get("id"),
                "sessionId": session.get("sessionId") or session.get("id"),
                "sessionToken": session.get("sessionToken"),
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
        access = _qa.check_access(quiz, user, student)
        if not access.get("allowed"):
            return jsonify({"error": "Дастрасӣ рад шуд.", "reason": access.get("reason")}), 403
        try:
            attempt = _qa.start_attempt(
                quiz_id,
                user_id=user["id"] if user else None,
                student_id=student_code,
            )
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        attempt["source"] = "quiz"
        return jsonify(attempt)

    app.view_functions["quiz_start"] = _patched_quiz_start
except Exception:
    pass
