"""Geografia server — dual-mode core + Phase 2–8 hooks."""
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
import hashlib  # noqa: E402
import secrets  # noqa: E402

# Allow Phase 8 quiz UI assets through static_proxy whitelist
try:
    PUBLIC_PATHS.update({
        "quiz.html",
        "css/quiz.css",
        "js/quiz-platform.js",
    })
except Exception:
    pass


def _hash_password(password: str, salt: str | None = None):
    salt = salt or secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), 120_000
    ).hex()
    return salt, password_hash


def create_admin_token(admin: dict) -> str:
    admin = enrich_admin(dict(admin)) or admin
    return issue_admin_token(admin)


def require_admin():
    admin = _jwt_require_admin()
    return enrich_admin(admin) if admin else None


def require_perm(*perms: str):
    admin = require_admin()
    if not admin:
        return None
    if any(admin_can(admin, p) for p in perms):
        return admin
    return False


globals()["create_admin_token"] = create_admin_token
globals()["create_user_token"] = _jwt_user_token
globals()["require_admin"] = require_admin
globals()["require_user"] = _jwt_require_user

_orig_submit = globals().get("submit_olympiad")


def submit_olympiad(olympiad_id: str):
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
app.view_functions["submit_olympiad"] = submit_olympiad

register_routes(app, public_student, public_user, olympiad_window_status)
register_quiz_routes(app, _jwt_require_user, require_perm)


@app.route("/quiz")
@app.route("/quiz.html")
def quiz_page():
    return send_from_directory(BASE_DIR, "quiz.html")


def admin_me():
    admin = require_admin()
    if not admin:
        return jsonify({"error": "Дастрасӣ рад шуд."}), 401
    role = normalize_role(admin.get("role"))
    return jsonify({
        "admin": {
            "id": admin.get("id"),
            "login": admin.get("login"),
            "name": admin.get("name"),
            "role": role,
        },
        "permissions": sorted(role_permissions(role)),
        "backend": repo.backend_name(),
    })


app.view_functions["admin_me"] = admin_me

_orig_admin_login = app.view_functions.get("admin_login")


def admin_login():
    resp = _orig_admin_login()
    if getattr(resp, "status_code", 200) != 200:
        return resp
    try:
        data = resp.get_json()
        login_name = (data.get("admin") or {}).get("login")
        if login_name:
            from db.repo import find_admin_by_login

            full = enrich_admin(find_admin_by_login(login_name))
            if full:
                token = create_admin_token(full)
                data["token"] = token
                data["admin"] = {
                    "id": full.get("id"),
                    "login": full.get("login"),
                    "name": full.get("name"),
                    "role": normalize_role(full.get("role")),
                    "createdAt": full.get("createdAt"),
                    "createdBy": full.get("createdBy"),
                }
                data["permissions"] = sorted(role_permissions(full.get("role")))
                return jsonify(data)
    except Exception:
        pass
    return resp


app.view_functions["admin_login"] = admin_login


def _gate(view_name: str, *perms: str):
    orig = app.view_functions.get(view_name)
    if not orig:
        return

    def wrapper(*args, **kwargs):
        admin = require_perm(*perms)
        if admin is None:
            return jsonify({"error": "Дастрасӣ рад шуд."}), 401
        if admin is False:
            return jsonify({"error": deny_message(perms[0])}), 403
        return orig(*args, **kwargs)

    wrapper.__name__ = view_name
    app.view_functions[view_name] = wrapper


_gate("admin_list_students", "students.read")
_gate("admin_create_student", "students.write")
_gate("admin_delete_student", "students.write")
_gate("admin_export_students", "students.read")
_gate("admin_list_olympiads", "olympiads.read")
_gate("admin_create_olympiad", "olympiads.write")
_gate("admin_update_olympiad", "olympiads.write")
_gate("admin_delete_olympiad", "olympiads.write")
_gate("admin_olympiad_results", "results.read")
_gate("admin_monitor", "monitor.read")
_gate("admin_list_admins", "admins.read")
_gate("admin_delete_admin", "admins.write")
_gate("admin_list_participants", "olympiads.read", "participants.write")
_gate("admin_set_participants", "participants.write")


