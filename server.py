"""Geografia server — dual-mode core + Phase 2/3 hooks."""
from __future__ import annotations

import urllib.request

# Load dual-mode server implementation (Phase 1.5)
_CORE = (
    "https://raw.githubusercontent.com/isoevibrohim/geogrfia/"
    "3e9e5989f992afa7ab478c9da0480bed9a2c8375/server.py"
)
_code = urllib.request.urlopen(_CORE, timeout=60).read()
exec(compile(_code, "server_core_remote.py", "exec"), globals())

# Phase 2 JWT + Phase 3 student link / participants / access
from db.phase23_hooks import (  # noqa: E402
    create_admin_token as _jwt_admin_token,
    create_user_token as _jwt_user_token,
    require_admin as _jwt_require_admin,
    require_user as _jwt_require_user,
    register_routes,
)
from db import student_access  # noqa: E402

# Override in-memory tokens with JWT
globals()["create_admin_token"] = _jwt_admin_token
globals()["create_user_token"] = _jwt_user_token
globals()["require_admin"] = _jwt_require_admin
globals()["require_user"] = _jwt_require_user

# Gate olympiad submit by participant assignment
_orig_submit = globals().get("submit_olympiad")

def submit_olympiad(olympiad_id: str):
    from flask import request, jsonify
    payload = request.get_json(silent=True) or {}
    student_id = str(payload.get("studentId", "")).strip()
    if student_id and olympiad_id:
        access = student_access.student_has_olympiad_access(olympiad_id, student_id)
        if not access.get("allowed"):
            reason = access.get("reason")
            msg = (
                "Шумо ба ин олимпиада таъин нашудаед."
                if reason == "not_assigned"
                else "Дастрасӣ рад шуд."
            )
            return jsonify({"error": msg, "reason": reason}), 403
    return _orig_submit(olympiad_id)

globals()["submit_olympiad"] = submit_olympiad
# Re-bind Flask route
app.view_functions["submit_olympiad"] = submit_olympiad

register_routes(app, public_student, public_user, olympiad_window_status)
