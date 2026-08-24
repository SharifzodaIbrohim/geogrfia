"""Boot patch: clear-recent hard-deletes finished attempts with savepoints."""
from __future__ import annotations

import json
import logging
from pathlib import Path

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
        """Run SQL under SAVEPOINT so a failure does not abort the whole transaction."""
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

    def _clear_recent():
        if not _require_admin():
            return jsonify({"error": "Дастрасӣ рад шуд."}), 401

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
                            details.append(f"attempts2:{err2[:120]}")
                        else:
                            cleared = n
                            details.append(f"attempts_del:{n}")
                    else:
                        cleared = n
                        details.append(f"attempts_del:{n}")

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
                        details.append(f"results_skip:{err[:60]}")
                    else:
                        details.append(f"results_del:{n}")

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
                log.exception("PG clear-recent failed")
                details.append(f"pg_fail:{e}")
                return jsonify(
                    {
                        "ok": False,
                        "error": str(e),
                        "details": details,
                        "cleared": cleared,
                    }
                ), 500

        try:
            path = Path(__file__).resolve().parent.parent / "data" / "results.json"
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, list) and data:
                    before = len(data)
                    sorted_rows = sorted(
                        data,
                        key=lambda r: r.get("finishedAt") or r.get("finished_at") or "",
                        reverse=True,
                    )
                    kept = sorted_rows[30:]
                    path.write_text(
                        json.dumps(kept, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                    if cleared == 0:
                        cleared = max(0, before - len(kept))
                    details.append(f"json:{before}->{len(kept)}")
        except Exception as e:
            details.append(f"json_err:{e}")

        log.info(
            "clear-recent cleared=%s before=%s after=%s details=%s",
            cleared,
            remaining_before,
            remaining_after,
            details,
        )
        return jsonify(
            {
                "ok": True,
                "cleared": cleared,
                "before": remaining_before,
                "after": remaining_after,
                "details": details,
                "message": "Натиҷаҳои охирин пок шуданд",
            }
        )

    def _clear_all():
        if not _require_admin():
            return jsonify({"error": "Дастрасӣ рад шуд."}), 401
        cleared = 0
        details = []
        eng = _pg_engine()
        if eng is not None:
            try:
                with eng.begin() as conn:
                    n, err = _sp_exec(conn, "DELETE FROM attempt_answers")
                    if err:
                        details.append(f"aa:{err[:80]}")
                    n, err = _sp_exec(
                        conn, "DELETE FROM attempts WHERE finished_at IS NOT NULL"
                    )
                    if err:
                        n, err = _sp_exec(
                            conn,
                            "DELETE FROM attempts WHERE CAST(status AS text) NOT IN "
                            "('in_progress','started','active')",
                        )
                    cleared = n
                    if err:
                        details.append(f"att:{err[:80]}")
                    n, err = _sp_exec(conn, "DELETE FROM results")
                    if err:
                        details.append(f"res:{err[:60]}")
                details.append("committed")
            except Exception as e:
                return jsonify({"ok": False, "error": str(e), "details": details}), 500
        try:
            path = Path(__file__).resolve().parent.parent / "data" / "results.json"
            if path.exists():
                path.write_text("[]", encoding="utf-8")
        except Exception:
            pass
        return jsonify({"ok": True, "cleared": cleared, "details": details})

    app.view_functions["_clear_recent_results"] = _clear_recent
    app.view_functions["clear_recent_alias"] = _clear_recent
    for r in list(app.url_map.iter_rules()):
        if r.rule in (
            "/api/admin/results/clear-recent",
            "/api/admin/monitor/clear-recent",
        ):
            app.view_functions[r.endpoint] = _clear_recent
        if r.rule == "/api/admin/results/clear-all":
            app.view_functions[r.endpoint] = _clear_all
    for name in list(app.view_functions.keys()):
        if "clear_recent" in name.lower():
            app.view_functions[name] = _clear_recent
        if name in ("_clear_all_results", "clear_all_results"):
            app.view_functions[name] = _clear_all

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

    print("[boot] patch_clear_recent: savepoint hard-delete installed")
    log.info("patch_clear_recent installed")