def admin_create_admin():
    admin = require_perm("admins.write")
    if admin is None:
        return jsonify({"error": "Дастрасӣ рад шуд."}), 401
    if admin is False or normalize_role(admin.get("role")) != "super_admin":
        return jsonify({"error": "Танҳо Super Admin метавонад админ созад."}), 403

    payload = request.get_json(silent=True) or {}
    login_name = str(payload.get("login", "")).strip()
    name = str(payload.get("name", "")).strip() or login_name
    password = str(payload.get("password", ""))
    role = normalize_role(payload.get("role") or "olympiad_admin")

    if len(login_name) < 3:
        return jsonify({"error": "Логин бояд камаш 3 рамз бошад."}), 400
    if len(password) < 6:
        return jsonify({"error": "Парол бояд камаш 6 рамз бошад."}), 400
    from db.repo import find_admin_by_login

    if find_admin_by_login(login_name):
        return jsonify({"error": "Ин логин аллакай вуҷуд дорад."}), 409

    salt, password_hash = _hash_password(password)
    new_admin = create_admin_with_role(
        login_name, name, salt, password_hash, admin["login"], role=role
    )
    return jsonify({"admin": new_admin}), 201


app.view_functions["admin_create_admin"] = admin_create_admin


@app.patch("/api/admin/admins/<admin_id>/role")
def admin_patch_role(admin_id: str):
    admin = require_perm("admins.write")
    if admin is None:
        return jsonify({"error": "Дастрасӣ рад шуд."}), 401
    if admin is False or normalize_role(admin.get("role")) != "super_admin":
        return jsonify({"error": "Танҳо Super Admin."}), 403
    payload = request.get_json(silent=True) or {}
    role = normalize_role(payload.get("role"))
    if role not in VALID_ROLES:
        return jsonify({"error": "Нақши нодуруст.", "valid": list(VALID_ROLES)}), 400
    if not update_admin_role(admin_id, role):
        return jsonify({"error": "Админ ёфт нашуд."}), 404
    return jsonify({"ok": True, "id": admin_id, "role": role})


@app.get("/api/admin/roles")
def admin_list_roles():
    admin = require_admin()
    if not admin:
        return jsonify({"error": "Дастрасӣ рад шуд."}), 401
    return jsonify({
        "roles": [
            {"id": r, "permissions": sorted(role_permissions(r))}
            for r in VALID_ROLES
        ]
    })


@app.get("/api/admin/dashboard")
def admin_dashboard():
    admin = require_perm("monitor.read", "students.read")
    if admin is None:
        return jsonify({"error": "Дастрасӣ рад шуд."}), 401
    if admin is False:
        return jsonify({"error": deny_message("monitor.read")}), 403
    return jsonify(schools_api.dashboard_stats())


@app.get("/api/admin/schools")
def admin_list_schools():
    admin = require_perm("schools.read", "students.read")
    if admin is None:
        return jsonify({"error": "Дастрасӣ рад шуд."}), 401
    if admin is False:
        return jsonify({"error": deny_message("schools.read")}), 403
    return jsonify({"schools": schools_api.list_schools()})


@app.post("/api/admin/schools")
def admin_create_school():
    admin = require_perm("schools.write")
    if admin is None:
        return jsonify({"error": "Дастрасӣ рад шуд."}), 401
    if admin is False:
        return jsonify({"error": deny_message("schools.write")}), 403
    payload = request.get_json(silent=True) or {}
    name = str(payload.get("name", "")).strip()
    location = str(payload.get("location", "") or "").strip() or None
    if len(name) < 2:
        return jsonify({"error": "Номи мактаб лозим аст."}), 400
    try:
        school = schools_api.create_school(name, location)
    except ValueError:
        return jsonify({"error": "Ин мактаб аллакай вуҷуд дорад."}), 409
    return jsonify({"school": school}), 201


@app.delete("/api/admin/schools/<school_id>")
def admin_delete_school(school_id: str):
    admin = require_perm("schools.write")
    if admin is None:
        return jsonify({"error": "Дастрасӣ рад шуд."}), 401
    if admin is False:
        return jsonify({"error": deny_message("schools.write")}), 403
    if not schools_api.delete_school(school_id):
        return jsonify({"error": "Мактаб ёфт нашуд."}), 404
    return jsonify({"ok": True})
