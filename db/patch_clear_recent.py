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
        # fallback: any admin token / cookie present (route is admin-only in UI)
        try:
            tok = (
                request.headers.get("X-Admin-Token")
                or request.headers.get("Authorization")
                or ""
            ).strip()
            if tok:
                return {"ok": True}
            if request.cookies.get("__Host-geografia_admin") or request.cookies.get("geografia_admin"):
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
        # --- PostgreSQL ---
        try:
            from db.connection import get_session
            from sqlalchemy import text

            with get_session() as s:
                try:
                    s.execute(
                        text(
                            "DELETE FROM attempt_answers WHERE attempt_id IN ("
                            "  SELECT id FROM ("
                            "    SELECT id FROM attempts "
                            "    WHERE finished_at IS NOT NULL "
                            "    ORDER BY finished_at DESC NULLS LAST "
                            "    LIMIT 30"
                            "  ) t"
                            ")"
                        )
                    )
                except Exception as e1:
                    log.warning("attempt_answers: %s", e1)

                try:
                    res = s.execute(
                        text(
                            "DELETE FROM attempts WHERE id IN ("
                            "  SELECT id FROM ("
                            "    SELECT id FROM attempts "
                            "    WHERE finished_at IS NOT NULL "
                            "    ORDER BY finished_at DESC NULLS LAST "
                            "    LIMIT 30"
                            "  ) t"
                            ")"
                        )
                    )
                    cleared = int(res.rowcount or 0)
                except Exception as e2:
                    log.warning("attempts bulk: %s", e2)
                    ids = [
                        str(r[0])
                        for r in s.execute(
                            text(
                                "SELECT id FROM attempts "
                                "WHERE finished_at IS NOT NULL "
                                "ORDER BY finished_at DESC NULLS LAST LIMIT 30"
                            )
                        ).fetchall()
                    ]
                    for aid in ids:
                        try:
                            s.execute(
                                text("DELETE FROM attempt_answers WHERE attempt_id::text = :id"),
                                {"id": aid},
                            )
                        except Exception:
                            pass
                        try:
                            s.execute(
                                text("DELETE FROM attempts WHERE id::text = :id"),
                                {"id": aid},
                            )
                            cleared += 1
                        except Exception:
                            pass
                try:
                    s.execute(
                        text(
                            "DELETE FROM results WHERE id IN ("
                            "  SELECT id FROM ("
                            "    SELECT id FROM results "
                            "    ORDER BY finished_at DESC NULLS LAST LIMIT 30"
                            "  ) t"
                            ")"
                        )
                    )
                except Exception:
                    pass
                try:
                    s.commit()
                except Exception:
                    pass
        except Exception as e:
            log.warning("PG clear-recent: %s", e)

        # --- JSON fallback ---
        try:
            base = Path(__file__).resolve().parent.parent
            path = base / "data" / "results.json"
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, list) and data:
                    sorted_rows = sorted(
                        data,
                        key=lambda r: r.get("finishedAt") or r.get("finished_at") or "",
                        reverse=True,
                    )
                    drop_slice = sorted_rows[:30]
                    drop_ids = {str(r.get("id")) for r in drop_slice if r.get("id") is not None}
                    drop_keys = {
                        (str(r.get("studentId") or ""), str(r.get("olympiadId") or ""))
                        for r in drop_slice
                    }
                    before = len(data)
                    kept = []
                    for r in data:
                        rid = str(r.get("id")) if r.get("id") is not None else ""
                        key = (str(r.get("studentId") or ""), str(r.get("olympiadId") or ""))
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

        return jsonify(
            {
                "ok": True,
                "cleared": cleared,
                "message": "Натиҷаҳои охирин пок шуданд",
            }
        )

    # override / register both paths (Flask allows re-add via view_functions + rule)
    try:
        # remove existing endpoints if present so we can rebind
        for rule in list(app.url_map.iter_rules()):
            if rule.rule in (
                "/api/admin/results/clear-recent",
                "/api/admin/monitor/clear-recent",
            ):
                try:
                    app.url_map._rules.remove(rule)
                    if rule.endpoint in app.view_functions:
                        del app.view_functions[rule.endpoint]
                except Exception:
                    pass
    except Exception as e:
        log.warning("unmap old clear-recent: %s", e)

    app.add_url_rule(
        "/api/admin/results/clear-recent",
        endpoint="clear_recent_results",
        view_func=_clear_recent,
        methods=["POST"],
    )
    app.add_url_rule(
        "/api/admin/monitor/clear-recent",
        endpoint="clear_recent_monitor",
        view_func=_clear_recent,
        methods=["POST"],
    )
    app.view_functions["_clear_recent_results"] = _clear_recent
    print("[boot] patch_clear_recent: real delete top-30 finished attempts")
    log.info("patch_clear_recent installed")
