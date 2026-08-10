"""Install public /api/leaderboard so leaderboard.html does not get HTML 404."""
from __future__ import annotations

import logging

log = logging.getLogger("geografia.leaderboard_install")


def install(app) -> None:
    from flask import jsonify, request

    def public_leaderboard():
        try:
            from db import leaderboard_api as lb
            settings = lb.get_settings()
            if settings.get("public") is False:
                return jsonify({"error": "Leaderboard пӯшида аст.", "entries": []}), 403
            entries = []
            if hasattr(lb, "build_leaderboard"):
                entries = lb.build_leaderboard() or []
            elif hasattr(lb, "list_entries"):
                entries = lb.list_entries() or []
            elif hasattr(lb, "get_leaderboard"):
                entries = lb.get_leaderboard() or []
            else:
                # Fallback: aggregate from attempts if available
                entries = _from_attempts()
            if not entries and settings.get("useDemo", True) and hasattr(lb, "_DEMO"):
                entries = list(lb._DEMO)
            return jsonify({
                "entries": entries,
                "settings": {
                    "title": settings.get("title") or "Leaderboard",
                    "showSchool": settings.get("showSchool", True),
                    "showClass": settings.get("showClass", True),
                },
            })
        except Exception as e:
            log.exception("leaderboard")
            return jsonify({"entries": [], "error": str(e)[:200]})

    def _from_attempts():
        try:
            from sqlalchemy import text
            from db.connection import get_session, is_postgres_enabled
            if not is_postgres_enabled():
                return []
            with get_session() as s:
                rows = s.execute(text(
                    "SELECT COALESCE(student_name, 'Иштирокчӣ') AS name, "
                    "student_school AS school, student_class AS class_name, "
                    "MAX(score) AS best, COUNT(*) AS contests "
                    "FROM attempts WHERE status IN ('passed','failed','submitted') "
                    "AND student_name IS NOT NULL "
                    "GROUP BY student_name, student_school, student_class "
                    "ORDER BY best DESC NULLS LAST LIMIT 50"
                )).mappings().all()
                return [{
                    "id": f"att-{i}",
                    "name": r["name"],
                    "school": r["school"] or "",
                    "className": r["class_name"] or "",
                    "rating": int(r["best"] or 0) * 10 + 1000,
                    "solved": int(r["contests"] or 0),
                    "contests": int(r["contests"] or 0),
                    "score": r["best"],
                } for i, r in enumerate(rows)]
        except Exception as e:
            log.warning("attempts leaderboard: %s", e)
            return []

    # Bind under several endpoint names the frontend might use
    app.view_functions["public_leaderboard"] = public_leaderboard
    has = False
    for r in list(app.url_map.iter_rules()):
        if r.rule in ("/api/leaderboard", "/api/leaderboard/") and "GET" in (r.methods or set()):
            app.view_functions[r.endpoint] = public_leaderboard
            has = True
    if not has:
        try:
            app.add_url_rule("/api/leaderboard", "public_leaderboard", public_leaderboard, methods=["GET"])
        except AssertionError:
            app.view_functions["public_leaderboard"] = public_leaderboard

    log.info("public /api/leaderboard installed")
