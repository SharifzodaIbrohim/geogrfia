"""Boot patch: clear-recent actually deletes top 30 finished attempts (not UI-only)."""
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

    def _clear_recent():
        admin = None
        try:
            admin = _require_admin()
        except Exception as e:
            log.warning("require_admin: %s", e)
            admin = None
        if not admin:
            return jsonify({"error": "Дастрасӣ рад шуд."}), 401

        cleared = 0
        details = []

        # --- PostgreSQL ---
        try:
            from db.connection import get_session
            from sqlalchemy import text

            with get_session() as s:
                id_sqls = [
                    (
                        "finished",
                        "SELECT id FROM attempts "
                        "WHERE finished_at IS NOT NULL "
                        "ORDER BY finished_at DESC NULLS LAST LIMIT 30",
                    ),
                    (
                        "status",
                        "SELECT id FROM attempts "
                        "WHERE status::text IN ('passed','failed','timeout','submitted','finished') "
                        "ORDER BY COALESCE(finished_at, started_at) DESC NULLS LAST LIMIT 30",
                    ),
                    (
                        "any_done",
                        "SELECT id FROM attempts "
                        "WHERE status::text NOT IN ('in_progress','started','active') "
                        "OR finished_at IS NOT NULL "
                        "ORDER BY COALESCE(finished_at, started_at) DESC NULLS LAST LIMIT 30",
                    ),
                ]
                ids = []
                for label, sql in id_sqls:
                    try:
                        rows = s.execute(text(sql)).fetchall()
                        ids = [str(r[0]) for r in rows]
                        if ids:
                            details.append(f"{label}:{len(ids)}")
                            break
                    except Exception as e:
                        details.append(f"{label}_err:{e}")
                        log.warning("id select %s: %s", label, e)

                if ids:
                    for aid in ids:
                        try:
                            s.execute(
                                text(
                                    "DELETE FROM attempt_answers WHERE attempt_id::text = :id"
                                ),
                                {"id": aid},
                            )
                        except Exception:
                            try:
                                s.execute(
                                    text(
                                        "DELETE FROM attempt_answers WHERE attempt_id = CAST(:id AS uuid)"
                                    ),
                                    {"id": aid},
                                )
                            except Exception:
                                pass
                        try:
                            res = s.execute(
                                text("DELETE FROM attempts WHERE id::text = :id"),
                                {"id": aid},
                            )
                            if res.rowcount:
                                cleared += int(res.rowcount)
                        except Exception:
                            try:
                                res = s.execute(
                                    text(
                                        "DELETE FROM attempts WHERE id = CAST(:id AS uuid)"
                                    ),
                                    {"id": aid},
                                )
                                if res.rowcount:
                                    cleared += int(res.rowcount)
                            except Exception as e:
                                log.warning("delete attempt %s: %s", aid, e)
                    try:
                        for aid in ids:
                            s.execute(
                                text("DELETE FROM results WHERE id::text = :id"),
                                {"id": aid},
                            )
                    except Exception:
                        pass
                else:
                    details.append("no_ids")
        except Exception as e:
            log.warning("PG clear-recent: %s", e)
            details.append(f"pg:{e}")

        # --- JSON fallback ---
        try:
            base = Path(__file__).resolve().parent.parent
            path = base / "data" / "results.json"
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, list) and data:
                    sorted_rows = sorted(
                        data,
                        key=lambda r: r.get("finishedAt")
                        or r.get("finished_at")
                        or "",
                        reverse=True,
                    )
                    drop_slice = sorted_rows[:30]
                    drop_ids = {
                        str(r.get("id")) for r in drop_slice if r.get("id") is not None
                    }
                    drop_keys = {
                        (
                            str(r.get("studentId") or ""),
                            str(r.get("olympiadId") or ""),
                        )
                        for r in drop_slice
                    }
                    before = len(data)
                    kept = []
                    for r in data:
                        rid = str(r.get("id")) if r.get("id") is not None else ""
                        key = (
                            str(r.get("studentId") or ""),
                            str(r.get("olympiadId") or ""),
                        )
                        if rid and rid in drop_ids:
                            continue
                        if key in drop_keys and (key[0] or key[1]):
                            continue
                        kept.append(r)
                    if len(kept) == before:
                        kept = sorted_rows[30:]
                    path.write_text(
                        json.dumps(kept, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                    if cleared == 0:
                        cleared = max(0, before - len(kept))
        except Exception as e:
            log.warning("JSON clear-recent: %s", e)

        log.info("clear-recent cleared=%s details=%s", cleared, details)
        return jsonify(
            {
                "ok": True,
                "cleared": cleared,
                "details": details,
                "message": "Натиҷаҳои охирин пок шуданд",
            }
        )

    # CRITICAL: do NOT remove url_map rules (breaks clear_recent_alias).
    # Only rebind view_functions so existing routes call the real delete.
    app.view_functions["_clear_recent_results"] = _clear_recent
    for ep in list(app.view_functions.keys()):
        if "clear_recent" in ep.lower() or ep in (
            "_clear_recent_results",
            "clear_recent_alias",
            "clear_recent_results",
            "clear_recent_monitor",
        ):
            app.view_functions[ep] = _clear_recent

    app.view_functions["clear_recent_alias"] = _clear_recent
    app.view_functions["_clear_recent_results"] = _clear_recent

    existing = {r.rule for r in app.url_map.iter_rules()}
    if "/api/admin/results/clear-recent" not in existing:
        app.add_url_rule(
            "/api/admin/results/clear-recent",
            endpoint="clear_recent_results",
            view_func=_clear_recent,
            methods=["POST"],
        )
    else:
        for rule in app.url_map.iter_rules():
            if rule.rule == "/api/admin/results/clear-recent":
                app.view_functions[rule.endpoint] = _clear_recent

    if "/api/admin/monitor/clear-recent" not in existing:
        app.add_url_rule(
            "/api/admin/monitor/clear-recent",
            endpoint="clear_recent_monitor",
            view_func=_clear_recent,
            methods=["POST"],
        )
    else:
        for rule in app.url_map.iter_rules():
            if rule.rule == "/api/admin/monitor/clear-recent":
                app.view_functions[rule.endpoint] = _clear_recent

    print("[boot] patch_clear_recent: real delete top-30 (view_functions rebound)")
    log.info("patch_clear_recent installed")
