"""Geografia server entry — loads stable core then profile."""
from __future__ import annotations

import urllib.request

# Full working server from last good commit
_url = (
    "https://raw.githubusercontent.com/SharifzodaIbrohim/geogrfia/"
    "12d743039abdc42c572a1f09d9d7f71572ee9035/server.py"
)
_src = urllib.request.urlopen(_url, timeout=90).read()
exec(compile(_src, "server_12d7430.py", "exec"), globals())

# Extra public static for Profile
try:
    PUBLIC_PATHS.update({
        "profile.html",
        "css/profile.css",
        "js/profile.js",
        "js/admin-gmail.js",
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

# /profile page
@app.route("/profile")
@app.route("/profile.html")
@app.route("/Profile")
def _profile_page():
    return send_from_directory(BASE_DIR, "profile.html")
