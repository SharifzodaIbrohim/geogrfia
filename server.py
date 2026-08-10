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

# ---- Hard fallback for /api/content (always available) ----
try:
    from flask import jsonify as _jfy, request as _rq_c
    import uuid as _uuid
    from datetime import datetime, timezone as _tz
    from pathlib import Path as _P

    _DEFAULT_BOOKS = [
        {"title": "География 7", "url": "/books/kitobkhon-net-geografiya-7.pdf", "type": "book", "lang": "tg"},
        {"title": "География 8 (2014)", "url": "/books/kitobkhon-net-8.-geografiya-2014.pdf", "type": "book", "lang": "tg"},
        {"title": "География 9 (2013)", "url": "/books/kitobkhon-net-9.-geografiya-2013.pdf", "type": "book", "lang": "tg"},
        {"title": "География 10", "url": "/books/kitobkhon-net-geografiya-10.pdf", "type": "book", "lang": "tg"},
        {"title": "География 11 (2015)", "url": "/books/kitobkhon-net-11.-geografiya-2015.pdf", "type": "book", "lang": "tg"},
    ]

    def _content_items():
        try:
            from db import content_api as _ca
            return _ca.list_content()
        except Exception:
            pass
        data_dir = None
        for cand in [BASE_DIR / "data", _P.cwd() / "data"]:
            try:
                cand.mkdir(parents=True, exist_ok=True)
                data_dir = cand
                break
            except Exception:
                continue
        path = (data_dir or _P.cwd()) / "content_items.json"
        items = []
        try:
            import json as _json
            if path.exists():
                items = _json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(items, list):
                    items = []
        except Exception:
            items = []
        if not items:
            now = datetime.now(_tz.utc).isoformat()
            items = [{
                "id": str(_uuid.uuid4()),
                "type": b["type"],
                "title": b["title"],
                "description": "",
                "url": b["url"],
                "lang": b["lang"],
                "createdAt": now,
            } for b in _DEFAULT_BOOKS]
            try:
                import json as _json
                path.write_text(_json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception:
                pass
        return items

    @app.get("/api/content")
    def _public_content_safe():
        kind = _rq_c.args.get("type") or None
        lang = _rq_c.args.get("lang") or None
        items = _content_items()
        if kind:
            items = [i for i in items if i.get("type") == kind]
        if lang:
            items = [i for i in items if i.get("lang") == lang or not i.get("lang")]
        return _jfy({"items": items, "count": len(items)})
except Exception:
    pass
