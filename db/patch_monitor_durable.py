"""Durable admin monitor: JOIN students + olympiad title; never empty names."""
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


def _rows_from_pg(limit: int = 500):
    try:
        from db.connection import get_engine
        from sqlalchemy import text
        engine = get_engine()
    except Exception as e:
        log.warning("monitor engine: %s", e)
        return []

    sqls = [
        """
        SELECT a.id::text AS id, a.olympiad_id::text AS olympiad_id,
               COALESCE(NULLIF(TRIM(st.full_name), ''), NULLIF(TRIM(a.student_name), ''), '') AS student_name,
               COALESCE(NULLIF(TRIM(st.class_name), ''), NULLIF(TRIM(a.student_class), ''), '') AS student_class,
               COALESCE(NULLIF(TRIM(st.school_name), ''), NULLIF(TRIM(a.student_school), ''), '') AS student_school,
               a.score, a.correct, a.total, a.pass_score,
               CAST(a.status AS text) AS status,
               a.finished_at, a.started_at,
               COALESCE(NULLIF(TRIM(st.student_code), ''),
                 CASE WHEN a.student_name ~ '^[0-9]{8,}$' THEN TRIM(a.student_name) ELSE NULL END
               ) AS student_code,
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
               COALESCE(a.student_name,'') AS student_name,
               COALESCE(a.student_class,'') AS student_class,
               COALESCE(a.student_school,'') AS student_school,
               a.score, a.correct, a.total, a.pass_score,
               CAST(a.status AS text) AS status,
               a.finished_at, a.started_at,
               NULL AS student_code,
               NULL AS olympiad_title
        FROM attempts a
        ORDER BY COALESCE(a.finished_at, a.started_at) DESC NULLS LAST
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
        nm = (r.get("student_name") or "").strip()
        code = (r.get("student_code") or "").strip()
        if _looks_like_code(nm):
            code = code or nm
            nm = ""
        if (not nm or nm == "\u0418\u0448\u0442\u0438\u0440\u043e\u043a\u0447\u04e3") and code:
            st = _resolve(code)
            if st:
                nm = st.get("fullName") or st.get("full_name") or nm
                if not r.get("student_class"):
                    r["student_class"] = st.get("className") or st.get("class_name")
                if not r.get("student_school"):
                    r["student_school"] = st.get("school") or st.get("school_name")
                code = st.get("id") or st.get("student_code") or code
        if not nm:
            nm = "\u0418\u0448\u0442\u0438\u0440\u043e\u043a\u0447\u04e3"
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
            "className": r.get("student_class") or "",
            "studentClass": r.get("student_class") or "",
            "school": r.get("student_school") or "",
            "studentSchool": r.get("student_school") or "",
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
        passed = sum(1 for r in results if str(r.get("status") or "").lower() in ("passed", "pass"))
        failed = sum(1 for r in results if str(r.get("status") or "").lower() in ("failed", "timeout", "fail"))
        live = []
        try:
            inprog = [r for r in results if str(r.get("status") or "").lower() in ("in_progress", "started", "active")]
            live = inprog[:50]
        except Exception:
            pass
        students_n = 0
        olymp_n = 0
        try:
            from db.repo import list_students, list_olympiads
            students_n = len(list_students() or [])
            olymp_n = len([o for o in (list_olympiads() or []) if str(o.get("status") or "").lower() in ("active", "published", "open")])
        except Exception:
            pass
        recent = [r for r in results if r.get("finishedAt") or str(r.get("status") or "").lower() not in ("in_progress", "started")]
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
                "passed": passed,
                "failed": failed,
            },
            "liveSessions": live,
            "sessions": live,
            "recent": recent[:30],
            "recentResults": recent[:30],
            "results": recent[:30],
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
