"""Durable admin monitor: JOIN students for fullName; expire stale in_progress."""
from __future__ import annotations

import logging

log = logging.getLogger("geografia.patch_monitor")


def _looks_like_code(name: str) -> bool:
    n = (name or "").strip()
    return n.isdigit() and len(n) >= 8


def _resolve(code: str):
    code = (code or "").strip()
    if not code:
        return None
    try:
        from db.repo import find_student_by_code
        return find_student_by_code(code)
    except Exception:
        return None


def _engine():
    try:
        from db.connection import get_engine
        return get_engine()
    except Exception as e:
        log.warning("monitor get_engine: %s", e)
        return None


def _expire_stale(hours: float = 24.0) -> int:
    engine = _engine()
    if engine is None:
        return 0
    from sqlalchemy import text
    n = 0
    try:
        with engine.begin() as conn:
            try:
                r = conn.execute(text(
                    "UPDATE attempts SET status = 'timeout', finished_at = COALESCE(finished_at, NOW()) "
                    "WHERE status IN ('in_progress','started','active') "
                    "AND expires_at IS NOT NULL AND expires_at < NOW()"
                ))
                n += int(r.rowcount or 0)
            except Exception as e:
                log.debug("expire expires_at: %s", e)
            try:
                r = conn.execute(text(
                    "UPDATE attempts SET status = 'timeout', finished_at = COALESCE(finished_at, NOW()) "
                    "WHERE CAST(status AS text) IN ('in_progress','started','active') "
                    "AND started_at IS NOT NULL AND started_at < NOW() - INTERVAL '24 hours'"
                ))
                n += int(r.rowcount or 0)
            except Exception as e:
                log.debug("expire by age: %s", e)
    except Exception as e:
        log.warning("expire_stale: %s", e)
    if n:
        log.info("expired %s stale in_progress attempts", n)
    return n


def _rows_from_pg(limit: int = 500):
    engine = _engine()
    if engine is None:
        return []
    from sqlalchemy import text
    sqls = [
        """
        SELECT a.id::text AS id,
               a.olympiad_id::text AS olympiad_id,
               COALESCE(NULLIF(TRIM(st.full_name), ''), NULLIF(TRIM(a.student_name), ''), '') AS student_name,
               COALESCE(NULLIF(TRIM(st.class_name), ''), NULLIF(TRIM(a.student_class), ''), '') AS student_class,
               COALESCE(NULLIF(TRIM(st.school_name), ''), NULLIF(TRIM(a.student_school), ''), '') AS student_school,
               a.score, a.correct, a.total, a.pass_score,
               CAST(a.status AS text) AS status,
               a.finished_at, a.started_at,
               COALESCE(NULLIF(TRIM(st.student_code), ''), '') AS student_code,
               o.title AS olympiad_title
        FROM attempts a
        LEFT JOIN olympiads o ON o.id = a.olympiad_id
        LEFT JOIN students st ON (
          (a.student_id IS NOT NULL AND st.id = a.student_id)
          OR (a.student_name IS NOT NULL AND TRIM(a.student_name) <> '' AND st.student_code = TRIM(a.student_name))
        )
        ORDER BY COALESCE(a.finished_at, a.started_at) DESC NULLS LAST
        LIMIT :lim
        """,
        """
        SELECT a.id::text AS id, a.olympiad_id::text AS olympiad_id,
               COALESCE(a.student_name, '') AS student_name,
               COALESCE(a.student_class, '') AS student_class,
               COALESCE(a.student_school, '') AS student_school,
               a.score, a.correct, a.total, a.pass_score,
               CAST(a.status AS text) AS status,
               a.finished_at, a.started_at, '' AS student_code, '' AS olympiad_title
        FROM attempts a
        ORDER BY COALESCE(a.finished_at, a.started_at) DESC NULLS LAST
        LIMIT :lim
        """,
    ]
    for i, sql in enumerate(sqls):
        try:
            with engine.connect() as conn:
                rows = [dict(r) for r in conn.execute(text(sql), {"lim": limit}).mappings().all()]
                log.info("monitor sql#%s rows=%s", i, len(rows))
                return rows
        except Exception as e:
            log.warning("monitor sql#%s fail: %s", i, e)
    return []


