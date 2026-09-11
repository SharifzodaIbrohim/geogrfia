"""Enrich admin results/monitor: names + Student ID + score from review."""
from __future__ import annotations

import logging

log = logging.getLogger("geografia.results_score_fix")


def _eng():
    try:
        from db.connection import get_engine
        e = get_engine()
        if e is not None:
            return e
    except Exception:
        pass
    try:
        from db import connection as c
        return getattr(c, "engine", None)
    except Exception:
        return None


def _build_review(aid):
    try:
        from db import patch_attempt_review as par
        if hasattr(par, "build_review"):
            return par.build_review(aid)
    except Exception as e:
        log.debug("build_review: %s", e)
    return None


def _fill_from_review(r, rev):
    if not isinstance(rev, dict):
        return r
    name = (
        rev.get("fullName")
        or rev.get("studentName")
        or rev.get("name")
        or (rev.get("student") or {}).get("name")
        or (rev.get("student") or {}).get("fullName")
    )
    if name:
        r["fullName"] = name
        r["name"] = name
        r["studentName"] = name
    school = rev.get("school") or (rev.get("student") or {}).get("school")
    if school:
        r["school"] = school
        r["studentSchool"] = school
    klass = rev.get("className") or (rev.get("student") or {}).get("className")
    if klass:
        r["className"] = klass
        r["studentClass"] = klass
    code = (
        rev.get("studentCode")
        or rev.get("studentId")
        or (rev.get("student") or {}).get("code")
        or ""
    )
    code = str(code).strip()
    if code and code not in ("—", "-", "None", "null"):
        r["studentCode"] = code
        r["studentId"] = code
    if rev.get("score") is not None:
        r["score"] = rev.get("score")
    if rev.get("correct") is not None:
        r["correct"] = rev.get("correct")
    if rev.get("total"):
        r["total"] = rev.get("total")
    return r


def _lookup_student(eng, r):
    if eng is None:
        return r
    try:
        from sqlalchemy import text
        aid = str(r.get("attemptId") or r.get("id") or "").strip()
        if not aid:
            return r
        with eng.connect() as conn:
            row = None
            try:
                row = conn.execute(
                    text(
                        """SELECT
                             COALESCE(NULLIF(TRIM(st.full_name), ''), NULLIF(TRIM(a.student_name), ''), '') AS full_name,
                             COALESCE(NULLIF(TRIM(st.school_name), ''), COALESCE(a.student_school, '')) AS school,
                             COALESCE(NULLIF(TRIM(st.class_name), ''), COALESCE(a.student_class, '')) AS class_name,
                             COALESCE(NULLIF(TRIM(st.student_code), ''), st.id::text, '') AS code
                           FROM attempts a
                           LEFT JOIN students st ON (
                             (a.student_id IS NOT NULL AND st.id = a.student_id)
                             OR (a.student_name IS NOT NULL AND TRIM(a.student_name) ~ '^[0-9]{8,}$'
                                 AND (st.student_code = TRIM(a.student_name) OR st.id::text = TRIM(a.student_name)))
                           )
                           WHERE a.id::text = :id LIMIT 1"""
                    ),
                    {"id": aid},
                ).mappings().first()
            except Exception as e:
                log.debug("attempt join: %s", e)
                try:
                    conn.rollback()
                except Exception:
                    pass
            if row:
                if row.get("full_name"):
                    r["fullName"] = row["full_name"]
                    r["name"] = row["full_name"]
                    r["studentName"] = row["full_name"]
                if row.get("school"):
                    r["school"] = row["school"]
                    r["studentSchool"] = row["school"]
                if row.get("class_name"):
                    r["className"] = row["class_name"]
                    r["studentClass"] = row["class_name"]
                if row.get("code"):
                    r["studentCode"] = str(row["code"])
                    r["studentId"] = str(row["code"])
    except Exception as e:
        log.debug("lookup_student: %s", e)
    return r


