"""Durable answers on submit — answers_json MUST survive even if attempt_answers fails.

Root cause of blank Review:
  - attempt_answers.question_id is UUID in schema
  - olympiad question ids are often non-UUID strings
  - INSERT failed → whole engine.begin() rolled back → answers_json never saved
  - score was written in a separate transaction → score exists, answers blank

Fix:
  1. ALTER question_id to TEXT (idempotent)
  2. Write answers_json in its own commit (never share tx with row inserts)
  3. attempt_answers best-effort with savepoints
  4. outermost submit wrap + before_request rewrap
"""
from __future__ import annotations

import json
import logging
import uuid

log = logging.getLogger("geografia.patch_answers_durable")


def _engine():
    try:
        from db.connection import engine, is_postgres_enabled

        if is_postgres_enabled() and engine is not None:
            return engine
    except Exception:
        pass
    return None


def _ensure_schema(eng) -> None:
    from sqlalchemy import text

    with eng.begin() as conn:
        for col in ("answers_json", "score_map_json"):
            try:
                conn.execute(
                    text(f"ALTER TABLE attempts ADD COLUMN IF NOT EXISTS {col} JSONB")
                )
            except Exception as e:
                log.warning("ensure %s: %s", col, e)
        for sql in (
            "ALTER TABLE attempt_answers ALTER COLUMN question_id TYPE TEXT USING question_id::text",
            "ALTER TABLE attempt_answers ADD COLUMN IF NOT EXISTS selected_text TEXT",
            "ALTER TABLE attempt_answers ADD COLUMN IF NOT EXISTS is_correct BOOLEAN",
        ):
            try:
                conn.execute(text(sql))
            except Exception as e:
                log.debug("schema alter: %s", e)
        try:
            conn.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS attempt_answers ("
                    "id UUID PRIMARY KEY, attempt_id UUID NOT NULL, "
                    "question_id TEXT NOT NULL, selected_idx INT, "
                    "is_correct BOOLEAN, selected_text TEXT, "
                    "UNIQUE (attempt_id, question_id))"
                )
            )
        except Exception:
            pass


def persist(attempt_id, answers, score_map=None):
    eng = _engine()
    if eng is None or not attempt_id:
        log.error("persist: no engine or attempt_id")
        return False
    answers = answers if isinstance(answers, dict) else {}
    score_map = score_map if isinstance(score_map, dict) else {}
    from sqlalchemy import text

    aj = json.dumps(answers, ensure_ascii=False)
    sm = json.dumps(score_map, ensure_ascii=False)
    ok_json = False

    # 1) answers_json in its OWN transaction (must not roll back)
    try:
        with eng.begin() as conn:
            for sql in (
                "UPDATE attempts SET answers_json = CAST(:aj AS jsonb), "
                "score_map_json = CAST(:sm AS jsonb) WHERE id::text = :id",
                "UPDATE attempts SET answers_json = CAST(:aj AS jsonb), "
                "score_map_json = CAST(:sm AS jsonb) WHERE id = CAST(:id AS uuid)",
            ):
                try:
                    res = conn.execute(
                        text(sql), {"aj": aj, "sm": sm, "id": str(attempt_id)}
                    )
                    if int(res.rowcount or 0) > 0:
                        ok_json = True
                        break
                except Exception as e:
                    log.warning("answers_json try: %s", e)
        if ok_json:
            log.info("answers_json OK attempt=%s n=%d", attempt_id, len(answers))
        else:
            log.error("answers_json UPDATE 0 rows attempt=%s — row missing?", attempt_id)
    except Exception as e:
        log.error("answers_json fatal: %s", e)

    # 2) attempt_answers best-effort (separate tx, savepoints)
    try:
        with eng.begin() as conn:
            for qid, sel in answers.items():
                si, st = None, None
                if isinstance(sel, dict):
                    for k in ("i", "index", "oi", "optionIndex"):
                        if sel.get(k) is not None:
                            try:
                                si = int(sel[k])
                                break
                            except Exception:
                                pass
                    st = sel.get("t") or sel.get("text")
                    if st is not None:
                        st = str(st)
                elif isinstance(sel, int):
                    si = sel
                elif isinstance(sel, str):
                    st = sel
                qid_s = str(qid)
                sp = conn.begin_nested()
                try:
                    conn.execute(
                        text(
                            "INSERT INTO attempt_answers "
                            "(id, attempt_id, question_id, selected_idx, selected_text) "
                            "VALUES (:id, CAST(:aid AS uuid), :qid, :sel, :st) "
                            "ON CONFLICT (attempt_id, question_id) DO UPDATE SET "
                            "selected_idx = EXCLUDED.selected_idx, "
                            "selected_text = EXCLUDED.selected_text"
                        ),
                        {
                            "id": str(uuid.uuid4()),
                            "aid": str(attempt_id),
                            "qid": qid_s,
                            "sel": si,
                            "st": st,
                        },
                    )
                    sp.commit()
                except Exception as e:
                    try:
                        sp.rollback()
                    except Exception:
                        pass
                    log.warning("attempt_answers row qid=%s: %s", qid_s, e)
    except Exception as e:
        log.error("attempt_answers batch: %s", e)

    return ok_json


