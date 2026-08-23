"""Boot patch: resolve Student ID \u2192 fullName on results; store real name on start."""
from __future__ import annotations

import logging

log = logging.getLogger("geografia.patch_names")


def _looks_like_code(name: str) -> bool:
    n = (name or "").strip()
    return n.isdigit() and len(n) >= 10


def _resolve_student(code: str):
    code = (code or "").strip()
    if not code:
        return None
    try:
        from db.repo import find_student_by_code
        return find_student_by_code(code)
    except Exception:
        return None


def install(app=None) -> None:
    try:
        from db import repo
        from sqlalchemy import text
        from db.connection import get_session

        def list_results(olympiad_id: str | None = None):
            if not repo.use_pg():
                items = repo._load_json(repo.RESULTS_FILE)
                if olympiad_id:
                    items = [r for r in items if str(r.get("olympiadId")) == str(olympiad_id)]
                for r in items:
                    nm = (r.get("studentName") or "").strip()
                    if _looks_like_code(nm) or not nm or nm == "\u0418\u0448\u0442\u0438\u0440\u043e\u043a\u0447\u04e3":
                        st = _resolve_student(nm if _looks_like_code(nm) else "")
                        if not st:
                            st = _resolve_student(str(r.get("studentId") or r.get("student_id") or ""))
                        if st and st.get("fullName"):
                            r["studentName"] = st["fullName"]
                            r["className"] = r.get("className") or st.get("className")
                            r["school"] = r.get("school") or st.get("school")
                        elif not nm:
                            r["studentName"] = "\u0418\u0448\u0442\u0438\u0440\u043e\u043a\u0447\u04e3"
                return items
            try:
                with get_session() as s:
                    base_sql = (
                        "SELECT a.id::text, a.olympiad_id::text, "
                        "COALESCE("
                        "  NULLIF(TRIM(st.full_name), ''), "
                        "  NULLIF(TRIM(a.student_name), ''), "
                        "  '\u0418\u0448\u0442\u0438\u0440\u043e\u043a\u0447\u04e3'"
                        ") AS student_name, "
                        "COALESCE(NULLIF(TRIM(st.class_name), ''), a.student_class) AS student_class, "
                        "COALESCE(NULLIF(TRIM(st.school_name), ''), a.student_school) AS student_school, "
                        "a.score, a.status, a.finished_at, "
                        "a.student_id::text AS student_uuid, "
                        "st.student_code AS student_code "
                        "FROM attempts a "
                        "LEFT JOIN students st ON ("
                        "  st.id = a.student_id "
                        "  OR (a.student_name IS NOT NULL AND st.student_code = TRIM(a.student_name))"
                        ") "
                    )
                    if olympiad_id:
                        rows = s.execute(text(
                            base_sql
                            + "WHERE a.olympiad_id::text = :oid "
                            "AND a.status IN ('passed','failed','submitted','timeout') "
                            "ORDER BY a.finished_at DESC NULLS LAST"
                        ), {"oid": str(olympiad_id)}).mappings().all()
                    else:
                        rows = s.execute(text(
                            base_sql
                            + "WHERE a.status IN ('passed','failed','submitted','timeout') "
                            "ORDER BY a.finished_at DESC NULLS LAST LIMIT 2000"
                        )).mappings().all()
                    out = []
                    for r in rows:
                        nm = (r.get("student_name") or "").strip() or "\u0418\u0448\u0442\u0438\u0440\u043e\u043a\u0447\u04e3"
                        if _looks_like_code(nm):
                            st = _resolve_student(nm)
                            if st and st.get("fullName"):
                                nm = st["fullName"]
                            else:
                                nm = "\u0418\u0448\u0442\u0438\u0440\u043e\u043a\u0447\u04e3"
                        out.append({
                            "id": r["id"],
                            "olympiadId": r.get("olympiad_id"),
                            "studentName": nm,
                            "fullName": nm,
                            "className": r.get("student_class"),
                            "school": r.get("student_school"),
                            "score": r.get("score"),
                            "status": r.get("status"),
                            "finishedAt": r["finished_at"].isoformat() if r.get("finished_at") else None,
                        })
                    return out
            except Exception as e:
                log.warning("list_results patch: %s", e)
                return []

        repo.list_results = list_results
        log.info("list_results name-resolve installed")
        print("[boot] patch_names: results show fullName not ID")
    except Exception as e:
        log.warning("patch_names list_results: %s", e)

    try:
        from db import olympiad_engine as oe

        _orig = oe.start_exam

        def start_exam(olympiad_id, student_code, fingerprint=None, **kwargs):
            result = _orig(olympiad_id, student_code, fingerprint=fingerprint, **kwargs)
            try:
                code = oe._norm_code(student_code) if hasattr(oe, "_norm_code") else str(student_code or "").strip()
                st = _resolve_student(code)
                name = (st or {}).get("fullName") or (st or {}).get("full_name")
                class_name = (st or {}).get("className") or (st or {}).get("class_name")
                school = (st or {}).get("school") or (st or {}).get("school_name")
                if name and not _looks_like_code(str(name)):
                    from db.connection import get_session, is_postgres_enabled
                    from sqlalchemy import text
                    aid = None
                    if isinstance(result, dict):
                        aid = result.get("attemptId") or result.get("sessionId") or result.get("id")
                    if aid and is_postgres_enabled():
                        with get_session() as s:
                            s.execute(
                                text(
                                    "UPDATE attempts SET "
                                    "student_name = :n, "
                                    "student_class = COALESCE(:c, student_class), "
                                    "student_school = COALESCE(:sch, student_school) "
                                    "WHERE id::text = :id"
                                ),
                                {"n": name, "c": class_name, "sch": school, "id": str(aid)},
                            )
                            try:
                                s.commit()
                            except Exception:
                                pass
                        log.info("stored fullName=%s on attempt %s", name, aid)
            except Exception as e:
                log.warning("patch_names start name: %s", e)
            return result

        oe.start_exam = start_exam
        log.info("start_exam name fix installed")
        print("[boot] patch_names: start_exam stores fullName")
    except Exception as e:
        log.warning("patch_names start_exam: %s", e)

    if app is not None:
        try:
            from flask import jsonify

            for rule in list(app.url_map.iter_rules()):
                if "monitor" in (rule.rule or "") and "GET" in (rule.methods or set()):
                    ep = rule.endpoint
                    orig = app.view_functions.get(ep)
                    if not orig:
                        continue

                    def make_mon(orig_fn):
                        def wrapped(*a, **k):
                            resp = orig_fn(*a, **k)
                            try:
                                body, status = resp, 200
                                if isinstance(resp, tuple):
                                    body, status = resp[0], resp[1]
                                if status and int(status) >= 400:
                                    return resp
                                data = body.get_json(silent=True) if hasattr(body, "get_json") else None
                                if not isinstance(data, dict):
                                    return resp
                                changed = False
                                for key in ("recentResults", "results", "sessions", "liveSessions"):
                                    items = data.get(key)
                                    if not isinstance(items, list):
                                        continue
                                    for r in items:
                                        if not isinstance(r, dict):
                                            continue
                                        nm = (r.get("studentName") or r.get("fullName") or "").strip()
                                        if not nm or nm == "\u0418\u0448\u0442\u0438\u0440\u043e\u043a\u0447\u04e3" or _looks_like_code(nm):
                                            sid = str(r.get("studentId") or r.get("student_id") or nm or "")
                                            st = _resolve_student(sid)
                                            if st and st.get("fullName"):
                                                r["studentName"] = st["fullName"]
                                                r["fullName"] = st["fullName"]
                                                if not r.get("className"):
                                                    r["className"] = st.get("className")
                                                if not r.get("school"):
                                                    r["school"] = st.get("school")
                                                changed = True
                                if changed:
                                    return jsonify(data)
                            except Exception as e:
                                log.warning("monitor name enrich: %s", e)
                            return resp

                        wrapped.__name__ = getattr(orig_fn, "__name__", "wrapped_monitor_names")
                        return wrapped

                    app.view_functions[ep] = make_mon(orig)
                    print(f"[boot] patch_names: monitor enrich on {ep}")
                    break
        except Exception as e:
            log.warning("patch_names monitor: %s", e)
