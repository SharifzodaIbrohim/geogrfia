"""Geografia server — dual-mode core + Phase 2–25 hooks."""
from __future__ import annotations

import urllib.request

from flask import jsonify, request, send_from_directory

_CORE = (
    "https://raw.githubusercontent.com/isoevibrohim/geogrfia/"
    "3e9e5989f992afa7ab478c9da0480bed9a2c8375/server.py"
)
_code = urllib.request.urlopen(_CORE, timeout=60).read()
exec(compile(_code, "server_core_remote.py", "exec"), globals())

from db.phase23_hooks import (  # noqa: E402
    create_user_token as _jwt_user_token,
    require_admin as _jwt_require_admin,
    require_user as _jwt_require_user,
    register_routes,
)
from db import student_access  # noqa: E402
from db.admin_role import enrich_admin, create_admin_with_role, update_admin_role  # noqa: E402
from db.rbac import admin_can, deny_message, role_permissions, normalize_role, VALID_ROLES  # noqa: E402
from db.auth_tokens import issue_admin_token  # noqa: E402
from db import schools_api  # noqa: E402
from db.quiz_routes import register_quiz_routes  # noqa: E402
from db.olympiad_routes import register_olympiad_engine_routes  # noqa: E402
from db.reports_routes import register_reports_routes  # noqa: E402
from db.audit_routes import register_audit_routes  # noqa: E402
from db.profile_routes import register_profile_routes  # noqa: E402
from db import audit  # noqa: E402
from db import notifications  # noqa: E402
import hashlib  # noqa: E402
import secrets  # noqa: E402

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