def install(app=None):
    eng = _engine()
    if eng is not None:
        try:
            _ensure_schema(eng)
        except Exception as e:
            log.warning("schema ensure: %s", e)

    try:
        try:
            from db import olympiad_engine as oe
        except Exception:
            import olympiad_engine as oe
    except Exception as e:
        log.warning("oe import: %s", e)
        return

    def _wrap(oe_mod):
        orig = oe_mod.submit_exam

        def wrapped(
            session_id, session_token=None, answers=None, fingerprint=None, **kwargs
        ):
            if isinstance(session_token, dict) and answers is None:
                answers = session_token
                session_token = kwargs.get("sessionToken") or kwargs.get(
                    "session_token"
                )
            answers = answers if isinstance(answers, dict) else {}
            result = orig(
                session_id,
                session_token,
                answers,
                fingerprint=fingerprint,
                **kwargs,
            )
            try:
                sm = {}
                try:
                    sessions = oe_mod._load_sessions() or {}
                    sess = sessions.get(str(session_id)) or {}
                    sm = sess.get("scoreMap") or {}
                    if sess is not None:
                        sess = dict(sess)
                        sess["answers"] = answers
                        sessions[str(session_id)] = sess
                        oe_mod._save_sessions(sessions)
                except Exception:
                    pass
                ok = persist(str(session_id), answers, sm)
                if not ok:
                    log.error(
                        "persist FAILED after submit attempt=%s n_answers=%d",
                        session_id,
                        len(answers),
                    )
                elif not answers:
                    log.warning("submit with EMPTY answers attempt=%s", session_id)
            except Exception as e:
                log.error("post-submit persist: %s", e)
            return result

        oe_mod.submit_exam = wrapped

    _wrap(oe)

    if app is not None:

        @app.before_request
        def _rewrap():
            if getattr(app, "_durable_answers_rewrap", False):
                return
            app._durable_answers_rewrap = True
            try:
                try:
                    from db import olympiad_engine as oe2
                except Exception:
                    import olympiad_engine as oe2
                _wrap(oe2)
            except Exception as e:
                log.warning("rewrap fail: %s", e)

        try:
            from flask import jsonify

            def _attempt_debug(aid):
                eng2 = _engine()
                if eng2 is None:
                    return jsonify({"error": "no pg"}), 500
                from sqlalchemy import text

                with eng2.connect() as conn:
                    row = conn.execute(
                        text(
                            "SELECT id::text, status::text, score, "
                            "answers_json IS NOT NULL AS has_aj, "
                            "score_map_json IS NOT NULL AS has_sm, "
                            "finished_at "
                            "FROM attempts WHERE id::text = :id"
                        ),
                        {"id": str(aid)},
                    ).mappings().first()
                    n_aa = 0
                    try:
                        n_aa = int(
                            conn.execute(
                                text(
                                    "SELECT COUNT(*) FROM attempt_answers "
                                    "WHERE attempt_id::text = :id"
                                ),
                                {"id": str(aid)},
                            ).scalar()
                            or 0
                        )
                    except Exception:
                        n_aa = -1
                if not row:
                    return jsonify({"error": "not_found", "id": aid}), 404
                return jsonify(
                    {
                        "id": row["id"],
                        "status": row["status"],
                        "score": row["score"],
                        "hasAnswersJson": bool(row["has_aj"]),
                        "hasScoreMapJson": bool(row["has_sm"]),
                        "attemptAnswersRows": n_aa,
                        "finishedAt": str(row["finished_at"])
                        if row["finished_at"]
                        else None,
                    }
                )

            app.add_url_rule(
                "/api/admin/attempts/<aid>/debug-answers",
                "attempt_debug_answers",
                _attempt_debug,
                methods=["GET"],
            )
        except Exception as e:
            log.warning("debug route: %s", e)

    print(
        "[boot] patch_answers_durable: answers_json own-tx + question_id TEXT + savepoints"
    )
    log.info("patch_answers_durable installed (split-tx)")
