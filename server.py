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

# P0.9: secrets policy check
try:
    import os as _os
    from db.secrets import require_production_secrets
    try:
        _sec = require_production_secrets()
        print("[boot] secrets:", _sec)
    except RuntimeError as _se:
        print("[boot] secrets WARNING:", _se)
        if _os.environ.get("GEOGRAFIA_STRICT_SECRETS", "").strip().lower() in ("1", "true", "yes"):
            raise
except Exception as _e:
    print("[boot] secrets check:", _e)

# P0.6: migrations
try:
    import os as _os
    if _os.environ.get("DATABASE_URL"):
        from db.migrate import run_migrations as _run_migrations
        _mig = _run_migrations()
        print("[boot] migrations:", _mig)
except Exception as _e:
    print("[boot] migrations failed:", _e)

try:
    PUBLIC_PATHS.update({
        "profile.html", "courses.html", "leaderboard.html",
        "css/profile.css", "js/profile.js", "js/admin-gmail.js",
        "js/i18n.js", "js/admin-content.js", "js/platform-home.js",
        "js/admin-leaderboard.js", "js/admin-fixes.js", "js/google-signin.js",
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

try:
    from flask import jsonify as _jq
    from db import quiz_api as _qapi
    from db.repo import list_olympiads as _list_oly

    def _public_list_quizzes_fixed():
        safe = []
        seen = set()
        try:
            items = _qapi.list_quizzes(include_draft=False)
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
        try:
            for o in _list_oly():
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
                    "questionCount": o.get("questionCount") or 0,
                    "source": "quiz",
                    "eventKind": "olympiad_quiz",
                })
        except Exception:
            pass
        return _jq({"quizzes": safe})

    app.view_functions["public_list_quizzes"] = _public_list_quizzes_fixed
    _has = False
    for _r in list(app.url_map.iter_rules()):
        if _r.rule == "/api/quizzes" and "GET" in (_r.methods or set()):
            app.view_functions[_r.endpoint] = _public_list_quizzes_fixed
            _has = True
    if not _has:
        try:
            app.add_url_rule("/api/quizzes", "public_list_quizzes", _public_list_quizzes_fixed, methods=["GET"])
        except AssertionError:
            pass
except Exception as _e:
    print("[boot] public quiz list override:", _e)

try:
    from db.force_public_quiz_list import install as _install_strict_quiz_list
    _install_strict_quiz_list(app)
except Exception as _e:
    print("[boot] force_public_quiz_list:", _e)

try:
    from db.install_leaderboard import install as _install_lb
    _install_lb(app)
except Exception as _e:
    print("[boot] leaderboard:", _e)

try:
    from db.one_attempt import install as _install_one_attempt
    _install_one_attempt()
except Exception:
    pass

try:
    from db.install_rbac_guards import install as _install_rbac
    _install_rbac(app)
except Exception as _e:
    print("[boot] rbac guards:", _e)

try:
    from db.install_secrets_health import install as _install_sec_health
    _install_sec_health(app)
except Exception as _e:
    print("[boot] secrets health:", _e)

# P1.1: HttpOnly Secure session cookies (user + admin)
try:
    from db.install_session_auth import install as _install_session
    _install_session(app)
except Exception as _e:
    print("[boot] session auth:", _e)
