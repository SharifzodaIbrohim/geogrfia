"""Boot patch: replace /api/auth/google with detailed errors + full try/except."""
from __future__ import annotations

from flask import request, jsonify


def install(app=None):
    if app is None:
        print("[boot] patch_google_login_detail: no app")
        return

    endpoints = set()
    for rule in app.url_map.iter_rules():
        path = str(rule.rule).rstrip("/")
        if path == "/api/auth/google" and "POST" in (rule.methods or set()):
            endpoints.add(rule.endpoint)
    for name in list(app.view_functions.keys()):
        if "google" in name.lower() and "login" in name.lower():
            endpoints.add(name)
    endpoints.add("google_login")

    if not endpoints:
        print("[boot] patch_google_login_detail: no endpoints found")
        return

    try:
        from db.google_auth import (
            google_configured,
            GOOGLE_CLIENT_ID,
            verify_google_id_token,
            last_verify_error,
        )
    except ImportError:
        from db.google_auth import google_configured, GOOGLE_CLIENT_ID, verify_google_id_token

        def last_verify_error():
            return None

    import repo

    def _get_create_token():
        import sys

        for mod_name in ("server", "__main__", "server_core"):
            mod = sys.modules.get(mod_name)
            if mod and callable(getattr(mod, "create_user_token", None)):
                return getattr(mod, "create_user_token")
        try:
            from db.phase23_hooks import create_user_token as jwt_ct

            return jwt_ct
        except Exception:
            pass
        from db.auth_tokens import issue_user_token

        return issue_user_token

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
        try:
            if not google_configured():
                return jsonify({
                    "error": "Google OAuth танзим нашудааст.",
                    "detail": "GOOGLE_CLIENT_ID missing",
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
                err = None
                try:
                    err = last_verify_error()
                except Exception:
                    err = None
                return jsonify({
                    "error": "Google token нодуруст аст.",
                    "detail": err or "verify_failed",
                    "clientIdPrefix": (GOOGLE_CLIENT_ID[:24] + "\u2026") if GOOGLE_CLIENT_ID else None,
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

            if not user or not user.get("id"):
                return jsonify({
                    "error": "Корбар холӣ баромад.",
                    "detail": "upsert returned empty",
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
                return jsonify({"error": "Token холӣ.", "detail": "empty_token"}), 500

            return jsonify({"user": _public_user(user), "token": token, "ok": True})
        except Exception as e:
            return jsonify({
                "error": "Хатои дохилии Google login.",
                "detail": f"{type(e).__name__}: {e}",
            }), 500

    for ep in endpoints:
        if ep in app.view_functions:
            app.view_functions[ep] = google_login_patched
            print(f"[boot] patch_google_login_detail: replaced view {ep}")

    try:
        for rule in list(app.url_map.iter_rules()):
            if str(rule.rule).rstrip("/") == "/api/auth/google":
                app.view_functions[rule.endpoint] = google_login_patched
                print(f"[boot] patch_google_login_detail: rebound rule endpoint {rule.endpoint}")
    except Exception as e:
        print("[boot] patch_google_login_detail rebind warn:", e)

    print("[boot] patch_google_login_detail: done endpoints=", sorted(endpoints))
