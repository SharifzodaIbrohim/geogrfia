"""Public + admin routes for Courses content."""
from __future__ import annotations

from flask import jsonify, request

from db import content_api
from db.rbac import deny_message


def register_content_routes(app, require_perm, require_admin):
    @app.get("/api/content")
    def public_content():
        kind = request.args.get("type") or None
        lang = request.args.get("lang") or None
        items = content_api.list_content(kind=kind, lang=lang)
        return jsonify({"items": items, "count": len(items)})

    @app.get("/api/admin/content")
    def admin_list_content():
        admin = require_perm("content.write", "monitor.read", "students.read")
        if admin is None:
            return jsonify({"error": "Дастрасӣ рад шуд."}), 401
        if admin is False:
            admin = require_admin()
            if not admin:
                return jsonify({"error": "Дастрасӣ рад шуд."}), 401
        items = content_api.list_content()
        return jsonify({"items": items, "count": len(items)})

    @app.post("/api/admin/content")
    def admin_add_content():
        admin = require_perm("content.write", "admins.write")
        if admin is None:
            return jsonify({"error": "Дастрасӣ рад шуд."}), 401
        if admin is False:
            admin = require_admin()
            if not admin:
                return jsonify({"error": "Дастрасӣ рад шуд."}), 401
        payload = request.get_json(silent=True) or {}
        try:
            item = content_api.add_content(payload)
        except ValueError:
            return jsonify({"error": "Унвон лозим аст."}), 400
        return jsonify({"item": item}), 201

    @app.delete("/api/admin/content/<item_id>")
    def admin_del_content(item_id: str):
        admin = require_admin()
        if not admin:
            return jsonify({"error": "Дастрасӣ рад шуд."}), 401
        if not content_api.delete_content(item_id):
            return jsonify({"error": "Ёфт нашуд."}), 404
        return jsonify({"ok": True})
