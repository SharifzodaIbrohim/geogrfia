"""Geografia server entry — loads stable core then platform patches."""
from __future__ import annotations

import logging
import urllib.request
from flask import send_from_directory

_boot_log = logging.getLogger("geografia.boot")
if not _boot_log.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [boot] %(message)s"))
    _boot_log.addHandler(_h)
    _boot_log.setLevel(logging.INFO)

_url = (
    "https://raw.githubusercontent.com/SharifzodaIbrohim/geogrfia/"
    "12d743039abdc42c572a1f09d9d7f71572ee9035/server.py"
)
_src = urllib.request.urlopen(_url, timeout=90).read()
exec(compile(_src, "server_12d7430.py", "exec"), globals())


def _safe_install(name: str, fn):
    """P1.7: never silent-swallow install failures."""
    try:
        fn()
    except Exception as e:
        _boot_log.exception("install failed: %s — %s", name, e)
        print(f"[boot] {name} FAILED: {e}")


try:
    import os as _os
    from db.secrets import require_production_secrets
    try:
        print("[boot] secrets:", require_production_secrets())
    except RuntimeError as _se:
        print("[boot] secrets WARNING:", _se)
        if _os.environ.get("GEOGRAFIA_STRICT_SECRETS", "").strip().lower() in ("1", "true", "yes"):
            raise
except Exception as _e:
    _boot_log.exception("secrets check")
    print("[boot] secrets check:", _e)

try:
    import os as _os
    if _os.environ.get("DATABASE_URL"):
        from db.migrate import run_migrations as _run_migrations
        print("[boot] migrations:", _run_migrations())
except Exception as _e:
    _boot_log.exception("migrations")
    print("[boot] migrations failed:", _e)

_safe_install("session_ttl", lambda: print("[boot] session ttl:", __import__("db.session_ttl", fromlist=["ttl_public_status"]).ttl_public_status()))
_safe_install("security_headers", lambda: __import__("db.security_headers", fromlist=["install"]).install(app))
_safe_install("rate_limit", lambda: __import__("db.install_rate_limit", fromlist=["install"]).install(app))
_safe_install("request_logging", lambda: __import__("db.request_logging", fromlist=["install"]).install(app))

try:
    PUBLIC_PATHS.update({
        "profile.html", "courses.html", "leaderboard.html", "student.html",
        "css/profile.css", "css/student.css", "js/profile.js", "js/student.js",
        "js/admin-gmail.js", "js/i18n.js", "js/admin-content.js", "js/platform-home.js",
        "js/admin-leaderboard.js", "js/admin-fixes.js", "js/google-signin.js",
        "js/auth-logout.js",
    })
except Exception as _e:
    _boot_log.warning("PUBLIC_PATHS: %s", _e)

try:
    from db.profile_routes import register_profile_routes
    register_profile_routes(app, _jwt_require_user, require_perm, require_admin)
except Exception:
    try:
        register_profile_routes(app, require_user, require_perm, require_admin)
    except Exception as _e:
        _boot_log.warning("profile_routes: %s", _e)

try:
    from db.content_routes import register_content_routes
    register_content_routes(app, require_perm, require_admin)
except Exception as _e:
    _boot_log.warning("content_routes: %s", _e)

@app.route("/profile")
@app.route("/profile.html")
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

@app.route("/student")
@app.route("/student.html")
def _student_page():
    return send_from_directory(BASE_DIR, "student.html")

try:
    from flask import jsonify as _jq
    from db import quiz_api as _qapi
    from db.repo import list_olympiads as _list_oly

    def _public_list_quizzes_fixed():
        safe, seen = [], set()
        try:
            items = _qapi.list_quizzes(include_draft=False)
        except Exception as e:
            _boot_log.warning("list_quizzes: %s", e)
            items = []
        for q in items:
            if q.get("source") == "olympiad":
                continue
            qid = q.get("id")
            if not qid or qid in seen:
                continue
            seen.add(qid)
            safe.append({
                "id": qid, "title": q.get("title"), "description": q.get("description"),
                "passScore": q.get("passScore"), "timeLimitSec": q.get("timeLimitSec"),
                "accessMode": q.get("accessMode") or "public", "questionCount": q.get("questionCount") or 0,
                "source": "quiz",
            })
        try:
            for o in _list_oly():
                if (o.get("type") or "olympiad").lower() != "quiz" or not o.get("isActive"):
                    continue
                oid = o.get("id")
                if not oid or oid in seen:
                    continue
                seen.add(oid)
                safe.append({
                    "id": oid, "title": o.get("title"), "passScore": o.get("passScore") or 70,
                    "accessMode": "school", "questionCount": o.get("questionCount") or 0,
                    "source": "quiz", "eventKind": "olympiad_quiz",
                })
        except Exception as e:
            _boot_log.warning("list_oly for quizzes: %s", e)
        return _jq({"quizzes": safe})

    for _r in list(app.url_map.iter_rules()):
        if _r.rule == "/api/quizzes" and "GET" in (_r.methods or set()):
            app.view_functions[_r.endpoint] = _public_list_quizzes_fixed
except Exception as _e:
    _boot_log.exception("public quiz list")
    print("[boot] public quiz list:", _e)

_safe_install("force_public_quiz_list", lambda: __import__("db.force_public_quiz_list", fromlist=["install"]).install(app))
_safe_install("leaderboard", lambda: __import__("db.install_leaderboard", fromlist=["install"]).install(app))
_safe_install("one_attempt", lambda: __import__("db.one_attempt", fromlist=["install"]).install())
_safe_install("rbac", lambda: __import__("db.install_rbac_guards", fromlist=["install"]).install(app))
_safe_install("secrets_health", lambda: __import__("db.install_secrets_health", fromlist=["install"]).install(app))
_safe_install("session_auth", lambda: __import__("db.install_session_auth", fromlist=["install"]).install(app))
_safe_install("student_portal", lambda: __import__("db.install_student_portal", fromlist=["install"]).install(app))
_safe_install("admin_students", lambda: __import__("db.install_admin_students", fromlist=["install"]).install(app))
