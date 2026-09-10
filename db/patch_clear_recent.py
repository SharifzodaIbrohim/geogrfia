"""clear-recent: delete last 30 finished attempts from Neon."""
from __future__ import annotations
import logging
log = logging.getLogger("geografia.patch_clear_recent")
RECENT_LIMIT = 30

def install(app=None):
    if app is None:
        return
    from flask import jsonify, request

    def _require_admin():
        try:
            tok = (request.headers.get("X-Admin-Token") or request.headers.get("Authorization") or "").strip()
            if tok:
                return True
            if request.cookies.get("__Host-geografia_admin") or request.cookies.get("geografia_admin"):
                return True
        except Exception:
            pass
        return False

    def _engine():
        try:
            from db.connection import get_engine, is_postgres_enabled
            if is_postgres_enabled():
                return get_engine()
        except Exception:
            pass
        return None

    def _clear_recent():
        if not _require_admin():
            return jsonify({"error": "Дастрасӣ рад шуд."}), 401
        eng = _engine()
        if eng is None:
            return jsonify({"ok": False, "cleared": 0, "message": "PostgreSQL дастнорас"}), 500
        from sqlalchemy import text
        cleared = 0
        try:
            with eng.begin() as conn:
                ids = [r[0] for r in conn.execute(text(
                    "SELECT id::text FROM attempts WHERE finished_at IS NOT NULL "
                    "ORDER BY finished_at DESC NULLS LAST LIMIT :lim"
                ), {"lim": RECENT_LIMIT}).fetchall()]
                if not ids:
                    ids = [r[0] for r in conn.execute(text(
                        "SELECT id::text FROM attempts ORDER BY COALESCE(finished_at, started_at) DESC NULLS LAST LIMIT :lim"
                    ), {"lim": RECENT_LIMIT}).fetchall()]
                for aid in ids:
                    try:
                        conn.execute(text("DELETE FROM attempt_answers WHERE attempt_id::text = :id"), {"id": aid})
                    except Exception:
                        pass
                    try:
                        res = conn.execute(text("DELETE FROM attempts WHERE id::text = :id"), {"id": aid})
                        cleared += int(res.rowcount or 0)
                    except Exception:
                        pass
        except Exception as e:
            log.exception("clear-recent")
            return jsonify({"ok": False, "cleared": 0, "message": str(e)}), 500
        return jsonify({"ok": True, "cleared": cleared, "message": f"Пок шуд: {cleared} сабт"})

    def _clear_all():
        if not _require_admin():
            return jsonify({"error": "Дастрасӣ рад шуд."}), 401
        body = request.get_json(silent=True) or {}
        if str(body.get("confirm") or "").upper() != "DELETE_ALL":
            return jsonify({"ok": False, "message": "confirm=DELETE_ALL лозим аст"}), 403
        eng = _engine()
        if eng is None:
            return jsonify({"ok": False, "message": "PostgreSQL дастнорас"}), 500
        from sqlalchemy import text
        with eng.begin() as conn:
            try:
                conn.execute(text("DELETE FROM attempt_answers"))
            except Exception:
                pass
            n = int(conn.execute(text("DELETE FROM attempts")).rowcount or 0)
        return jsonify({"ok": True, "cleared": n, "message": f"Пок шуд: {n} сабт (ҳама)"})

    for name in list(app.view_functions.keys()):
        low = name.lower()
        if "clear_recent" in low or "clear-recent" in low:
            app.view_functions[name] = _clear_recent
        if "clear_all" in low:
            app.view_functions[name] = _clear_all
    existing = {r.rule for r in app.url_map.iter_rules()}
    if "/api/admin/results/clear-recent" not in existing:
        app.add_url_rule("/api/admin/results/clear-recent", "clear_recent_v3", _clear_recent, methods=["POST"])
    else:
        for r in app.url_map.iter_rules():
            if r.rule == "/api/admin/results/clear-recent":
                app.view_functions[r.endpoint] = _clear_recent
    if "/api/admin/monitor/clear-recent" not in existing:
        app.add_url_rule("/api/admin/monitor/clear-recent", "clear_recent_mon_v3", _clear_recent, methods=["POST"])
    if "/api/admin/results/clear-all" not in existing:
        app.add_url_rule("/api/admin/results/clear-all", "clear_all_v3", _clear_all, methods=["POST"])
    print("[boot] patch_clear_recent: hard delete recent ENABLED")
