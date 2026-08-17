"""Persist full multi-type olympiad questions in PostgreSQL (questions_json).

Critical: never return a fake olympiad if DB insert failed.
Strategy: use original repo.create_olympiad (proven), then UPDATE questions_json.
"""
from __future__ import annotations

import json
import logging
import uuid
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

    # Schema ensure is optional — never block boot if PG is waking up
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
                log.warning("schema ensure skipped (DB not ready): %s", e)
    except Exception as e:
        log.warning("schema ensure: %s", e)

    _oly_from_pg = getattr(repo, "_oly_from_pg", None)
    _create = getattr(repo, "create_olympiad", None)
    _find = getattr(repo, "find_olympiad", None)

    def _row_get(row, key, default=None):
        try:
            if hasattr(row, "get"):
                return row.get(key, default)
            return row[key]
        except Exception:
            return default

    def _enrich_from_json(o: dict, olympiad_id: str) -> dict:
        if not o or not isinstance(o, dict):
            return o
        try:
            if not repo.use_pg():
                return o
            from sqlalchemy import text
            try:
                from db.connection import get_session
            except Exception:
                from connection import get_session  # type: ignore
            with get_session() as s:
                row = s.execute(
                    text(
                        "SELECT questions_json, show_results_to_students, is_active "
                        "FROM olympiads WHERE id::text = :id"
                    ),
                    {"id": str(olympiad_id)},
                ).mappings().first()
            if not row:
                return o
            raw = row.get("questions_json")
            if isinstance(raw, list) and raw:
                o["questions"] = raw
                o["questionCount"] = len(raw)
            elif isinstance(raw, str) and raw.strip():
                try:
                    parsed = json.loads(raw)
                    if isinstance(parsed, list) and parsed:
                        o["questions"] = parsed
                        o["questionCount"] = len(parsed)
                except Exception:
                    pass
            if row.get("show_results_to_students") is not None:
                o["showResultsToStudents"] = bool(row.get("show_results_to_students"))
            if row.get("is_active") is not None:
                o["isActive"] = bool(row.get("is_active"))
        except Exception as e:
            log.warning("enrich: %s", e)
        return o

    if _oly_from_pg is not None:
        def oly_from_pg(session, o_row):
            base = _oly_from_pg(session, o_row)
            if not isinstance(base, dict):
                return base
            raw = _row_get(o_row, "questions_json")
            qs = None
            if isinstance(raw, list):
                qs = raw
            elif isinstance(raw, str) and raw.strip():
                try:
                    qs = json.loads(raw)
                except Exception:
                    qs = None
            if isinstance(qs, list) and qs:
                fixed = []
                for i, q in enumerate(qs):
                    if not isinstance(q, dict):
                        continue
                    item = dict(q)
                    if item.get("id") is None:
                        item["id"] = i + 1
                    item["type"] = str(item.get("type") or "single").lower()
                    fixed.append(item)
                base["questions"] = fixed
                base["questionCount"] = len(fixed)
            show = _row_get(o_row, "show_results_to_students")
            if show is not None:
                base["showResultsToStudents"] = bool(show)
            return base

        repo._oly_from_pg = oly_from_pg

    if _create is not None:
        def create_olympiad(data: dict) -> dict:
            data = dict(data or {})
            questions = data.get("questions") or []
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
                    with get_session() as s:
                        try:
                            s.execute(
                                text(
                                    "UPDATE olympiads SET "
                                    "questions_json = CAST(:qjson AS jsonb), "
                                    "show_results_to_students = :show, "
                                    "is_active = :act, "
                                    "updated_at = NOW() "
                                    "WHERE id::text = :id"
                                ),
                                {
                                    "id": oid,
                                    "qjson": json.dumps(questions, ensure_ascii=False),
                                    "show": bool(show_results),
                                    "act": bool(data.get("isActive", True)),
                                },
                            )
                        except Exception as e:
                            log.warning("questions_json update skipped: %s", e)
                            try:
                                s.execute(
                                    text(
                                        "UPDATE olympiads SET is_active = :act, updated_at = NOW() "
                                        "WHERE id::text = :id"
                                    ),
                                    {"id": oid, "act": bool(data.get("isActive", True))},
                                )
                            except Exception as e2:
                                log.warning("is_active update: %s", e2)
            except Exception as e:
                log.warning("post-create enrich failed: %s", e)

            found = _find(oid) if _find else None
            if found and isinstance(found, dict):
                found = _enrich_from_json(found, oid)
                found["questions"] = questions or found.get("questions") or []
                found["questionCount"] = len(found["questions"])
                found["showResultsToStudents"] = bool(show_results)
                found["isActive"] = bool(data.get("isActive", found.get("isActive", True)))
                return found

            row["questions"] = questions
            row["questionCount"] = len(questions)
            row["showResultsToStudents"] = bool(show_results)
            row["isActive"] = bool(data.get("isActive", True))
            return row

        repo.create_olympiad = create_olympiad
        log.info("patched repo.create_olympiad (original + questions_json)")

    if _find is not None:
        def find_olympiad(olympiad_id: str):
            o = _find(olympiad_id)
            if not o or not isinstance(o, dict):
                return o
            return _enrich_from_json(o, str(olympiad_id))

        repo.find_olympiad = find_olympiad

    try:
        import db.olympiad_engine as eng
        if getattr(repo, "find_olympiad", None):
            eng.find_olympiad = repo.find_olympiad

        def _public_questions(qs_src: list) -> list:
            import secrets as _sec
            order = list(range(len(qs_src or [])))
            _sec.SystemRandom().shuffle(order)
            out = []
            for orig_i in order:
                q = (qs_src or [])[orig_i] or {}
                qid = q.get("id")
                if qid is None:
                    qid = str(orig_i)
                qtype = str(q.get("type") or "single").lower()
                item = {
                    "id": str(qid),
                    "type": qtype,
                    "text": q.get("text"),
                    "options": eng._sanitize_options(q.get("options")),
                    "originalIndex": orig_i,
                }
                if qtype == "matching":
                    item["leftItems"] = list(q.get("leftItems") or [])
                    item["rightItems"] = list(q.get("rightItems") or [])
                if qtype in ("short", "text"):
                    item["inputType"] = "text"
                for bad in eng._FORBIDDEN_Q_KEYS:
                    item.pop(bad, None)
                out.append(item)
            return out

        eng._public_questions = _public_questions
    except Exception as e:
        log.warning("engine rebind: %s", e)

    print("[boot] patch_olympiad_questions_pg: create via original + questions_json")


if __name__ == "__main__":
    install()
