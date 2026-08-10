"""Geografia server entry — loads stable core then profile/content/i18n assets."""
from __future__ import annotations

import urllib.request

from flask import send_from_directory

# Full working server from last good commit
_url = (
    "https://raw.githubusercontent.com/SharifzodaIbrohim/geogrfia/"
    "12d743039abdc42c572a1f09d9d7f71572ee9035/server.py"
)
_src = urllib.request.urlopen(_url, timeout=90).read()
exec(compile(_src, "server_12d7430.py", "exec"), globals())

# Extra public static assets
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

# Profile API routes
try:
    from db.profile_routes import register_profile_routes
    register_profile_routes(app, _jwt_require_user, require_perm, require_admin)
except Exception:
    try:
        register_profile_routes(app, require_user, require_perm, require_admin)
    except Exception:
        pass

# Content / Courses API
try:
    from db.content_routes import register_content_routes
    register_content_routes(app, require_perm, require_admin)
except Exception as _e:
    pass

# Pages
@app.route("/profile")
@app.route("/profile.html")
@app.route("/Profile")
def _profile_page():
    return send_from_directory(BASE_DIR, "profile.html")


@app.route("/courses")
@app.route("/courses.html")
def _courses_page():
    return send_from_directory(BASE_DIR, "courses.html")


# Serve books PDFs if folder exists
try:
    @app.route("/books/<path:filename>")
    def _books(filename):
        return send_from_directory(BASE_DIR / "books", filename)
except Exception:
    pass
