"""Phase 17–18 routes: audit log + notifications."""
from __future__ import annotations

from flask import jsonify, request

from db import audit
from db import notifications
from db.rbac import deny_message


def register_audit_routes(app, require_perm, require_admin):
    @app.get("/api/admin/audit")
    def admin_audit_list():
        admin = require_perm("admins.read", "monitor.read")
        if admin is None:
            return jsonify({"error": "Дастрасӣ рад шуд."}), 401
        if admin is False:
            return jsonify({"error": deny_message("monitor.read")}), 403
        limit = request.args.get("limit") or 100
        try:
            limit = int(limit)
        except ValueError:
            limit = 100
        rows = audit.list_audit(
            limit=limit,
            action=request.args.get("action") or None,
            admin_login=request.args.get("admin") or None,
        )
        return jsonify({"logs": rows, "count": len(rows)})

    @app.get("/api/admin/notifications")
    def admin_notifications():
        admin = require_admin()
        if not admin:
            return jsonify({"error": "Дастрасӣ рад шуд."}), 401
        unread = request.args.get("unread") == "1"
        rows = notifications.list_notifications(
            audience="admin",
            unread_only=unread,
            limit=int(request.args.get("limit") or 50),
        )
        return jsonify({"notifications": rows, "count": len(rows)})

    @app.post("/api/admin/notifications/<notif_id>/read")
    def admin_notif_read(notif_id: str):
        admin = require_admin()
        if not admin:
            return jsonify({"error": "Дастрасӣ рад шуд."}), 401
        ok = notifications.mark_read(notif_id)
        if not ok:
            return jsonify({"error": "Ёфт нашуд."}), 404
        return jsonify({"ok": True})

    @app.post("/api/admin/notifications/test")
    def admin_notif_test():
        admin = require_perm("admins.write")
        if admin is None:
            return jsonify({"error": "Дастрасӣ рад шуд."}), 401
        if admin is False:
            return jsonify({"error": deny_message("admins.write")}), 403
        payload = request.get_json(silent=True) or {}
        n = notifications.create_notification(
            title=str(payload.get("title") or "Тести огоҳӣ"),
            body=str(payload.get("body") or "Phase 18 notification test"),
            link="/admin",
            audience="admin",
            email=payload.get("email"),
        )
        audit.log_action(
            action="notification.test",
            admin=admin,
            target_type="notification",
            target_id=n["id"],
            ip=request.headers.get("X-Forwarded-For", request.remote_addr),
        )
        return jsonify({"notification": n}), 201
