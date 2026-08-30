"""clear-recent: NEVER hard-deletes from PostgreSQL.

Admin button only refreshes the UI list.
Physical delete of results is disabled to stop accidental data loss.
Use a separate super-admin tool if true purge is ever needed.
"""
from __future__ import annotations
import logging
log = logging.getLogger("geografia.patch_clear_recent")

def install(app=None):
    if app is None:
        return
    from flask import jsonify, request

    def _require_admin():
        for modname in ("db.phase23_hooks", "db.session_cookies"):
            try:
                mod = __import__(modname, fromlist=["require_admin"])
                fn = getattr(mod, "require_admin", None)
                if fn:
                    return fn()
            except Exception:
                continue
        try:
            tok = (request.headers.get("X-Admin-Token") or request.headers.get("Authorization") or "").strip()
            if tok:
                return {"ok": True}
            if request.cookies.get("__Host-geografia_admin") or request.cookies.get("geografia_admin"):
                return {"ok": True}
        except Exception:
            pass
        return None

    def _clear_recent():
        if not _require_admin():
            return jsonify({"error": "Дастрасӣ рад шуд."}), 401
        # HARD DELETE DISABLED — results must stay in PostgreSQL
        body = {}
        try:
            body = request.get_json(silent=True) or {}
        except Exception:
            body = {}
        confirm = str(body.get("confirm") or "").strip()
        if confirm in ("DELETE", "DELETE_ALL", "DELETE_HARD"):
            log.warning("clear-recent hard DELETE blocked (disabled). confirm=%s", confirm)
            return jsonify({
                "ok": False,
                "blocked": True,
                "cleared": 0,
                "message": "Нест кардан аз база ғайрифаъол аст. Натиҷаҳо дар PostgreSQL мемонанд. "
                           "Танҳо рӯйхат нав карда мешавад.",
            })
        return jsonify({
            "ok": True,
            "soft": True,
            "cleared": 0,
            "message": "Рӯйхат нав шуд. База тағйир наёфт — натиҷаҳо нигоҳ дошта шуданд.",
        })

    def _clear_all():
        if not _require_admin():
            return jsonify({"error": "Дастрасӣ рад шуд."}), 401
        log.warning("clear-all blocked (hard delete disabled)")
        return jsonify({
            "ok": False,
            "blocked": True,
            "cleared": 0,
            "message": "Пок кардани ҳама аз база ғайрифаъол аст.",
        }), 403

    for name in list(app.view_functions.keys()):
        low = name.lower()
        if "clear_recent" in low or "clear-recent" in low:
            app.view_functions[name] = _clear_recent
        if "clear_all" in low:
            app.view_functions[name] = _clear_all

    for r in list(app.url_map.iter_rules()):
        if r.rule in ("/api/admin/results/clear-recent", "/api/admin/monitor/clear-recent"):
            app.view_functions[r.endpoint] = _clear_recent
        if r.rule == "/api/admin/results/clear-all":
            app.view_functions[r.endpoint] = _clear_all

    existing = {r.rule for r in app.url_map.iter_rules()}
    if "/api/admin/results/clear-recent" not in existing:
        app.add_url_rule("/api/admin/results/clear-recent", "clear_recent_results", _clear_recent, methods=["POST"])
    if "/api/admin/monitor/clear-recent" not in existing:
        app.add_url_rule("/api/admin/monitor/clear-recent", "clear_recent_monitor", _clear_recent, methods=["POST"])
    if "/api/admin/results/clear-all" not in existing:
        app.add_url_rule("/api/admin/results/clear-all", "clear_all_results", _clear_all, methods=["POST"])

    print("[boot] patch_clear_recent: HARD DELETE DISABLED — soft UI refresh only")
    log.info("patch_clear_recent: hard delete disabled")
