"""Boot patch: clear-recent hard-deletes finished attempts with engine.begin() commit."""
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

    def _clear_recent():
        if not _require_admin():
            return jsonify({"error": "Дастрасӣ рад шуд."}), 401

        cleared = 0
        details = []
        remaining = None
        eng = _pg_engine()

        if eng is not None:
            from sqlalchemy import text

            try:
                with eng.begin() as conn:
                    ids = []
                    for label, sql in (
                        (
                            "finished",
                            "SELECT id::text FROM attempts "
                            "WHERE finished_at IS NOT NULL "
                            "ORDER BY finished_at DESC NULLS LAST LIMIT 30",
                        ),
                        (
                            "status",
                            "SELECT id::text FROM attempts "
                            "WHERE status::text IN "
                            "('passed','failed','timeout','submitted','finished') "
                            "ORDER BY COALESCE(finished_at, started_at) DESC "
                            "NULLS LAST LIMIT 30",
                        ),
                    ):
                        try:
                            ids = [r[0] for r in conn.execute(text(sql)).fetchall()]
                            if ids:
                                details.append(f"{label}:{len(ids)}")
                                break
                        except Exception as e:
                            details.append(f"{label}_err:{e}")

                    if not ids:
                        details.append("no_ids")
                    else:
                        for aid in ids:
                            for q in (
                                "DELETE FROM attempt_answers WHERE attempt_id::text = :id",
                                "DELETE FROM attempt_answers WHERE attempt_id = CAST(:id AS uuid)",
                            ):
                                try:
                                    conn.execute(text(q), {"id": aid})
                                    break
                                except Exception:
                                    continue
                        for aid in ids:
                            deleted_one = False
                            for q in (
                                "DELETE FROM attempts WHERE id::text = :id",
                                "DELETE FROM attempts WHERE id = CAST(:id AS uuid)",
                            ):
                                try:
                                    res = conn.execute(text(q), {"id": aid})
                                    n = int(res.rowcount or 0)
                                    if n:
                                        cleared += n
                                        deleted_one = True
                                        break
                                except Exception as e:
                                    details.append(f"del_err:{aid}:{e}")
                            if not deleted_one:
                                details.append(f"miss:{aid}")
                        for aid in ids:
                            try:
                                conn.execute(
                                    text("DELETE FROM results WHERE id::text = :id"),
                                    {"id": aid},
                                )
                            except Exception:
                                pass

                    try:
                        remaining = int(
                            conn.execute(
                                text(
                                    "SELECT COUNT(*) FROM attempts "
                                    "WHERE status::text IN "
                                    "('passed','failed','timeout','submitted','finished')"
                                )
                            ).scalar()
                            or 0
                        )
                        details.append(f"remaining:{remaining}")
                    except Exception as e:
                        details.append(f"count_err:{e}")
                details.append("committed")
            except Exception as e:
                log.exception("PG clear-recent failed")
                details.append(f"pg_fail:{e}")
                return jsonify(
                    {"ok": False, "error": str(e), "details": details, "cleared": cleared}
                ), 500
        else:
            details.append("no_pg_engine")

        try:
            base = Path(__file__).resolve().parent.parent
            path = base / "data" / "results.json"
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
                        json.dumps(kept, ensure_ascii=False, indent=2), encoding="utf-8"
                    )
                    if cleared == 0:
                        cleared = max(0, before - len(kept))
                    details.append(f"json:{before}->{len(kept)}")
        except Exception as e:
            details.append(f"json_err:{e}")

        log.info("clear-recent cleared=%s details=%s", cleared, details)
        return jsonify(
            {
                "ok": True,
                "cleared": cleared,
                "remaining": remaining,
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
            from sqlalchemy import text
            try:
                with eng.begin() as conn:
                    try:
                        conn.execute(text("DELETE FROM attempt_answers"))
                    except Exception as e:
                        details.append(f"aa:{e}")
                    try:
                        res = conn.execute(
                            text(
                                "DELETE FROM attempts WHERE status::text IN "
                                "('passed','failed','timeout','submitted','finished') "
                                "OR finished_at IS NOT NULL"
                            )
                        )
                        cleared = int(res.rowcount or 0)
                    except Exception:
                        res = conn.execute(text("DELETE FROM attempts"))
                        cleared = int(res.rowcount or 0)
                    try:
                        conn.execute(text("DELETE FROM results"))
                    except Exception:
                        pass
                details.append("committed")
            except Exception as e:
                return jsonify({"ok": False, "error": str(e)}), 500
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
    else:
        for r in app.url_map.iter_rules():
            if r.rule == "/api/admin/results/clear-all":
                app.view_functions[r.endpoint] = _clear_all

    print("[boot] patch_clear_recent: engine.begin hard-delete installed")
    log.info("patch_clear_recent installed")
