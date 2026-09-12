"""Persist full multi-type olympiad questions in PostgreSQL (questions_json).

Always enrich from questions_json on read (list/find/_oly_from_pg).
On create: original insert + UPDATE questions_json with commit verify.
"""
from __future__ import annotations

import json
import logging
from typing import Any

log = logging.getLogger("geografia.patch_olympiad_questions_pg")


def install(app=None):
    try:
        import db.repo as repo
    except Exception:
        try:
            import repo  # type: ignore
        except Exception as e:
            log.warning("repo import failed: %s", e)
            return

    try:
        if repo.use_pg():
            from sqlalchemy import text
            try:
                from db.connection import get_session
            except Exception:
                from connection import get_session  # type: ignore
            try:
                with get_session() as s:
                    s.execute(text("SELECT 1"))
                    for ddl in (
                        "ALTER TABLE olympiads ADD COLUMN IF NOT EXISTS questions_json JSONB",
                        "ALTER TABLE olympiads ADD COLUMN IF NOT EXISTS show_results_to_students BOOLEAN DEFAULT true",
                    ):
                        try:
                            s.execute(text(ddl))
                        except Exception as e:
                            log.warning("ddl: %s", e)
            except Exception as e:
                log.warning("schema ensure skipped: %s", e)
    except Exception as e:
        log.warning("schema ensure: %s", e)

    def _load_qjson(olympiad_id: str):
        if not repo.use_pg() or not olympiad_id:
            return None
        from sqlalchemy import text
        try:
            from db.connection import get_session
        except Exception:
            from connection import get_session  # type: ignore
        try:
            with get_session() as s:
                row = s.execute(
                    text(
                        "SELECT questions_json, show_results_to_students, is_active "
                        "FROM olympiads WHERE id::text = :id"
                    ),
                    {"id": str(olympiad_id)},
                ).mappings().first()
            if not row:
                return None
            raw = row.get("questions_json")
            qs = None
            if isinstance(raw, list):
                qs = raw
            elif isinstance(raw, dict):
                qs = raw.get("questions") if isinstance(raw.get("questions"), list) else None
            elif isinstance(raw, str) and raw.strip():
                try:
                    parsed = json.loads(raw)
                    if isinstance(parsed, list):
                        qs = parsed
                    elif isinstance(parsed, dict) and isinstance(parsed.get("questions"), list):
                        qs = parsed["questions"]
                except Exception:
                    qs = None
            return {
                "questions": qs,
                "showResultsToStudents": row.get("show_results_to_students"),
                "isActive": row.get("is_active"),
            }
        except Exception as e:
            log.warning("load_qjson: %s", e)
            return None

    def _apply_qjson(o: dict, olympiad_id: str) -> dict:
        if not isinstance(o, dict):
            return o
        meta = _load_qjson(olympiad_id)
        if not meta:
            return o
        qs = meta.get("questions")
        if isinstance(qs, list) and qs:
            fixed = []
            for i, q in enumerate(qs):
                if not isinstance(q, dict):
                    continue
                item = dict(q)
                if item.get("id") is None:
                    item["id"] = i + 1
                t = str(item.get("type") or item.get("qtype") or "").lower().strip()
                if t in ("choice", "mcq", "single_choice"):
                    t = "single"
                if t in ("match",):
                    t = "matching"
                if t:
                    item["type"] = t
                if item.get("correctText") and not item.get("correctAnswer"):
                    item["correctAnswer"] = item["correctText"]
                if item.get("correctAnswer") and not item.get("correctText"):
                    item["correctText"] = str(item["correctAnswer"])
                pairs = item.get("pairs") or item.get("correctPairs")
                if isinstance(pairs, dict):
                    item["pairs"] = pairs
                    item["correctPairs"] = pairs
                fixed.append(item)
            if fixed:
                o["questions"] = fixed
                o["questionCount"] = len(fixed)
        if meta.get("showResultsToStudents") is not None:
            o["showResultsToStudents"] = bool(meta["showResultsToStudents"])
        if meta.get("isActive") is not None:
            o["isActive"] = bool(meta["isActive"])
        return o

    _oly_from_pg = getattr(repo, "_oly_from_pg", None)
    _create = getattr(repo, "create_olympiad", None)
    _find = getattr(repo, "find_olympiad", None)
    _list = getattr(repo, "list_olympiads", None)

    if _oly_from_pg is not None:
        def oly_from_pg(session, o_row):
            base = _oly_from_pg(session, o_row)
            if not isinstance(base, dict):
                return base
            oid = str(base.get("id") or "")
            return _apply_qjson(base, oid)

        repo._oly_from_pg = oly_from_pg

    if _find is not None:
        def find_olympiad(olympiad_id: str):
            o = _find(olympiad_id)
            if not o or not isinstance(o, dict):
                return o
            return _apply_qjson(o, str(olympiad_id))

        repo.find_olympiad = find_olympiad

    if _list is not None:
        def list_olympiads():
            items = _list() or []
            out = []
            for o in items:
                if isinstance(o, dict) and o.get("id"):
                    out.append(_apply_qjson(dict(o), str(o["id"])))
                else:
                    out.append(o)
            return out

        repo.list_olympiads = list_olympiads

    if _create is not None:
        def create_olympiad(data: dict) -> dict:
            data = dict(data or {})
            questions = json.loads(json.dumps(data.get("questions") or [], ensure_ascii=False))
            data["questions"] = json.loads(json.dumps(questions, ensure_ascii=False))
            if "isActive" not in data:
                data["isActive"] = True
            show_results = data.get("showResultsToStudents")
            if show_results is None:
                show_results = True
                data["showResultsToStudents"] = True

            row = _create(data)
            if not row or not isinstance(row, dict) or not row.get("id"):
                raise RuntimeError("Олимпиада дар база захира нашуд")

            oid = str(row["id"])
            try:
                if repo.use_pg():
                    from sqlalchemy import text
                    try:
                        from db.connection import get_session
                    except Exception:
                        from connection import get_session  # type: ignore
                    qjson = json.dumps(questions, ensure_ascii=False)
                    with get_session() as s:
                        res = s.execute(
                            text(
                                "UPDATE olympiads SET "
                                "questions_json = CAST(:qjson AS jsonb), "
                                "show_results_to_students = :show, "
                                "is_active = :act "
                                "WHERE id::text = :id"
                            ),
                            {
                                "id": oid,
                                "qjson": qjson,
                                "show": bool(show_results),
                                "act": bool(data.get("isActive", True)),
                            },
                        )
                        rc = int(res.rowcount or 0)
                        log.info("questions_json UPDATE oid=%s rows=%s nQ=%s", oid, rc, len(questions))
                        if rc <= 0:
                            s.execute(
                                text(
                                    "UPDATE olympiads SET questions_json = CAST(:qjson AS jsonb) "
                                    "WHERE id = CAST(:id AS uuid)"
                                ),
                                {"id": oid, "qjson": qjson},
                            )
            except Exception as e:
                log.error("questions_json save failed: %s", e)

            found = repo.find_olympiad(oid) if getattr(repo, "find_olympiad", None) else None
            if found and isinstance(found, dict):
                if not (found.get("questions") and any(
                    (q or {}).get("type") not in (None, "single") or (q or {}).get("correctText")
                    for q in (found.get("questions") or [])
                )):
                    found["questions"] = questions
                    found["questionCount"] = len(questions)
                found["showResultsToStudents"] = bool(show_results)
                found["isActive"] = bool(data.get("isActive", found.get("isActive", True)))
                return found

            row["questions"] = questions
            row["questionCount"] = len(questions)
            row["showResultsToStudents"] = bool(show_results)
            row["isActive"] = bool(data.get("isActive", True))
            return row

        repo.create_olympiad = create_olympiad
        log.info("patched repo.create_olympiad + questions_json")

    try:
        import db.olympiad_engine as eng
        if getattr(repo, "find_olympiad", None):
            eng.find_olympiad = repo.find_olympiad
    except Exception as e:
        log.warning("engine find wire: %s", e)

    print("[boot] patch_olympiad_questions_pg: questions_json enrich on list/find/create")
    log.info("patch_olympiad_questions_pg installed")
