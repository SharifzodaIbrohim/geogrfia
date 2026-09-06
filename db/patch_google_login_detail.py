"""Boot patch: richer Google login errors + safe upsert/token path."""
from __future__ import annotations

from flask import request, jsonify


def install(app=None):
    if app is None:
        return

    # Prefer the real endpoint name; Flask may store as view function name
    view_name = None
    for name, fn in list(app.view_functions.items()):
        if name in ("google_login", "auth_google", "api_auth_google"):
            view_name = name
            break
    if view_name is None:
        # Match by rule path
        for rule in app.url_map.iter_rules():
            if str(rule.rule).rstrip("/") == "/api/auth/google" and "POST" in (rule.methods or set()):
                view_name = rule.endpoint
                break
    if not view_name:
        print("[boot] patch_google_login_detail: no /api/auth/google endpoint")
        return

    from db.google_auth import (
        google_configured,
        GOOGLE_CLIENT_ID,
        verify_google_id_token,
        last_verify_error,
    )
    import repo

    # create_user_token may be patched to JWT in globals of server_core
    def _get_create_token():
        import sys
        # Prefer live globals on the loaded server module
        for mod_name in ("server_core", "server", "__main__"):
            mod = sys.modules.get(mod_name)
            if mod and hasattr(mod, "create_user_token"):
                return getattr(mod, "create_user_token")
        # Fallback: phase23 JWT
        try:
            from db.phase23_hooks import create_user_token as jwt_ct
            return jwt_ct
        except Exception:
            pass
        raise RuntimeError("create_user_token not found")

    def _public_user(user: dict) -> dict:
        if not user:
            return {}
        return {
            "id": user.get("id"),
            "email": user.get("email"),
            "name": user.get("name"),
            "avatar": user.get("avatar") or user.get("avatarUrl") or user.get("avatar_url"),
            "googleId": user.get("googleId") or user.get("google_id"),
        }

    def google_login_patched():
        if not google_configured():
            return jsonify({
                "error": "Google OAuth ҳоло танзим нашудааст. GOOGLE_CLIENT_ID-ро гузоред.",
                "detail": "not_configured",
            }), 503

        payload = request.get_json(silent=True) or {}
        id_token = str(
            payload.get("idToken")
            or payload.get("credential")
            or payload.get("token")
            or ""
        ).strip()
        if not id_token:
            return jsonify({"error": "idToken лозим аст.", "detail": "missing_token"}), 400

        info = verify_google_id_token(id_token)
        if not info:
            err = last_verify_error() or "verify_failed"
            # Safe diagnostics for the client (no secrets)
            return jsonify({
                "error": "Google token нодуруст аст.",
                "detail": err,
                "clientIdPrefix": (GOOGLE_CLIENT_ID[:20] + "\u2026") if GOOGLE_CLIENT_ID else None,
            }), 401

        try:
            user = repo.upsert_google_user(
                google_id=info["sub"],
                email=info["email"],
                name=info["name"],
                avatar=info.get("picture"),
            )
        except Exception as e:
            return jsonify({
                "error": "Сабти корбар ноком шуд.",
                "detail": f"{type(e).__name__}: {e}",
            }), 500

        try:
            create_user_token = _get_create_token()
            token = create_user_token(user)
        except Exception as e:
            return jsonify({
                "error": "Сохтани session ноком шуд.",
                "detail": f"{type(e).__name__}: {e}",
            }), 500

        if not token:
            return jsonify({"error": "Token холӣ баромад.", "detail": "empty_token"}), 500

        return jsonify({"user": _public_user(user), "token": token})

    app.view_functions[view_name] = google_login_patched
    print(f"[boot] patch_google_login_detail: replaced {view_name}")
