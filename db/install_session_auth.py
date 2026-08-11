"""
P1.1 — Install cookie-based session on login/logout and identity helpers.
"""
from __future__ import annotations

import logging
import sys
from typing import Any

from flask import g, jsonify, make_response, request

log = logging.getLogger("geografia.session_auth")


def install(app) -> None:
    from db import session_cookies as sc
    from db.admin_role import enrich_admin

    _patch_google_login(app, sc)
    _patch_admin_login(app, sc, enrich_admin)
    _add_logout_routes(app, sc)
    _add_me_routes(app, sc, enrich_admin)
    _install_before_request(app, sc, enrich_admin)
    _patch_require_admin_globals(sc, enrich_admin)
    log.info(
        "session cookies installed user=%s admin=%s",
        sc.user_cookie_name(),
        sc.admin_cookie_name(),
    )
    print(
        "[boot] session auth: cookies",
        sc.user_cookie_name(),
        sc.admin_cookie_name(),
    )


def _patch_google_login(app, sc) -> None:
    orig = app.view_functions.get("google_login")

    def google_login():
        if orig is None:
            return jsonify({"error": "Google login not available"}), 501
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

        if status >= 400 or not body.get("user"):
            return jsonify(body), status

        resp = make_response(jsonify({
            "ok": True,
            "user": body["user"],
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
            "token": body.get("token"),  # transition only
        }
        resp = make_response(jsonify(out), 200)
        cookie_tok = sc.set_admin_session(resp, admin)
        # Bridge cookie JWT into legacy ADMIN_TOKENS so core require_admin works
        _register_legacy_admin_token(cookie_tok, admin)
        if body.get("token"):
            _register_legacy_admin_token(body["token"], admin)
        return resp

    app.view_functions["admin_login"] = admin_login


def _register_legacy_admin_token(token: str, admin: dict) -> None:
    if not token:
        return
    payload = {
        "id": admin.get("id"),
        "login": admin.get("login"),
        "name": admin.get("name"),
        "role": admin.get("role"),
    }
    for modname in ("server_12d7430", "server_core_remote", "__main__"):
        mod = sys.modules.get(modname)
        if mod and hasattr(mod, "ADMIN_TOKENS"):
            try:
                mod.ADMIN_TOKENS[token] = payload
            except Exception:
                pass


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
            return jsonify({"authenticated": False, "admin": None, "error": "Дастрасӣ рад шуд."}), 401
        return jsonify({
            "authenticated": True,
            "ok": True,
            "admin": {
                "id": admin.get("id"),
                "login": admin.get("login"),
                "name": admin.get("name"),
                "role": admin.get("role"),
            },
            "session": "cookie",
        })

    # Override ANY existing handler bound to these paths
    for rule, preferred_ep, fn in [
        ("/api/auth/me", "auth_me", auth_me),
        ("/api/admin/me", "admin_me", admin_me),
    ]:
        replaced = False
        for r in list(app.url_map.iter_rules()):
            if r.rule == rule and "GET" in (r.methods or set()):
                app.view_functions[r.endpoint] = fn
                replaced = True
        if preferred_ep in app.view_functions:
            app.view_functions[preferred_ep] = fn
            replaced = True
        if not replaced:
            try:
                app.add_url_rule(rule, preferred_ep, fn, methods=["GET"])
            except AssertionError:
                app.view_functions[preferred_ep] = fn


def _install_before_request(app, sc, enrich_admin) -> None:
    """Each request: if admin cookie present, register JWT into ADMIN_TOKENS."""

    @app.before_request
    def _bind_session_cookie():
        try:
            admin = enrich_admin(sc.current_admin(request))
            g.session_admin = admin
            if admin:
                # Cookie value itself is the JWT — use as legacy token key
                from db.session_cookies import admin_cookie_name
                raw = (request.cookies.get(admin_cookie_name()) or "").strip()
                if raw:
                    _register_legacy_admin_token(raw, admin)
            user = sc.current_user(request)
            g.session_user = user
        except Exception:
            g.session_admin = None
            g.session_user = None


def _patch_require_admin_globals(sc, enrich_admin) -> None:
    """Wrap core require_admin to prefer cookie session."""
    for modname in ("server_12d7430", "__main__"):
        mod = sys.modules.get(modname)
        if not mod:
            continue
        orig = getattr(mod, "require_admin", None)
        if not callable(orig):
            continue

        def _make(orig_fn):
            def require_admin_wrapped(*args, **kwargs):
                admin = getattr(g, "session_admin", None)
                if admin:
                    return admin
                try:
                    admin = enrich_admin(sc.current_admin(request))
                    if admin:
                        return admin
                except Exception:
                    pass
                return orig_fn(*args, **kwargs)

            return require_admin_wrapped

        try:
            setattr(mod, "require_admin", _make(orig))
        except Exception as e:
            log.debug("require_admin wrap %s: %s", modname, e)
