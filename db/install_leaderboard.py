"""Install public + admin leaderboard routes."""
from __future__ import annotations

import logging

log = logging.getLogger("geografia.leaderboard_install")


def _with_ranks(entries: list) -> list:
    out = []
    for i, e in enumerate(entries or []):
        row = dict(e) if isinstance(e, dict) else {"name": str(e)}
        row["rank"] = int(row.get("rank") or (i + 1))
        out.append(row)
    return out


def _require_admin():
    from flask import request, jsonify
    token = request.headers.get("X-Admin-Token") or ""
    admin = None
    try:
        from db.auth_tokens import admin_from_token
        from db.admin_role import enrich_admin
        admin = enrich_admin(admin_from_token(token))
    except Exception:
        admin = None
    if not admin:
        # cookie session may set g.admin via before_request bridge
        try:
            from flask import g
            admin = getattr(g, "admin", None)
        except Exception:
            pass
    if not admin:
        return None, (jsonify({"error": "Дастрасӣ рад шуд."}), 401)
    return admin, None


def install(app) -> None:
    from flask import jsonify, request

    def public_leaderboard():
        try:
            from db import leaderboard_api as lb

            if hasattr(lb, "build_global_leaderboard"):
                data = lb.build_global_leaderboard(limit=100, public_only=True)
                return jsonify(data)
            settings = lb.get_settings()
            if settings.get("public") is False:
                return jsonify({"error": "Leaderboard пӯшида аст.", "entries": []}), 403
            entries = []
            if hasattr(lb, "build_leaderboard"):
                entries = lb.build_leaderboard() or []
            entries = _with_ranks(entries)
            if hasattr(lb, "apply_privacy"):
                entries = lb.apply_privacy(entries, settings)
            return jsonify({
                "entries": entries,
                "total": len(entries),
                "settings": {
                    "title": settings.get("title") or "Leaderboard",
                    "showSchool": settings.get("showSchool", True),
                    "showClass": settings.get("showClass", True),
                    "showScore": settings.get("showScore", True),
                    "hideNames": settings.get("hideNames", False),
                    "public": settings.get("public", True),
                },
            })
        except Exception as e:
            log.exception("leaderboard")
            return jsonify({"entries": [], "error": str(e)[:200]})

    def admin_lb_settings_get():
        admin, err = _require_admin()
        if err:
            return err
        from db import leaderboard_api as lb
        s = lb.get_settings()
        return jsonify(s)

    def admin_lb_settings_post():
        admin, err = _require_admin()
        if err:
            return err
        from db import leaderboard_api as lb
        payload = request.get_json(silent=True) or {}
        s = lb.update_settings(payload)
        return jsonify(s)

    def admin_lb_list():
        admin, err = _require_admin()
        if err:
            return err
        from db import leaderboard_api as lb
        limit = 100
        try:
            limit = int(request.args.get("limit") or 100)
        except Exception:
            pass
        if hasattr(lb, "build_global_leaderboard"):
            data = lb.build_global_leaderboard(limit=limit, public_only=False)
            return jsonify(data)
        settings = lb.get_settings()
        entries = lb.build_leaderboard() if hasattr(lb, "build_leaderboard") else []
        entries = _with_ranks(entries or [])
        return jsonify({"entries": entries, "settings": settings, "total": len(entries)})

    # public
    try:
        app.add_url_rule("/api/leaderboard", "public_leaderboard_v2", public_leaderboard, methods=["GET"])
    except AssertionError:
        app.view_functions["public_leaderboard_v2"] = public_leaderboard
        for r in list(app.url_map.iter_rules()):
            if r.rule in ("/api/leaderboard", "/api/leaderboard/") and "GET" in (r.methods or set()):
                app.view_functions[r.endpoint] = public_leaderboard

    # admin settings
    for rule, endpoint, view, methods in [
        ("/api/admin/leaderboard/settings", "admin_lb_settings_get", admin_lb_settings_get, ["GET"]),
        ("/api/admin/leaderboard/settings", "admin_lb_settings_post", admin_lb_settings_post, ["POST"]),
        ("/api/admin/leaderboard", "admin_lb_list", admin_lb_list, ["GET"]),
    ]:
        try:
            app.add_url_rule(rule, endpoint, view, methods=methods)
        except AssertionError:
            app.view_functions[endpoint] = view

    log.info("leaderboard public + admin settings routes installed")
