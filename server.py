"""Geografia server — dual-mode core + Phase 2–25 hooks."""
from __future__ import annotations

import urllib.request

from flask import jsonify, request, send_from_directory

# Load last known-good core from this repo history, then layer profile hooks.
_CORE = (
    "https://raw.githubusercontent.com/SharifzodaIbrohim/geogrfia/"
    "12d743039abdc42c572a1f09d9d7f71572ee9035/server.py"
)
_code = urllib.request.urlopen(_CORE, timeout=60).read()
exec(compile(_code, "server_core_remote.py", "exec"), globals())

# Profile public assets + routes (idempotent if already present in core)
try:
    PUBLIC_PATHS.update({
        "quiz.html",
        "countries.html",
        "profile.html",
        "css/quiz.css",
        "css/platform.css",
        "css/profile.css",
        "js/quiz-platform.js",
        "js/platform.js",
        "js/platform-home.js",
        "js/profile.js",
        "js/admin-audit.js",
        "js/admin-gmail.js",
    })
except Exception:
    pass

try:
    from db.profile_routes import register_profile_routes  # noqa: E402
    register_profile_routes(app, require_user, require_perm, require_admin)
except Exception as _e:
    try:
        register_profile_routes(app, _jwt_require_user, require_perm, require_admin)
    except Exception:
        pass

# Ensure /profile is served even if missing from core
@app.route("/profile")
@app.route("/profile.html")
@app.route("/Profile")
def profile_page():
    return send_from_directory(BASE_DIR, "profile.html")
