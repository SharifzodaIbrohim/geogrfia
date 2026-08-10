"""Public + admin routes for Courses content."""
from __future__ import annotations

from flask import jsonify, request

from db import content_api


def register_content_routes(app, require_perm, require_admin):
    @app.get("/api/content")
    def public_content():
        try:
            kind = request.args.get("type") or None
            lang = request.args.get("lang") or None
            items = content_api.list_content(kind=kind, lang=lang)
            return jsonify({"items": items, "count": len(items)})
        except Exception as e:
            return jsonify({"items": [], "count": 0, "error": str(e)}), 200

    @app.get("/api/admin/content")
    def admin_list_content():
        try:
            admin = require_perm("content.write", "monitor.read", "students.read")
        except Exception:
            admin = None
        if admin is None:
            try:
                admin = require_admin()
            except Exception:
                admin = None
        if not admin:
            return jsonify({"error": "Дастрасӣ рад шуд."}), 401
        try:
            items = content_api.list_content()
            return jsonify({"items": items, "count": len(items)})
        except Exception as e:
            return jsonify({"items": [], "count": 0, "error": str(e)}), 200

    @app.post("/api/admin/content")
    def admin_add_content():
        try:
            admin = require_perm("content.write", "admins.write")
        except Exception:
            admin = None
        if admin is None:
            try:
                admin = require_admin()
            except Exception:
                admin = None
        if not admin:
            return jsonify({"error": "Дастрасӣ рад шуд."}), 401
        payload = request.get_json(silent=True) or {}
        try:
            item = content_api.add_content(payload)
        except ValueError:
            return jsonify({"error": "Унвон лозим аст."}), 400
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        return jsonify({"item": item}), 201

    @app.delete("/api/admin/content/<item_id>")
    def admin_del_content(item_id: str):
        try:
            admin = require_admin()
        except Exception:
            admin = None
        if not admin:
            return jsonify({"error": "Дастрасӣ рад шуд."}), 401
        try:
            if not content_api.delete_content(item_id):
                return jsonify({"error": "Ёфт нашуд."}), 404
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        return jsonify({"ok": True})
