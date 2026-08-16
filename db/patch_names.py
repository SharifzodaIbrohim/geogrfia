"""Boot patch: resolve Student ID → fullName on results; store real name on start."""
from __future__ import annotations

import logging

log = logging.getLogger("geografia.patch_names")


def _looks_like_code(name: str) -> bool:
    n = (name or "").strip()
    return n.isdigit() and len(n) >= 10


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
                    if _looks_like_code(nm):
                        st = repo.find_student_by_code(nm)
                        if st and st.get("fullName"):
                            r["studentName"] = st["fullName"]
                        else:
                            r["studentName"] = "Иштирокчӣ"
                return items
            try:
                with get_session() as s:
                    if olympiad_id:
                        rows = s.execute(text(
                            "SELECT a.id::text, a.olympiad_id::text, "
                            "COALESCE(NULLIF(TRIM(st.full_name), ''), NULLIF(TRIM(a.student_name), ''), 'Иштирокчӣ') AS student_name, "
                            "COALESCE(NULLIF(TRIM(st.class_name), ''), a.student_class) AS student_class, "
                            "COALESCE(NULLIF(TRIM(st.school_name), ''), a.student_school) AS student_school, "
                            "a.score, a.status, a.finished_at "
                            "FROM attempts a "
                            "LEFT JOIN students st ON st.id = a.student_id "
                            "WHERE a.olympiad_id::text = :oid "
                            "AND a.status IN ('passed','failed','submitted','timeout') "
                            "ORDER BY a.finished_at DESC NULLS LAST"
                        ), {"oid": str(olympiad_id)}).mappings().all()
                    else:
                        rows = s.execute(text(
                            "SELECT a.id::text, a.olympiad_id::text, "
                            "COALESCE(NULLIF(TRIM(st.full_name), ''), NULLIF(TRIM(a.student_name), ''), 'Иштирокчӣ') AS student_name, "
                            "COALESCE(NULLIF(TRIM(st.class_name), ''), a.student_class) AS student_class, "
                            "COALESCE(NULLIF(TRIM(st.school_name), ''), a.student_school) AS student_school, "
                            "a.score, a.status, a.finished_at "
                            "FROM attempts a "
                            "LEFT JOIN students st ON st.id = a.student_id "
                            "WHERE a.status IN ('passed','failed','submitted','timeout') "
                            "ORDER BY a.finished_at DESC NULLS LAST LIMIT 2000"
                        )).mappings().all()
                    out = []
                    for r in rows:
                        nm = (r.get("student_name") or "").strip() or "Иштирокчӣ"
                        if _looks_like_code(nm):
                            nm = "Иштирокчӣ"
                        out.append({
                            "id": r["id"], "olympiadId": r.get("olympiad_id"),
                            "studentName": nm,
                            "className": r.get("student_class"),
                            "school": r.get("student_school"),
                            "score": r.get("score"), "status": r.get("status"),
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
                code = oe._norm_code(student_code)
                st = None
                try:
                    from db.repo import find_student_by_code
                    st = find_student_by_code(code)
                except Exception:
                    pass
                name = (st or {}).get("fullName") or (st or {}).get("full_name")
                if name and not _looks_like_code(str(name)):
                    from db.connection import get_session, is_postgres_enabled
                    from sqlalchemy import text
                    sid = result.get("sessionId") if isinstance(result, dict) else None
                    if sid and is_postgres_enabled():
                        with get_session() as s:
                            s.execute(
                                text("UPDATE attempts SET student_name = :n WHERE id::text = :id"),
                                {"n": name, "id": sid},
                            )
            except Exception as e:
                log.warning("patch_names start name: %s", e)
            return result

        oe.start_exam = start_exam
        log.info("start_exam name fix installed")
        print("[boot] patch_names: start_exam stores fullName")
    except Exception as e:
        log.warning("patch_names start_exam: %s", e)
