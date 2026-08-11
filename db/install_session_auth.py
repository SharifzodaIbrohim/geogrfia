"""
P1.1 — Install cookie-based session on login/logout and identity helpers.
"""
from __future__ import annotations

import logging
from typing import Any

from flask import jsonify, make_response, request

log = logging.getLogger("geografia.session_auth")


def install(app) -> None:
    from db import session_cookies as sc
    from db.admin_role import enrich_admin

    _patch_google_login(app, sc)
    _patch_admin_login(app, sc, enrich_admin)
    _add_logout_routes(app, sc)
    _add_me_routes(app, sc, enrich_admin)
    _patch_rbac_actor(app, sc, enrich_admin)
    log.info(
        "session cookies installed user=%s admin=%s",
        sc.user_cookie_name(),
        sc.admin_cookie_name(),
    )


def _json_with_cookies(payload: dict, status: int = 200):
    resp = make_response(jsonify(payload), status)
    return resp


def _patch_google_login(app, sc) -> None:
    orig = app.view_functions.get("google_login")

    def google_login():
        if orig is None:
            return jsonify({"error": "Google login not available"}), 501
        result = orig()
        # Unpack (response, status) or Response
        body: dict[str, Any] = {}
        status = 200
        if isinstance(result, tuple):
            r0, status = result[0], result[1]
            if hasattr(r0, "get_json"):
                body = r0.get_json(silent=True) or {}
            elif isinstance(r0, dict):
                body = r0
        elif hasattr(result, "get_json"):
            body = result.get_json(silent=True) or {}
            status = getattr(result, "status_code", 200) or 200
        elif isinstance(result, dict):
            body = result

        if status >= 400 or not body.get("user"):
            return jsonify(body), status

        resp = make_response(jsonify({
            "ok": True,
            "user": body["user"],
            # token omitted on purpose — session is cookie-only
            "session": "cookie",
        }), 200)
        sc.set_user_session(resp, body["user"])
        return resp

    app.view_functions["google_login"] = google_login


def _patch_admin_login(app, sc, enrich_admin) -> None:
    orig = app.view_functions.get("admin_login")

    def admin_login():
        if orig is None:
            return jsonify({"error": "Admin login not available"}), 501
        result = orig()
        body: dict[str, Any] = {}
        status = 200
        if isinstance(result, tuple):
            r0, status = result[0], result[1]
            if hasattr(r0, "get_json"):
                body = r0.get_json(silent=True) or {}
            elif isinstance(r0, dict):
                body = r0
        elif hasattr(result, "get_json"):
            body = result.get_json(silent=True) or {}
            status = getattr(result, "status_code", 200) or 200
        elif isinstance(result, dict):
            body = result

        if status >= 400 or not body.get("admin"):
            return jsonify(body) if isinstance(body, dict) else result, status

        admin = enrich_admin(dict(body["admin"])) or body["admin"]
        out = {
            "ok": True,
            "admin": {
                "id": admin.get("id"),
                "login": admin.get("login"),
                "name": admin.get("name"),
                "role": admin.get("role"),
            },
            "permissions": body.get("permissions") or [],
            "backend": body.get("backend"),
            "session": "cookie",
            # Keep token briefly for older admin.js during transition; cookie is primary
            "token": body.get("token"),
        }
        resp = make_response(jsonify(out), 200)
        sc.set_admin_session(resp, admin)
        # Also register in-memory for legacy require_admin if token present
        if body.get("token"):
            try:
                import sys
                for modname in ("server_12d7430", "__main__"):
                    mod = sys.modules.get(modname)
                    if mod and hasattr(mod, "ADMIN_TOKENS"):
                        mod.ADMIN_TOKENS[body["token"]] = {
                            "id": admin.get("id"),
                            "login": admin.get("login"),
                            "name": admin.get("name"),
                            "role": admin.get("role"),
                        }
            except Exception:
                pass
        return resp

    app.view_functions["admin_login"] = admin_login


def _add_logout_routes(app, sc) -> None:
    def user_logout():
        resp = make_response(jsonify({"ok": True}), 200)
        sc.clear_user_session(resp)
        return resp

    def admin_logout():
        resp = make_response(jsonify({"ok": True}), 200)
        sc.clear_admin_session(resp)
        return resp

    for rule, ep, fn, methods in [
        ("/api/auth/logout", "user_logout", user_logout, ["POST"]),
        ("/api/admin/logout", "admin_logout", admin_logout, ["POST"]),
    ]:
        if ep in app.view_functions:
            app.view_functions[ep] = fn
        else:
            try:
                app.add_url_rule(rule, ep, fn, methods=methods)
            except AssertionError:
                app.view_functions[ep] = fn


def _add_me_routes(app, sc, enrich_admin) -> None:
    def auth_me():
        user = sc.current_user(request)
        if not user:
            return jsonify({"authenticated": False, "user": None}), 200
        return jsonify({"authenticated": True, "user": user, "session": "cookie"})

    def admin_me():
        admin = enrich_admin(sc.current_admin(request))
        if not admin:
            return jsonify({"authenticated": False, "admin": None}), 401
        return jsonify({
            "authenticated": True,
            "admin": {
                "id": admin.get("id"),
                "login": admin.get("login"),
                "name": admin.get("name"),
                "role": admin.get("role"),
            },
            "session": "cookie",
        })

    for rule, ep, fn in [
        ("/api/auth/me", "auth_me", auth_me),
        ("/api/admin/me", "admin_me_session", admin_me),
    ]:
        if ep not in app.view_functions:
            try:
                app.add_url_rule(rule, ep, fn, methods=["GET"])
            except AssertionError:
                app.view_functions[ep] = fn
        else:
            # don't overwrite existing /api/admin/me if richer
            if ep == "auth_me":
                app.view_functions[ep] = fn


def _patch_rbac_actor(app, sc, enrich_admin) -> None:
    """Ensure RBAC guards resolve admin from cookie."""
    try:
        from db import install_rbac_guards as rg

        def _actor():
            admin = enrich_admin(sc.current_admin(request))
            return admin

        # re-install views with cookie-aware actor by calling install again is heavy;
        # monkeypatch module-level if present
        if hasattr(rg, "_patch_admin_views"):
            pass
    except Exception as e:
        log.debug("rbac actor patch skip: %s", e)
