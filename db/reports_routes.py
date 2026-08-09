"""Phase 13–16 routes — live monitor, filtered results, leaderboard, CSV export."""
from __future__ import annotations

from flask import jsonify, request, Response

from db import reports_api
from db.rbac import deny_message


def register_reports_routes(app, require_perm, require_admin):
    @app.get("/api/admin/live")
    def admin_live():
        admin = require_perm("monitor.read", "results.read")
        if admin is None:
            return jsonify({"error": "Дастрасӣ рад шуд."}), 401
        if admin is False:
            return jsonify({"error": deny_message("monitor.read")}), 403
        return jsonify(reports_api.live_monitor())

    @app.get("/api/admin/results")
    def admin_results_filtered():
        admin = require_perm("results.read", "monitor.read")
        if admin is None:
            return jsonify({"error": "Дастрасӣ рад шуд."}), 401
        if admin is False:
            return jsonify({"error": deny_message("results.read")}), 403
        args = request.args
        min_score = args.get("minScore")
        max_score = args.get("maxScore")
        try:
            min_score = int(min_score) if min_score not in (None, "") else None
            max_score = int(max_score) if max_score not in (None, "") else None
        except ValueError:
            return jsonify({"error": "minScore/maxScore рақам бошанд."}), 400
        rows = reports_api.filter_results(
            olympiad_id=args.get("olympiadId") or None,
            school=args.get("school") or None,
            class_name=args.get("class") or None,
            status=args.get("status") or None,
            min_score=min_score,
            max_score=max_score,
        )
        return jsonify({"results": rows, "count": len(rows)})

    @app.get("/api/admin/results/export")
    def admin_results_export():
        admin = require_perm("results.read")
        if admin is None:
            return jsonify({"error": "Дастрасӣ рад шуд."}), 401
        if admin is False:
            return jsonify({"error": deny_message("results.read")}), 403
        args = request.args
        csv_text = reports_api.results_csv(
            olympiad_id=args.get("olympiadId") or None,
            school=args.get("school") or None,
            class_name=args.get("class") or None,
            status=args.get("status") or None,
        )
        return Response(
            "\ufeff" + csv_text,
            mimetype="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": "attachment; filename=results.csv",
            },
        )

    @app.get("/api/olympiads/<olympiad_id>/leaderboard")
    def public_leaderboard(olympiad_id: str):
        try:
            data = reports_api.leaderboard(
                olympiad_id,
                limit=int(request.args.get("limit") or 50),
                school=request.args.get("school") or None,
            )
        except ValueError:
            return jsonify({"error": "Ёфт нашуд."}), 404
        if not data.get("leaderboardPublic"):
            admin = require_admin()
            if not admin:
                return jsonify({"error": "Leaderboard хусусӣ аст.", "leaderboardPublic": False}), 403
        return jsonify(data)

    @app.get("/api/admin/olympiads/<olympiad_id>/leaderboard")
    def admin_leaderboard(olympiad_id: str):
        admin = require_perm("results.read", "monitor.read")
        if admin is None:
            return jsonify({"error": "Дастрасӣ рад шуд."}), 401
        if admin is False:
            return jsonify({"error": deny_message("results.read")}), 403
        try:
            data = reports_api.leaderboard(
                olympiad_id,
                limit=int(request.args.get("limit") or 100),
                school=request.args.get("school") or None,
            )
        except ValueError:
            return jsonify({"error": "Ёфт нашуд."}), 404
        return jsonify(data)

    @app.patch("/api/admin/olympiads/<olympiad_id>/leaderboard")
    def admin_leaderboard_visibility(olympiad_id: str):
        admin = require_perm("olympiads.write")
        if admin is None:
            return jsonify({"error": "Дастрасӣ рад шуд."}), 401
        if admin is False:
            return jsonify({"error": deny_message("olympiads.write")}), 403
        payload = request.get_json(silent=True) or {}
        is_public = bool(payload.get("public", True))
        o = reports_api.set_leaderboard_public(olympiad_id, is_public)
        if not o:
            return jsonify({"error": "Ёфт нашуд."}), 404
        return jsonify({"ok": True, "leaderboardPublic": is_public})
