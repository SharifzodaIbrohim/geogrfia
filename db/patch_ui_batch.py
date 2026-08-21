"""UI batch: showResults hide score, public stats, clear-recent, live sessions, public_admin.role."""
from __future__ import annotations
import logging
log = logging.getLogger("geografia.patch_ui_batch")

def install(app=None):
    try:
        import db.olympiad_engine as eng
        _submit = eng.submit_exam

        def _show_results_flag(oly):
            if not oly or not isinstance(oly, dict):
                return False
            if "showResultsToStudents" in oly:
                return bool(oly.get("showResultsToStudents"))
            if "show_results_to_students" in oly:
                return bool(oly.get("show_results_to_students"))
            # try enrich from PG
            try:
                oid = oly.get("id")
                if oid:
                    from sqlalchemy import text
                    try:
                        from db.connection import get_session
                    except Exception:
                        from connection import get_session  # type: ignore
                    with get_session() as s:
                        row = s.execute(
                            text("SELECT show_results_to_students FROM olympiads WHERE id::text = :id"),
                            {"id": str(oid)},
                        ).mappings().first()
                    if row is not None and row.get("show_results_to_students") is not None:
                        return bool(row.get("show_results_to_students"))
            except Exception as e:
                log.warning("show flag lookup: %s", e)
            return False

        def submit_exam(*args, **kwargs):
            out = _submit(*args, **kwargs)
            if not isinstance(out, dict):
                return out
            try:
                oly_id = out.get("olympiadId") or (out.get("result") or {}).get("olympiadId")
                oly = eng.find_olympiad(oly_id) if oly_id else None
                show = _show_results_flag(oly)
                if not show:
                    msg = (
                        "Шумо бо муваффақият супоридед. "
                        "Лутфан интизор шавед, то баллҳоятон муайян шаванд."
                    )
                    hidden = {
                        "ok": True,
                        "pendingReview": True,
                        "hideScore": True,
                        "message": msg,
                        "status": "submitted",
                        "attemptId": out.get("attemptId") or (out.get("result") or {}).get("attemptId"),
                        "olympiadId": oly_id,
                        "result": {
                            "pendingReview": True,
                            "hideScore": True,
                            "message": msg,
                            "status": "submitted",
                            "attemptId": out.get("attemptId"),
                            "olympiadId": oly_id,
                        },
                    }
                    return hidden
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
            return {"ok": True, "students": len(students), "olympiads": len(olympiads), "activeOlympiads": active}
        except Exception as e:
            return {"ok": False, "students": 0, "error": str(e)}

    @app.post("/api/admin/monitor/clear-recent")
    def clear_recent_alias():
        from flask import jsonify
        fn = app.view_functions.get("_clear_recent_results")
        if fn:
            return fn()
        return jsonify({"ok": True})

    print("[boot] patch_ui_batch OK")
