"""Persist full multi-type olympiad questions in PostgreSQL (questions_json)."""
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

    if _oly_from_pg is not None:
        def oly_from_pg(session, o_row):
            base = _oly_from_pg(session, o_row)
            if not isinstance(base, dict):
                return base
            raw = _row_get(o_row, "questions_json")
            if raw is None and hasattr(o_row, "__getitem__"):
                try:
                    raw = o_row["questions_json"]
                except Exception:
                    raw = None
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
                    item["id"] = item["id"] if isinstance(item["id"], int) else str(item["id"])
                    item["type"] = str(item.get("type") or "single").lower()
                    fixed.append(item)
                base["questions"] = fixed
                base["questionCount"] = len(fixed)
            show = _row_get(o_row, "show_results_to_students")
            if show is not None:
                base["showResultsToStudents"] = bool(show)
            elif "showResultsToStudents" not in base:
                base["showResultsToStudents"] = True
            return base

        repo._oly_from_pg = oly_from_pg
        log.info("patched repo._oly_from_pg for questions_json")

    if _create is not None:
        def create_olympiad(data: dict) -> dict:
            questions = data.get("questions") or []
            show_results = data.get("showResultsToStudents")
            if show_results is None:
                show_results = True

            use_pg = False
            try:
                use_pg = bool(repo.use_pg())
            except Exception:
                use_pg = False

            if not use_pg:
                row = _create(data)
                if isinstance(row, dict):
                    row["questions"] = questions
                    row["questionCount"] = len(questions)
                    row["showResultsToStudents"] = bool(show_results)
                return row

            from sqlalchemy import text

            try:
                from db.connection import get_session
            except Exception:
                from connection import get_session  # type: ignore

            oid = str(data.get("id") or uuid.uuid4())
            title = str(data.get("title") or "").strip() or "Олимпиада"
            oly_type = str(data.get("type") or "olympiad")
            try:
                pass_score = int(data.get("passScore") or 70)
            except (TypeError, ValueError):
                pass_score = 70
            is_active = bool(data.get("isActive", True))
            start_time = data.get("startTime")
            end_time = data.get("endTime")
            duration = data.get("durationSec")
            created = data.get("createdAt")

            with get_session() as s:
                inserted = False
                for sql, params in (
                    (
                        "INSERT INTO olympiads "
                        "(id, title, type, pass_score, is_active, start_at, end_at, duration_sec, "
                        " status, questions_json, show_results_to_students) "
                        "VALUES (:id, :title, :type, :ps, :act, :st, :en, :dur, "
                        " 'published', CAST(:qjson AS jsonb), :show) "
                        "ON CONFLICT (id) DO UPDATE SET "
                        " title = EXCLUDED.title, type = EXCLUDED.type, pass_score = EXCLUDED.pass_score, "
                        " is_active = EXCLUDED.is_active, start_at = EXCLUDED.start_at, end_at = EXCLUDED.end_at, "
                        " duration_sec = EXCLUDED.duration_sec, questions_json = EXCLUDED.questions_json, "
                        " show_results_to_students = EXCLUDED.show_results_to_students, updated_at = NOW()",
                        {
                            "id": oid,
                            "title": title,
                            "type": oly_type,
                            "ps": pass_score,
                            "act": is_active,
                            "st": start_time,
                            "en": end_time,
                            "dur": duration,
                            "qjson": json.dumps(questions, ensure_ascii=False),
                            "show": bool(show_results),
                        },
                    ),
                    (
                        "INSERT INTO olympiads "
                        "(id, title, type, pass_score, is_active, start_at, end_at, duration_sec, status) "
                        "VALUES (:id, :title, :type, :ps, :act, :st, :en, :dur, 'published') "
                        "ON CONFLICT (id) DO UPDATE SET "
                        " title = EXCLUDED.title, type = EXCLUDED.type, pass_score = EXCLUDED.pass_score, "
                        " is_active = EXCLUDED.is_active, start_at = EXCLUDED.start_at, end_at = EXCLUDED.end_at, "
                        " duration_sec = EXCLUDED.duration_sec, updated_at = NOW()",
                        {
                            "id": oid,
                            "title": title,
                            "type": oly_type,
                            "ps": pass_score,
                            "act": is_active,
                            "st": start_time,
                            "en": end_time,
                            "dur": duration,
                        },
                    ),
                ):
                    try:
                        s.execute(text(sql), params)
                        inserted = True
                        break
                    except Exception as e:
                        log.warning("olympiad insert try failed: %s", e)
                        try:
                            s.rollback()
                        except Exception:
                            pass
                if not inserted:
                    return _create(data)

                try:
                    s.execute(text(
                        "DELETE FROM olympiad_options WHERE question_id IN "
                        "(SELECT id FROM olympiad_questions WHERE olympiad_id::text = :oid)"
                    ), {"oid": oid})
                    s.execute(text("DELETE FROM olympiad_questions WHERE olympiad_id::text = :oid"), {"oid": oid})
                except Exception as e:
                    log.warning("clear questions: %s", e)

                for i, q in enumerate(questions):
                    if not isinstance(q, dict):
                        continue
                    qid = str(uuid.uuid4())
                    qtype = str(q.get("type") or "single").lower()
                    qtext = str(q.get("text") or "")
                    payload = dict(q)
                    payload["id"] = q.get("id") if q.get("id") is not None else (i + 1)
                    try:
                        s.execute(text(
                            "INSERT INTO olympiad_questions "
                            "(id, olympiad_id, sort_order, text, qtype, payload) "
                            "VALUES (:id, :oid, :ord, :text, :qtype, CAST(:payload AS jsonb))"
                        ), {
                            "id": qid, "oid": oid, "ord": i, "text": qtext,
                            "qtype": qtype, "payload": json.dumps(payload, ensure_ascii=False),
                        })
                    except Exception:
                        try:
                            s.execute(text(
                                "INSERT INTO olympiad_questions "
                                "(id, olympiad_id, sort_order, text) "
                                "VALUES (:id, :oid, :ord, :text)"
                            ), {"id": qid, "oid": oid, "ord": i, "text": qtext})
                        except Exception as e2:
                            log.warning("question insert: %s", e2)
                            continue
                    if qtype == "single":
                        ans = 0
                        try:
                            ans = int(q.get("answer") or 0)
                        except (TypeError, ValueError):
                            ans = 0
                        for j, opt in enumerate(q.get("options") or []):
                            try:
                                s.execute(text(
                                    "INSERT INTO olympiad_options "
                                    "(id, question_id, sort_order, text, is_correct) "
                                    "VALUES (:id, :qid, :ord, :text, :ok)"
                                ), {
                                    "id": str(uuid.uuid4()), "qid": qid, "ord": j,
                                    "text": str(opt), "ok": j == ans,
                                })
                            except Exception as e3:
                                log.warning("option insert: %s", e3)

            found = None
            if _find:
                found = _find(oid)
            if found and isinstance(found, dict):
                found["questions"] = questions
                found["questionCount"] = len(questions)
                found["showResultsToStudents"] = bool(show_results)
                return found
            return {
                "id": oid,
                "title": title,
                "type": oly_type,
                "passScore": pass_score,
                "isActive": is_active,
                "startTime": start_time,
                "endTime": end_time,
                "durationSec": duration,
                "questions": questions,
                "questionCount": len(questions),
                "showResultsToStudents": bool(show_results),
                "createdAt": created,
            }

        repo.create_olympiad = create_olympiad
        log.info("patched repo.create_olympiad for multi-type JSON")

    if _find is not None:
        def find_olympiad(olympiad_id: str):
            o = _find(olympiad_id)
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
                    row = s.execute(text(
                        "SELECT questions_json, show_results_to_students FROM olympiads WHERE id::text = :id"
                    ), {"id": str(olympiad_id)}).mappings().first()
                if row:
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
            except Exception as e:
                log.warning("find_olympiad enrich: %s", e)
            return o

        repo.find_olympiad = find_olympiad
        log.info("patched repo.find_olympiad enrich questions_json")

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
        log.info("rebound eng.find_olympiad + hardened _public_questions")
    except Exception as e:
        log.warning("engine rebind: %s", e)

    print("[boot] patch_olympiad_questions_pg: multi-type PG storage")


if __name__ == "__main__":
    install()