def _enrich_row(row, eng, review_cache):
    if not isinstance(row, dict):
        return row
    r = dict(row)
    aid = str(r.get("attemptId") or r.get("id") or "").strip()

    if aid:
        if aid not in review_cache:
            try:
                review_cache[aid] = _build_review(aid)
            except Exception as e:
                log.debug("review %s: %s", aid, e)
                review_cache[aid] = None
        rev = review_cache.get(aid)
        if isinstance(rev, dict):
            r = _fill_from_review(r, rev)

    r = _lookup_student(eng, r)

    if not r.get("fullName") and not r.get("name"):
        r["fullName"] = r.get("studentName") or "—"
        r["name"] = r["fullName"]
    if not r.get("studentCode"):
        r["studentCode"] = r.get("studentId") or "—"
        r["studentId"] = r["studentCode"]
    if not r.get("school"):
        r["school"] = r.get("studentSchool") or "—"
    if not r.get("className"):
        r["className"] = r.get("studentClass") or "—"

    try:
        score = int(r.get("score") or 0)
    except Exception:
        score = 0
    ps = r.get("passScore") or r.get("pass_score") or 70
    try:
        ps = int(ps)
    except Exception:
        ps = 70
    st = str(r.get("status") or "").lower()
    if score >= ps:
        r["status"] = "passed"
        r["passed"] = True
    elif st not in ("timeout", "in_progress", "started"):
        r["status"] = "failed"
        r["passed"] = False
    return r


def _enrich_payload(data, eng):
    cache = {}
    if isinstance(data, list):
        return [_enrich_row(x, eng, cache) for x in data]
    if not isinstance(data, dict):
        return data
    out = dict(data)
    for key in ("results", "recent", "recentResults", "items", "attempts"):
        if isinstance(out.get(key), list):
            out[key] = [_enrich_row(x, eng, cache) for x in out[key]]
    rows = out.get("recent") or out.get("recentResults") or out.get("results") or []
    if isinstance(rows, list) and rows:
        passed = sum(
            1
            for x in rows
            if str(x.get("status") or "").lower() in ("passed", "pass")
            or x.get("passed") is True
        )
        failed = sum(
            1
            for x in rows
            if str(x.get("status") or "").lower() in ("failed", "fail", "timeout")
            or x.get("passed") is False
        )
        stats = dict(out.get("stats") or {})
        stats["passed"] = passed
        stats["failed"] = failed
        if not stats.get("results"):
            stats["results"] = len(rows)
        out["stats"] = stats
    return out


def install(app=None):
    if app is None:
        return
    eng = _eng()
    from flask import jsonify

    wrapped_eps = set()

    def _wrap(ep):
        if ep in wrapped_eps or ep not in app.view_functions:
            return
        orig = app.view_functions[ep]
        wrapped_eps.add(ep)

        def wrapped(*args, **kwargs):
            resp = orig(*args, **kwargs)
            try:
                if hasattr(resp, "get_json"):
                    data = resp.get_json(silent=True)
                    if data is not None:
                        return jsonify(_enrich_payload(data, eng)), getattr(
                            resp, "status_code", 200
                        )
                if isinstance(resp, tuple) and resp:
                    body = resp[0]
                    code = resp[1] if len(resp) > 1 else 200
                    if hasattr(body, "get_json"):
                        data = body.get_json(silent=True)
                        if data is not None:
                            return jsonify(_enrich_payload(data, eng)), code
                if isinstance(resp, (dict, list)):
                    return jsonify(_enrich_payload(resp, eng))
            except Exception as e:
                log.warning("results_score_fix wrap: %s", e)
            return resp

        app.view_functions[ep] = wrapped
        print("[boot] results_score_fix wrapped", ep)

    for rule in list(app.url_map.iter_rules()):
        path = str(rule.rule)
        ep = rule.endpoint
        if "export" in path:
            continue
        if (
            path.endswith("/results")
            or "/results" in path
            or path.endswith("/monitor")
            or path == "/api/admin/monitor"
            or path.endswith("/live")
        ):
            _wrap(ep)

    print("[boot] patch_results_score_fix OK n=%s" % len(wrapped_eps))
