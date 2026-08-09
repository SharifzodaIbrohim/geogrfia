"""Profile + admin Gmail users monitoring routes."""
from __future__ import annotations

from flask import jsonify, request

from db import profile_api
from db.rbac import deny_message


def register_profile_routes(app, require_user, require_perm, require_admin):
    @app.get("/api/me/profile")
    def me_profile():
        user = require_user()
        if not user:
            return jsonify({"error": "Аввал ворид шавед."}), 401
        uid = str(user.get("id") or "")
        profile = profile_api.get_user_by_id(uid) or {
            "id": uid,
            "email": user.get("email"),
            "name": user.get("name"),
            "picture": user.get("picture") or user.get("avatarUrl"),
            "profileComplete": False,
            "rating": 1200,
            "maxRating": 1200,
            "kind": "gmail",
        }
        stats = profile_api.user_quiz_stats(uid)
        return jsonify({"profile": profile, "stats": stats, "needsOnboarding": not profile.get("profileComplete")})

    @app.patch("/api/me/profile")
    def me_profile_update():
        user = require_user()
        if not user:
            return jsonify({"error": "Аввал ворид шавед."}), 401
        payload = request.get_json(silent=True) or {}
        uid = str(user.get("id") or "")
        updated = profile_api.update_profile(uid, payload)
        if not updated:
            return jsonify({"error": "Навсозӣ нашуд."}), 400
        return jsonify({"profile": updated, "needsOnboarding": not updated.get("profileComplete")})

    @app.get("/api/admin/gmail-users")
    def admin_gmail_users():
        admin = require_perm("students.read", "monitor.read", "users.read")
        if admin is None:
            return jsonify({"error": "Дастрасӣ рад шуд."}), 401
        if admin is False:
            # fallback monitor
            admin = require_perm("monitor.read")
            if admin is None:
                return jsonify({"error": "Дастрасӣ рад шуд."}), 401
            if admin is False:
                return jsonify({"error": deny_message("students.read")}), 403
        rows = profile_api.list_gmail_users(
            school=request.args.get("school") or None,
            region=request.args.get("region") or None,
            gender=request.args.get("gender") or None,
            limit=int(request.args.get("limit") or 200),
        )
        # attach light stats
        out = []
        for u in rows:
            st = profile_api.user_quiz_stats(u["id"])
            out.append({**u, "stats": {"passed": st["passed"], "failed": st["failed"], "attempts": st["attempts"]}})
        return jsonify({"users": out, "count": len(out), "kind": "gmail"})
