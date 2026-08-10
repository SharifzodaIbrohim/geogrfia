"""
P0.7 / P0.8 boot install:
  - Patch repo role defaults (no super_admin invent)
  - Override admin delete / role-change view functions with guarded versions
"""
from __future__ import annotations

import logging

from flask import jsonify, request

log = logging.getLogger("geografia.rbac_guards")


def install(app) -> None:
    _patch_repo_defaults()
    _patch_admin_views(app)
    log.info("RBAC guards installed")


def _patch_repo_defaults() -> None:
    try:
        from db import repo

        _orig_list = repo.list_admins
        _orig_find = repo.find_admin_by_login

        def list_admins():
            items = _orig_list()
            for a in items:
                # Do not invent privileges for missing role
                if not a.get("role"):
                    a["role"] = None
            return items

        def find_admin_by_login(login: str):
            a = _orig_find(login)
            if a and not a.get("role"):
                # leave empty → normalize_role → None → deny
                a["role"] = a.get("role") or None
            # Strip accidental string 'super_admin' only when it was our old default
            # for missing DB value — if PG returned real role, keep it.
            return a

        repo.list_admins = list_admins
        repo.find_admin_by_login = find_admin_by_login
    except Exception as e:
        log.warning("repo patch: %s", e)


def _patch_admin_views(app) -> None:
    from db.rbac import normalize_role, is_super_admin, deny_message
    from db.admin_role import (
        enrich_admin,
        update_admin_role,
        delete_admin_safe,
        disable_admin_safe,
        create_admin_with_role,
    )
    from db import admin_guards

    def _actor():
        # Prefer JWT/enriched path used by app
        try:
            from db.auth_tokens import admin_from_token
            token = request.headers.get("X-Admin-Token") or ""
            admin = enrich_admin(admin_from_token(token))
            if admin:
                return admin
        except Exception:
            pass
        # Fallback in-memory tokens from core
        try:
            token = request.headers.get("X-Admin-Token") or ""
            raw = app.view_functions  # noqa: keep reference
            # ADMIN_TOKENS may live in globals of server core
            import sys
            mod = sys.modules.get("server_12d7430") or sys.modules.get("__main__")
            tokens = getattr(mod, "ADMIN_TOKENS", None) if mod else None
            if tokens and token in tokens:
                return enrich_admin(dict(tokens[token]))
        except Exception:
            pass
        return None

    # --- DELETE admin ---
    def admin_delete_admin(admin_id: str):
        actor = _actor()
        if not actor:
            return jsonify({"error": "Дастрасӣ рад шуд."}), 401
        try:
            ok = delete_admin_safe(
                admin_id,
                actor=actor,
                ip=request.headers.get("X-Forwarded-For", request.remote_addr),
            )
            if not ok:
                return jsonify({"error": "Ёфт нашуд."}), 404
            return jsonify({"ok": True})
        except PermissionError as e:
            code = str(e)
            msgs = {
                "super_admin_required": "Танҳо Super Admin.",
                "cannot_self_delete": "Шумо худро нест карда наметавонед.",
                "cannot_delete_last_super_admin": "Охирин Super Admin-ро нест кардан мумкин нест.",
            }
            return jsonify({"error": msgs.get(code, code), "reason": code}), 403
        except ValueError as e:
            if str(e) == "not_found":
                return jsonify({"error": "Ёфт нашуд."}), 404
            return jsonify({"error": str(e)}), 400

    # --- PATCH role ---
    def admin_patch_role(admin_id: str):
        actor = _actor()
        if not actor:
            return jsonify({"error": "Дастрасӣ рад шуд."}), 401
        payload = request.get_json(silent=True) or {}
        new_role = payload.get("role")
        try:
            ok = update_admin_role(
                admin_id,
                new_role,
                actor=actor,
                ip=request.headers.get("X-Forwarded-For", request.remote_addr),
            )
            if not ok:
                return jsonify({"error": "Ёфт нашуд."}), 404
            return jsonify({"ok": True, "role": normalize_role(new_role)})
        except PermissionError as e:
            code = str(e)
            msgs = {
                "super_admin_required": "Танҳо Super Admin.",
                "cannot_demote_last_super_admin": "Охирин Super Admin-ро паст кардан мумкин нест.",
            }
            return jsonify({"error": msgs.get(code, code), "reason": code}), 403
        except ValueError as e:
            code = str(e)
            msgs = {
                "invalid_role": "Нақши нодуруст.",
                "not_found": "Ёфт нашуд.",
            }
            status = 404 if code == "not_found" else 400
            return jsonify({"error": msgs.get(code, code), "reason": code}), status

    # Bind over existing endpoints if present
    for name, fn in [
        ("admin_delete_admin", admin_delete_admin),
        ("admin_patch_role", admin_patch_role),
    ]:
        if name in app.view_functions:
            app.view_functions[name] = fn
        else:
            # ensure routes exist
            try:
                if name == "admin_delete_admin":
                    app.add_url_rule(
                        "/api/admin/admins/<admin_id>",
                        name,
                        fn,
                        methods=["DELETE"],
                    )
                elif name == "admin_patch_role":
                    app.add_url_rule(
                        "/api/admin/admins/<admin_id>/role",
                        name,
                        fn,
                        methods=["PATCH"],
                    )
            except AssertionError:
                app.view_functions[name] = fn
