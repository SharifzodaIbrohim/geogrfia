"""Boot patch: clear-recent is SAFE by default — no hard DELETE without explicit confirm.

Why results vanished:
  - Button «Пок кардан» called POST /api/admin/*/clear-recent
  - Old handler hard-deleted the last 30 finished attempts from PostgreSQL
  - Confirm dialog was weak; admin.js + admin-fixes both bound the same button

New behavior:
  - Default (no body.confirm): soft only — does NOT touch the database
  - Hard delete only when body is {"confirm":"DELETE"} (exact string)
  - clear-all still requires {"confirm":"DELETE_ALL"}
  - Admin auth still required
  - Scoring / olympiad / review APIs unchanged
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
            tok = (
                request.headers.get("X-Admin-Token")
                or request.headers.get("Authorization")
                or ""
            ).strip()
            if tok:
                return {"ok": True}
            if request.cookies.get("__Host-geografia_admin") or request.cookies.get(
                "geografia_admin"
            ):
                return {"ok": True}
        except Exception:
            pass
        return None

    def _pg_engine():
        try:
            from db.connection import engine, is_postgres_enabled

            if is_postgres_enabled() and engine is not None:
                return engine
        except Exception as e:
            log.warning("engine: %s", e)
        return None

    def _sp_exec(conn, sql, params=None):
        from sqlalchemy import text

        sp = conn.begin_nested()
        try:
            res = conn.execute(text(sql), params or {})
            sp.commit()
            return int(res.rowcount or 0), None
        except Exception as e:
            try:
                sp.rollback()
            except Exception:
                pass
            return 0, str(e)

    def _parse_body():
        try:
            data = request.get_json(silent=True) or {}
            if not isinstance(data, dict):
                data = {}
        except Exception:
            data = {}
        return data

    def _clear_recent():
        """Soft by default. Hard delete only with confirm=DELETE."""
        if not _require_admin():
            return jsonify({"error": "Дастрасӣ рад шуд."}), 401

        body = _parse_body()
        confirm = str(body.get("confirm") or body.get("hard") or "").strip()
        hard = confirm == "DELETE"

        if not hard:
            return jsonify(
                {
                    "ok": True,
                    "soft": True,
                    "cleared": 0,
                    "message": "Рӯйхат аз нав бор шавад. База тағйир наёфт. "
                    "Барои нест кардан аз база confirm=DELETE лозим аст.",
                }
            )

        cleared = 0
        details = []
        remaining_before = None
        remaining_after = None
        eng = _pg_engine()

        if eng is None:
            details.append("no_pg_engine")
        else:
            from sqlalchemy import text

            try:
                with eng.begin() as conn:
                    try:
                        remaining_before = int(
                            conn.execute(
                                text(
                                    "SELECT COUNT(*) FROM attempts "
                                    "WHERE finished_at IS NOT NULL"
                                )
                            ).scalar()
                            or 0
                        )
                    except Exception as e:
                        details.append(f"count_before_err:{e}")

                    n, err = _sp_exec(
                        conn,
                        "DELETE FROM attempt_answers WHERE attempt_id IN ("
                        "  SELECT id FROM ("
                        "    SELECT id FROM attempts "
                        "    WHERE finished_at IS NOT NULL "
                        "    ORDER BY finished_at DESC NULLS LAST "
                        "    LIMIT 30"
                        "  ) t"
                        ")",
                    )
                    if err:
                        details.append(f"answers:{err[:120]}")
                    else:
                        details.append(f"answers_del:{n}")

                    n, err = _sp_exec(
                        conn,
                        "DELETE FROM attempts WHERE id IN ("
                        "  SELECT id FROM ("
                        "    SELECT id FROM attempts "
                        "    WHERE finished_at IS NOT NULL "
                        "    ORDER BY finished_at DESC NULLS LAST "
                        "    LIMIT 30"
                        "  ) t"
                        ")",
                    )
                    if err:
                        details.append(f"attempts:{err[:120]}")
                        n, err2 = _sp_exec(
                            conn,
                            "DELETE FROM attempts WHERE id IN ("
                            "  SELECT id FROM ("
                            "    SELECT id FROM attempts "
                            "    WHERE CAST(status AS text) IN "
                            "    ('passed','failed','timeout','submitted','finished') "
                            "    ORDER BY COALESCE(finished_at, started_at) DESC NULLS LAST "
                            "    LIMIT 30"
                            "  ) t"
                            ")",
                        )
                        if err2:
                            details.append(f"attempts_fallback:{err2[:120]}")
                        else:
                            cleared = n
                            details.append(f"attempts_del:{n}")
                    else:
                        cleared = n
                        details.append(f"attempts_del:{n}")

                    try:
                        n, err = _sp_exec(
                            conn,
                            "DELETE FROM results WHERE id IN ("
                            "  SELECT id FROM ("
                            "    SELECT id FROM results "
                            "    ORDER BY 1 DESC LIMIT 30"
                            "  ) t"
                            ")",
                        )
                        if err:
                            details.append(f"results:{err[:80]}")
                        else:
                            details.append(f"results_del:{n}")
                    except Exception as e:
                        details.append(f"results_skip:{e}")

                    try:
                        remaining_after = int(
                            conn.execute(
                                text(
                                    "SELECT COUNT(*) FROM attempts "
                                    "WHERE finished_at IS NOT NULL"
                                )
                            ).scalar()
                            or 0
                        )
                    except Exception as e:
                        details.append(f"count_after_err:{e}")
                details.append("committed")
            except Exception as e:
                details.append(f"tx_err:{e}")
                log.error("clear-recent hard failed: %s", e)

        log.warning(
            "HARD clear-recent by admin: cleared=%s before=%s after=%s details=%s",
            cleared,
            remaining_before,
            remaining_after,
            details,
        )
        return jsonify(
            {
                "ok": True,
                "hard": True,
                "cleared": cleared,
                "remainingBefore": remaining_before,
                "remainingAfter": remaining_after,
                "details": details,
                "message": f"Пок шуд: {cleared} сабт (охирин 30 finished).",
            }
        )

    def _clear_all():
        if not _require_admin():
            return jsonify({"error": "Дастрасӣ рад шуд."}), 401
        body = _parse_body()
        confirm = str(body.get("confirm") or "").strip()
        if confirm != "DELETE_ALL":
            return jsonify(
                {
                    "ok": False,
                    "error": "Барои пок кардани ҳама confirm=DELETE_ALL лозим аст.",
                }
            ), 400

        cleared = 0
        details = []
        eng = _pg_engine()
        if eng is not None:
            from sqlalchemy import text

            try:
                with eng.begin() as conn:
                    n, err = _sp_exec(conn, "DELETE FROM attempt_answers")
                    details.append(f"answers:{n if not err else err[:80]}")
                    n, err = _sp_exec(conn, "DELETE FROM attempts WHERE finished_at IS NOT NULL")
                    if err:
                        n, err = _sp_exec(
                            conn,
                            "DELETE FROM attempts WHERE CAST(status AS text) IN "
                            "('passed','failed','timeout','submitted','finished')",
                        )
                    cleared = n
                    details.append(f"attempts:{n if not err else err[:80]}")
                    try:
                        n2, err2 = _sp_exec(conn, "DELETE FROM results")
                        details.append(f"results:{n2 if not err2 else err2[:80]}")
                    except Exception:
                        pass
            except Exception as e:
                details.append(f"tx:{e}")
                log.error("clear-all failed: %s", e)

        log.warning("HARD clear-all by admin: cleared=%s details=%s", cleared, details)
        return jsonify(
            {
                "ok": True,
                "cleared": cleared,
                "details": details,
                "message": f"Пок шуд: {cleared} сабт (ҳама finished).",
            }
        )

    for name in list(app.view_functions.keys()):
        low = name.lower()
        if "clear_recent" in low or "clear-recent" in low:
            app.view_functions[name] = _clear_recent
        if name in ("_clear_all_results", "clear_all_results") or "clear_all" in low:
            app.view_functions[name] = _clear_all

    for r in list(app.url_map.iter_rules()):
        if r.rule in (
            "/api/admin/results/clear-recent",
            "/api/admin/monitor/clear-recent",
        ):
            app.view_functions[r.endpoint] = _clear_recent
        if r.rule == "/api/admin/results/clear-all":
            app.view_functions[r.endpoint] = _clear_all

    existing = {r.rule for r in app.url_map.iter_rules()}
    if "/api/admin/results/clear-recent" not in existing:
        app.add_url_rule(
            "/api/admin/results/clear-recent",
            "clear_recent_results",
            _clear_recent,
            methods=["POST"],
        )
    if "/api/admin/monitor/clear-recent" not in existing:
        app.add_url_rule(
            "/api/admin/monitor/clear-recent",
            "clear_recent_monitor",
            _clear_recent,
            methods=["POST"],
        )
    if "/api/admin/results/clear-all" not in existing:
        app.add_url_rule(
            "/api/admin/results/clear-all",
            "clear_all_results",
            _clear_all,
            methods=["POST"],
        )

    print("[boot] patch_clear_recent: SAFE soft-default + confirm=DELETE hard")
    log.info("patch_clear_recent installed (soft default)")
