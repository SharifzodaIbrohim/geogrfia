"""Boot patch: resolve Student ID \u2192 fullName on results; store real name on start."""
from __future__ import annotations

import logging

log = logging.getLogger("geografia.patch_names")


def _looks_like_code(name: str) -> bool:
    n = (name or "").strip()
    return n.isdigit() and len(n) >= 8


def _resolve_student(code: str):
    code = (code or "").strip()
    if not code:
        return None
    try:
        from db.repo import find_student_by_code
        return find_student_by_code(code)
    except Exception:
        return None


def _fill_name(row: dict) -> dict:
    """Ensure studentName/fullName/school/class/studentCode are populated."""
    nm = (row.get("studentName") or row.get("fullName") or row.get("student_name") or "").strip()
    code = (
        row.get("studentCode")
        or row.get("student_code")
        or row.get("studentId")
        or row.get("student_id")
        or ""
    )
    code = str(code or "").strip()
    if _looks_like_code(nm):
        code = code or nm
        nm = ""
    placeholder = "\u0418\u0448\u0442\u0438\u0440\u043e\u043a\u0447\u04e3"
    need = (not nm) or nm == placeholder or _looks_like_code(nm)
    if need and code:
        st = _resolve_student(code)
        if st:
            nm = (st.get("fullName") or st.get("full_name") or nm or placeholder)
            row["className"] = row.get("className") or row.get("studentClass") or st.get("className") or st.get("class_name") or ""
            row["school"] = row.get("school") or row.get("studentSchool") or st.get("school") or st.get("school_name") or ""
            row["studentCode"] = st.get("id") or st.get("student_code") or code
            row["studentId"] = row["studentCode"]
    if not nm:
        nm = placeholder
    row["studentName"] = nm
    row["fullName"] = nm
    row["name"] = nm
    if not row.get("studentCode") and _looks_like_code(code):
        row["studentCode"] = code
        row["studentId"] = code
    return row


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
                return [_fill_name(dict(r)) for r in items]

            rows_out = []
            try:
                with get_session() as s:
                    base_sql = (
                        "SELECT a.id::text AS id, a.olympiad_id::text AS olympiad_id, "
                        "COALESCE("
                        "  NULLIF(TRIM(st.full_name), ''), "
                        "  NULLIF(TRIM(a.student_name), ''), "
                        "  ''"
                        ") AS student_name, "
                        "COALESCE(NULLIF(TRIM(st.class_name), ''), NULLIF(TRIM(a.student_class), ''), '') AS student_class, "
                        "COALESCE(NULLIF(TRIM(st.school_name), ''), NULLIF(TRIM(a.student_school), ''), '') AS student_school, "
                        "a.score, a.correct, a.total, a.pass_score, "
                        "CAST(a.status AS text) AS status, a.finished_at, a.started_at, "
                        "a.student_id::text AS student_uuid, "
                        "COALESCE(NULLIF(TRIM(st.student_code), ''), "
                        "  CASE WHEN a.student_name ~ '^[0-9]{8,}$' THEN TRIM(a.student_name) ELSE NULL END"
                        ") AS student_code "
                        "FROM attempts a "
                        "LEFT JOIN students st ON ("
                        "  (a.student_id IS NOT NULL AND st.id = a.student_id) "
                        "  OR (a.student_name IS NOT NULL AND TRIM(a.student_name) <> '' AND st.student_code = TRIM(a.student_name))"
                        ") "
                    )
                    if olympiad_id:
                        q = (
                            base_sql
                            + "WHERE a.olympiad_id::text = :oid "
                            "ORDER BY COALESCE(a.finished_at, a.started_at) DESC NULLS LAST"
                        )
                        raw = s.execute(text(q), {"oid": str(olympiad_id)}).mappings().all()
                    else:
                        q = (
                            base_sql
                            + "ORDER BY COALESCE(a.finished_at, a.started_at) DESC NULLS LAST "
                            "LIMIT 500"
                        )
                        raw = s.execute(text(q)).mappings().all()

                    for r in raw:
                        item = {
                            "id": r.get("id"),
                            "attemptId": r.get("id"),
                            "olympiadId": r.get("olympiad_id"),
                            "studentName": r.get("student_name") or "",
                            "fullName": r.get("student_name") or "",
                            "className": r.get("student_class") or "",
                            "studentClass": r.get("student_class") or "",
                            "school": r.get("student_school") or "",
                            "studentSchool": r.get("student_school") or "",
                            "score": r.get("score"),
                            "correct": r.get("correct"),
                            "total": r.get("total"),
                            "passScore": r.get("pass_score"),
                            "status": r.get("status"),
                            "finishedAt": r["finished_at"].isoformat() if hasattr(r.get("finished_at"), "isoformat") else r.get("finished_at"),
                            "startedAt": r["started_at"].isoformat() if hasattr(r.get("started_at"), "isoformat") else r.get("started_at"),
                            "studentCode": r.get("student_code") or "",
                            "studentId": r.get("student_code") or r.get("student_uuid") or "",
                        }
                        rows_out.append(_fill_name(item))
            except Exception as e:
                log.warning("patch_names list_results PG: %s", e)
                try:
                    with get_session() as s:
                        raw = s.execute(text(
                            "SELECT id::text, olympiad_id::text, student_name, student_class, student_school, "
                            "score, correct, total, pass_score, CAST(status AS text) AS status, "
                            "finished_at, started_at, student_id::text "
                            "FROM attempts ORDER BY COALESCE(finished_at, started_at) DESC NULLS LAST LIMIT 500"
                        )).mappings().all()
                        for r in raw:
                            if olympiad_id and str(r.get("olympiad_id")) != str(olympiad_id):
                                continue
                            item = {
                                "id": r.get("id"),
                                "attemptId": r.get("id"),
                                "olympiadId": r.get("olympiad_id"),
                                "studentName": r.get("student_name") or "",
                                "className": r.get("student_class") or "",
                                "school": r.get("student_school") or "",
                                "score": r.get("score"),
                                "correct": r.get("correct"),
                                "total": r.get("total"),
                                "passScore": r.get("pass_score"),
                                "status": r.get("status"),
                                "finishedAt": r["finished_at"].isoformat() if hasattr(r.get("finished_at"), "isoformat") else r.get("finished_at"),
                                "studentId": r.get("student_id") or "",
                                "studentCode": "",
                            }
                            rows_out.append(_fill_name(item))
                except Exception as e2:
                    log.warning("patch_names fallback: %s", e2)

            return rows_out

        repo.list_results = list_results
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
                        if isinstance(result, dict):
                            result["studentName"] = name
                            result["fullName"] = name
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

            def _wrap_results_view(view):
                def wrapped(*a, **kw):
                    resp = view(*a, **kw)
                    try:
                        data = resp.get_json(silent=True) if hasattr(resp, "get_json") else None
                        if isinstance(data, dict):
                            items = data.get("results") or data.get("items") or data.get("rows")
                            if isinstance(items, list):
                                data["results"] = [_fill_name(dict(x)) for x in items]
                                if "items" in data:
                                    data["items"] = data["results"]
                                return jsonify(data)
                    except Exception as e:
                        log.warning("wrap results: %s", e)
                    return resp
                wrapped.__name__ = getattr(view, "__name__", "wrapped_results")
                return wrapped

            for ep, fn in list(app.view_functions.items()):
                rule_paths = [str(r.rule) for r in app.url_map.iter_rules() if r.endpoint == ep]
                if any("/results" in p for p in rule_paths):
                    app.view_functions[ep] = _wrap_results_view(fn)
                    print(f"[boot] patch_names: wrapped results endpoint {ep}")
        except Exception as e:
            log.warning("patch_names wrap routes: %s", e)

    print("[boot] patch_names installed")