def _fmt(rows):
    out = []
    for r in rows:
        nm = (r.get("student_name") or "").strip()
        code = (r.get("student_code") or "").strip()
        if _looks_like_code(nm):
            code = code or nm
            nm = ""
        if (not nm or nm == "Иштирокчӣ") and code:
            st = _resolve(code)
            if st:
                nm = st.get("fullName") or st.get("full_name") or nm
                if not r.get("student_class"):
                    r["student_class"] = st.get("className") or st.get("class_name")
                if not r.get("student_school"):
                    r["student_school"] = st.get("school") or st.get("school_name")
                code = st.get("id") or st.get("student_code") or code
        if not nm or nm == "Иштирокчӣ":
            nm = code or "—"
        status = str(r.get("status") or "").lower()
        fa, sa = r.get("finished_at"), r.get("started_at")
        out.append({
            "id": r.get("id"),
            "attemptId": r.get("id"),
            "olympiadId": r.get("olympiad_id"),
            "olympiadTitle": r.get("olympiad_title") or "",
            "title": r.get("olympiad_title") or "",
            "studentId": code or "",
            "studentCode": code or "",
            "studentName": nm,
            "fullName": nm,
            "name": nm,
            "className": r.get("student_class") or "",
            "studentClass": r.get("student_class") or "",
            "school": r.get("student_school") or "",
            "studentSchool": r.get("student_school") or "",
            "score": r.get("score"),
            "correct": r.get("correct"),
            "total": r.get("total"),
            "passScore": r.get("pass_score"),
            "status": status or r.get("status"),
            "finishedAt": fa.isoformat() if hasattr(fa, "isoformat") else fa,
            "startedAt": sa.isoformat() if hasattr(sa, "isoformat") else sa,
        })
    return out


def _count_table(table: str) -> int:
    engine = _engine()
    if engine is None:
        return 0
    from sqlalchemy import text
    try:
        with engine.connect() as conn:
            return int(conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar() or 0)
    except Exception:
        return 0


def install(app=None):
    if app is None:
        return
    from flask import jsonify

    def admin_monitor():
        try:
            _expire_stale(24)
        except Exception as e:
            log.debug("expire on monitor: %s", e)
        rows = _rows_from_pg(500) or []
        results = _fmt(rows)
        live_status = ("in_progress", "started", "active")
        live = [r for r in results if str(r.get("status") or "").lower() in live_status]
        recent = [r for r in results if str(r.get("status") or "").lower() not in live_status]
        if not recent and results:
            recent = results
        students_n = _count_table("students")
        olymp_n = _count_table("olympiads")
        return jsonify({
            "ok": True,
            "stats": {
                "students": students_n,
                "studentCount": students_n,
                "olympiads": olymp_n,
                "activeOlympiads": olymp_n,
                "liveSessions": len(live),
                "inProgress": len(live),
                "results": len(recent),
                "resultsToday": len(recent),
            },
            "liveSessions": live[:50],
            "sessions": live[:50],
            "recent": recent[:50],
            "recentResults": recent[:50],
            "results": recent[:50],
        })

    bound = 0
    for rule in list(app.url_map.iter_rules()):
        path = str(rule.rule).rstrip("/")
        if path in ("/api/admin/monitor", "/api/monitor", "/api/admin/live"):
            app.view_functions[rule.endpoint] = admin_monitor
            bound += 1
            print(f"[boot] monitor_durable: rebound {rule.endpoint} -> {path}")
    if not bound:
        app.add_url_rule("/api/admin/monitor", "admin_monitor_durable", admin_monitor, methods=["GET"])
        print("[boot] monitor_durable: added /api/admin/monitor")
    print("[boot] patch_monitor_durable installed")
