"""Monitor/results always read finished attempts from PostgreSQL (durable)."""
from __future__ import annotations
import logging
log = logging.getLogger("geografia.patch_monitor_durable")

FINISHED = ("passed", "failed", "timeout", "submitted", "finished")

def _rows_from_pg(limit=500):
    try:
        from db.connection import engine, is_postgres_enabled
        if not is_postgres_enabled() or engine is None:
            return None
    except Exception:
        return None
    from sqlalchemy import text
    sqls = [
        """
        SELECT a.id::text AS id,
               a.olympiad_id::text AS olympiad_id,
               COALESCE(NULLIF(TRIM(a.student_name), ''), st.full_name, '') AS student_name,
               COALESCE(a.student_class, st.class_name, '') AS student_class,
               COALESCE(a.student_school, st.school_name, '') AS student_school,
               a.score, a.correct, a.total, a.pass_score,
               CAST(a.status AS text) AS status,
               a.finished_at, a.started_at,
               st.student_code AS student_code
        FROM attempts a
        LEFT JOIN students st ON st.id = a.student_id
        WHERE a.finished_at IS NOT NULL
           OR CAST(a.status AS text) IN ('passed','failed','timeout','submitted','finished')
        ORDER BY COALESCE(a.finished_at, a.started_at) DESC NULLS LAST
        LIMIT :lim
        """,
        """
        SELECT a.id::text AS id, a.olympiad_id::text AS olympiad_id,
               COALESCE(a.student_name,'') AS student_name,
               COALESCE(a.student_class,'') AS student_class,
               COALESCE(a.student_school,'') AS student_school,
               a.score, a.correct, a.total, a.pass_score,
               CAST(a.status AS text) AS status,
               a.finished_at, a.started_at,
               NULL AS student_code
        FROM attempts a
        WHERE a.finished_at IS NOT NULL
        ORDER BY a.finished_at DESC NULLS LAST
        LIMIT :lim
        """,
    ]
    with engine.connect() as conn:
        for sql in sqls:
            try:
                rows = conn.execute(text(sql), {"lim": limit}).mappings().all()
                return [dict(r) for r in rows]
            except Exception as e:
                log.warning("monitor sql fail: %s", e)
    return []

def _fmt(rows):
    out = []
    for r in rows or []:
        fa = r.get("finished_at")
        sa = r.get("started_at")
        out.append({
            "id": r.get("id"),
            "attemptId": r.get("id"),
            "olympiadId": r.get("olympiad_id"),
            "studentId": r.get("student_code") or "",
            "studentName": r.get("student_name") or "",
            "fullName": r.get("student_name") or "",
            "className": r.get("student_class") or "",
            "school": r.get("student_school") or "",
            "score": r.get("score"),
            "correct": r.get("correct"),
            "total": r.get("total"),
            "passScore": r.get("pass_score"),
            "status": r.get("status"),
            "finishedAt": fa.isoformat() if hasattr(fa, "isoformat") else fa,
            "startedAt": sa.isoformat() if hasattr(sa, "isoformat") else sa,
        })
    return out

def install(app=None):
    if app is None:
        return
    from flask import jsonify

    def admin_monitor():
        rows = _rows_from_pg(500) or []
        results = _fmt(rows)
        passed = sum(1 for r in results if r.get("status") == "passed")
        failed = sum(1 for r in results if r.get("status") in ("failed", "timeout"))
        live = []
        try:
            try:
                from db import olympiad_engine as oe
            except Exception:
                import olympiad_engine as oe
            sessions = oe._load_sessions() or {}
            for sid, sess in sessions.items():
                if sess.get("status") in (None, "in_progress", "started"):
                    live.append({
                        "attemptId": sid,
                        "studentId": sess.get("studentId") or sess.get("studentCode"),
                        "olympiadId": sess.get("olympiadId"),
                        "startedAt": sess.get("startedAt"),
                        "status": "in_progress",
                    })
        except Exception as e:
            log.debug("live sessions: %s", e)
        students_n = olympiads_n = active_n = 0
        try:
            from db import repo
            students_n = len(repo.list_students() or [])
            oly = repo.list_olympiads() or []
            olympiads_n = len(oly)
            try:
                from db.repo import is_olympiad_open
                active_n = sum(1 for o in oly if is_olympiad_open(o))
            except Exception:
                active_n = olympiads_n
        except Exception:
            pass
        return jsonify({
            "backend": "postgresql",
            "stats": {
                "students": students_n,
                "olympiads": olympiads_n,
                "activeOlympiads": active_n,
                "results": len(results),
                "resultsToday": len(results),
                "passed": passed,
                "failed": failed,
                "liveSessions": len(live),
                "inProgress": len(live),
            },
            "recentResults": results[:50],
            "results": results[:50],
            "liveSessions": live[:50],
            "sessions": live[:50],
        })

    for name in list(app.view_functions.keys()):
        if name in ("admin_monitor",) or name.lower() == "monitor":
            app.view_functions[name] = admin_monitor
    for r in list(app.url_map.iter_rules()):
        if r.rule == "/api/admin/monitor" and r.methods and "GET" in r.methods:
            app.view_functions[r.endpoint] = admin_monitor

    existing = {r.rule for r in app.url_map.iter_rules()}
    if "/api/admin/monitor" not in existing:
        app.add_url_rule("/api/admin/monitor", "admin_monitor_durable", admin_monitor, methods=["GET"])

    try:
        from db import repo
        def list_results(olympiad_id=None):
            rows = _rows_from_pg(2000) or []
            out = _fmt(rows)
            if olympiad_id:
                out = [r for r in out if str(r.get("olympiadId")) == str(olympiad_id)]
            return out
        repo.list_results = list_results
        log.info("list_results overridden to durable attempts query")
    except Exception as e:
        log.warning("list_results override: %s", e)

    print("[boot] patch_monitor_durable: attempts-based monitor + list_results")
    log.info("patch_monitor_durable installed")
