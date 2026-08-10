"""Geografia server entry — loads stable core then platform patches."""
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
        "profile.html", "courses.html", "leaderboard.html",
        "css/profile.css", "js/profile.js", "js/admin-gmail.js",
        "js/i18n.js", "js/admin-content.js", "js/platform-home.js",
        "js/admin-leaderboard.js", "js/admin-fixes.js",
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

@app.route("/leaderboard")
@app.route("/leaderboard.html")
def _leaderboard_page():
    return send_from_directory(BASE_DIR, "leaderboard.html")

try:
    @app.route("/books/<path:filename>")
    def _books(filename):
        return send_from_directory(BASE_DIR / "books", filename)
except Exception:
    pass

# Olympiad: Student ID only via student_access — no Gmail open on olympiads.
# Ordinary users: /quiz = standalone quizzes; /student = olympiads + quizzes.

# FINAL override: public quiz list = standalone only (must run last)
try:
    from flask import jsonify as _jq
    from db import quiz_api as _qapi

    def _public_list_quizzes_fixed():
        items = _qapi.list_quizzes(include_draft=False)
        safe = []
        for q in items:
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
        return _jq({"quizzes": safe})

    app.view_functions["public_list_quizzes"] = _public_list_quizzes_fixed
except Exception:
    pass

try:
    from db.force_public_quiz_list import install as _install_strict_quiz_list
    _install_strict_quiz_list(app)
except Exception as _e:
    print("[boot] force_public_quiz_list:", _e)

try:
    from db.one_attempt import install as _install_one_attempt
    _install_one_attempt()
except Exception:
    pass
