"""Enrich admin results/monitor rows using review score + student code."""
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
        log.debug("build_review import: %s", e)
    return None


def _student_code(eng, row):
    code = str(
        row.get("studentCode")
        or row.get("student_code")
        or row.get("studentId")
        or row.get("student_id")
        or ""
    ).strip()
    if code and code not in ("—", "-", "None", "null"):
        return code
    name = str(row.get("fullName") or row.get("studentName") or row.get("name") or "").strip()
    sn = str(row.get("studentName") or "").strip()
    if sn.isdigit() and len(sn) >= 10:
        return sn
    if eng is None or not name:
        return ""
    try:
        from sqlalchemy import text
        with eng.connect() as conn:
            r = conn.execute(
                text(
                    """SELECT COALESCE(NULLIF(TRIM(student_code), ''), id::text) AS code
                       FROM students
                       WHERE full_name = :n
                          OR TRIM(COALESCE(last_name,'') || ' ' || COALESCE(first_name,'')) = :n
                       LIMIT 1"""
                ),
                {"n": name},
            ).mappings().first()
            if r and r.get("code"):
                return str(r["code"])
    except Exception as e:
        log.debug("student code: %s", e)
        try:
            from sqlalchemy import text
            with eng.connect() as conn:
                r = conn.execute(
                    text(
                        "SELECT id::text AS code FROM students WHERE full_name = :n LIMIT 1"
                    ),
                    {"n": name},
                ).mappings().first()
                if r and r.get("code"):
                    return str(r["code"])
        except Exception as e2:
            log.debug("student code2: %s", e2)
    return ""


def _enrich_row(row, eng, review_cache):
    if not isinstance(row, dict):
        return row
    r = dict(row)
    aid = str(r.get("attemptId") or r.get("id") or "").strip()
    code = _student_code(eng, r)
    if code:
        r["studentCode"] = code
        r["studentId"] = code
    else:
        r["studentCode"] = r.get("studentCode") or "—"
        r["studentId"] = r.get("studentId") or r["studentCode"]

    try:
        score = int(r.get("score") or 0)
    except Exception:
        score = 0
    try:
        correct = int(r.get("correct") or 0)
    except Exception:
        correct = 0
    if aid and (score == 0 or correct == 0):
        if aid not in review_cache:
            try:
                review_cache[aid] = _build_review(aid)
            except Exception as e:
                log.debug("review %s: %s", aid, e)
                review_cache[aid] = None
        rev = review_cache.get(aid)
        if isinstance(rev, dict) and rev.get("items") is not None:
            r["score"] = rev.get("score", score)
            r["correct"] = rev.get("correct", correct)
            if rev.get("total"):
                r["total"] = rev.get("total")
            score = int(r.get("score") or 0)

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
