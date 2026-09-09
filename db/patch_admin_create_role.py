"""
Fix admin create: pass actor so super_admin is actually stored.
Also accept role=admin (full ops except managing admins).
"""
from __future__ import annotations

import logging

from flask import jsonify, request

log = logging.getLogger("geografia.patch_admin_create_role")


def install(app) -> None:
    import server as srv

    require_perm = getattr(srv, "require_perm", None)
    require_admin = getattr(srv, "require_admin", None)
    _hash_password = getattr(srv, "_hash_password", None) or getattr(srv, "hash_password", None)

    if require_perm is None and require_admin is None:
        log.warning("patch_admin_create_role: no require_perm/require_admin")
        return
    if _hash_password is None:
        import hashlib
        import secrets

        def _hash_password(password: str, salt: str | None = None):
            salt = salt or secrets.token_hex(16)
            password_hash = hashlib.pbkdf2_hmac(
                "sha256", password.encode("utf-8"), bytes.fromhex(salt), 120_000
            ).hex()
            return salt, password_hash

    from db.rbac import normalize_role, VALID_ROLES, is_super_admin, admin_can
    from db.admin_role import create_admin_with_role, update_admin_role
    from db.repo import find_admin_by_login

    def _actor():
        if require_perm is not None:
            a = require_perm("admins.write")
            if a is False:
                return False
            return a
        return require_admin() if require_admin else None

    def admin_create_admin():
        admin = _actor()
        if admin is None:
            return jsonify({"error": "Дастрасӣ рад шуд."}), 401
        if admin is False or not is_super_admin(admin):
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
        if find_admin_by_login(login_name):
            return jsonify({"error": "Ин логин аллакай вуҷуд дорад."}), 409
        if role is None:
            return jsonify({"error": "Нақши нодуруст.", "valid": list(VALID_ROLES)}), 400

        salt, password_hash = _hash_password(password)
        new_admin = create_admin_with_role(
            login_name,
            name,
            salt,
            password_hash,
            admin.get("login") or str(admin.get("id") or "system"),
            role=role,
            actor=admin,  # critical: allows super_admin assignment
        )
        return jsonify({"admin": new_admin}), 201

    def admin_patch_role(admin_id: str):
        admin = _actor()
        if admin is None:
            return jsonify({"error": "Дастрасӣ рад шуд."}), 401
        if admin is False or not is_super_admin(admin):
            return jsonify({"error": "Танҳо Super Admin."}), 403
        payload = request.get_json(silent=True) or {}
        role = normalize_role(payload.get("role"))
        if role not in VALID_ROLES:
            return jsonify({"error": "Нақши нодуруст.", "valid": list(VALID_ROLES)}), 400
        try:
            ok = update_admin_role(
                admin_id,
                role,
                actor=admin,
                ip=request.headers.get("X-Forwarded-For", request.remote_addr),
            )
        except PermissionError as e:
            code = str(e)
            msgs = {
                "super_admin_required": "Танҳо Super Admin.",
                "cannot_demote_last_super_admin": "Охирин Super Admin-ро паст кардан мумкин нест.",
            }
            return jsonify({"error": msgs.get(code, code), "reason": code}), 403
        except ValueError as e:
            code = str(e)
            status = 404 if code == "not_found" else 400
            return jsonify({"error": code, "reason": code}), status
        if not ok:
            return jsonify({"error": "Админ ёфт нашуд."}), 404
        return jsonify({"ok": True, "id": admin_id, "role": role})

    app.view_functions["admin_create_admin"] = admin_create_admin
    app.view_functions["admin_patch_role"] = admin_patch_role
    for rule, endpoint, methods in (
        ("/api/admin/admins", "admin_create_admin", ["POST"]),
        ("/api/admin/admins/<admin_id>/role", "admin_patch_role", ["PATCH"]),
    ):
        try:
            app.add_url_rule(rule, endpoint, app.view_functions[endpoint], methods=methods)
        except Exception:
            pass

    log.info("patch_admin_create_role installed")
    print("[boot] patch_admin_create_role OK")
