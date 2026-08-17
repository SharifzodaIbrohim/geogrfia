"""UI/admin batch: showResults hide score, public_admin.role, public stats, clear-recent, live sessions."""
from __future__ import annotations
import logging
log = logging.getLogger("geografia.patch_ui_batch")

def install(app=None):
    try:
        import db.olympiad_engine as eng
        _submit = eng.submit_exam
        def submit_exam(*args, **kwargs):
            out = _submit(*args, **kwargs)
            if not isinstance(out, dict):
                return out
            try:
                oly_id = out.get("olympiadId") or (out.get("result") or {}).get("olympiadId")
                oly = eng.find_olympiad(oly_id) if oly_id else None
                show = True
                if oly is not None:
                    if "showResultsToStudents" in oly:
                        show = bool(oly.get("showResultsToStudents"))
                    elif "show_results_to_students" in oly:
                        show = bool(oly.get("show_results_to_students"))
                if not show:
                    msg = (
                        "Шумо бо муваффақият супоридед. "
                        "Лутфан интизор шавед, то баллҳоятон муайян шаванд."
                    )
                    return {
                        "ok": True,
                        "pendingReview": True,
                        "message": msg,
                        "status": "submitted",
                        "attemptId": out.get("attemptId") or (out.get("result") or {}).get("attemptId"),
                        "olympiadId": oly_id,
                        "result": {
                            "pendingReview": True,
                            "message": msg,
                            "status": "submitted",
                            "attemptId": out.get("attemptId"),
                            "olympiadId": oly_id,
                        },
                    }
            except Exception as e:
                log.warning("showResults filter: %s", e)
            return out
        eng.submit_exam = submit_exam
        log.info("submit_exam showResults filter installed")
    except Exception as e:
        log.warning("submit patch: %s", e)

    if app is None:
        print("[boot] patch_ui_batch: engine-only")
        return

    import sys
    for mod_name, mod in list(sys.modules.items()):
        if mod and hasattr(mod, "public_admin") and callable(getattr(mod, "public_admin")):
            _pa = mod.public_admin
            def public_admin(a, _orig=_pa):
                base = _orig(a) if _orig else {}
                if not isinstance(base, dict):
                    base = {}
                base["role"] = (a or {}).get("role") or base.get("role") or "monitor"
                return base
            try:
                mod.public_admin = public_admin
            except Exception:
                pass

    @app.get("/api/public/stats")
    def public_stats():
        try:
            import db.repo as repo
            students = repo.list_students()
            olympiads = repo.list_olympiads()
            active = sum(1 for o in olympiads if o.get("isActive"))
            return {
                "ok": True,
                "students": len(students),
                "olympiads": len(olympiads),
                "activeOlympiads": active,
            }
        except Exception as e:
            return {"ok": False, "students": 0, "error": str(e)}

    @app.post("/api/admin/monitor/clear-recent")
    def clear_recent_alias():
        from flask import jsonify
        fn = app.view_functions.get("_clear_recent_results")
        if fn:
            return fn()
        try:
            import db.repo as repo
            if hasattr(repo, "clear_recent_results"):
                repo.clear_recent_results()
            return jsonify({"ok": True})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    orig_monitor = app.view_functions.get("admin_monitor")
    if orig_monitor:
        def admin_monitor_wrapped():
            from flask import jsonify
            resp = orig_monitor()
            try:
                data = resp.get_json() if hasattr(resp, "get_json") else None
                if not isinstance(data, dict):
                    return resp
                if not data.get("liveSessions"):
                    live = []
                    try:
                        from sqlalchemy import text
                        from db.connection import get_session
                        with get_session() as s:
                            rows = s.execute(text(
                                "SELECT a.id::text AS id, a.student_id::text AS student_id, "
                                "a.olympiad_id::text AS olympiad_id, a.status::text AS status, "
                                "a.started_at, a.expires_at, "
                                "COALESCE(st.full_name, a.student_id::text) AS student_name, "
                                "COALESCE(o.title, a.olympiad_id::text) AS olympiad_title "
                                "FROM attempts a "
                                "LEFT JOIN students st ON (st.id::text = a.student_id::text OR st.student_code = a.student_id::text) "
                                "LEFT JOIN olympiads o ON o.id = a.olympiad_id "
                                "WHERE a.status::text = 'in_progress' "
                                "ORDER BY a.started_at DESC NULLS LAST LIMIT 50"
                            )).mappings().all()
                            for r in rows:
                                live.append({
                                    "studentName": r.get("student_name"),
                                    "studentId": r.get("student_id"),
                                    "olympiadTitle": r.get("olympiad_title"),
                                    "answered": "—",
                                    "startedAt": r["started_at"].isoformat() if r.get("started_at") else "",
                                    "expiresAt": r["expires_at"].isoformat() if r.get("expires_at") else "",
                                })
                    except Exception as e:
                        log.warning("live sessions: %s", e)
                    data["liveSessions"] = live
                return jsonify(data)
            except Exception:
                return resp
        app.view_functions["admin_monitor"] = admin_monitor_wrapped

    print("[boot] patch_ui_batch OK")
