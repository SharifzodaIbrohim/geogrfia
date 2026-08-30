"""Tiny durable answers fix: outermost submit wrap + engine.begin persist."""
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


def persist(attempt_id, answers, score_map=None):
    eng = _engine()
    if eng is None or not attempt_id:
        return False
    answers = answers if isinstance(answers, dict) else {}
    score_map = score_map if isinstance(score_map, dict) else {}
    from sqlalchemy import text

    aj = json.dumps(answers, ensure_ascii=False)
    sm = json.dumps(score_map, ensure_ascii=False)
    ok = False
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
                        ok = True
                        break
                except Exception as e:
                    log.warning("answers_json: %s", e)
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
                            "qid": str(qid),
                            "sel": si,
                            "st": st,
                        },
                    )
                except Exception as e:
                    log.error("attempt_answers %s: %s", qid, e)
        if ok:
            log.info("durable answers OK %s n=%d", attempt_id, len(answers))
        else:
            log.error("durable answers UPDATE 0 rows id=%s", attempt_id)
        return ok
    except Exception as e:
        log.error("durable persist fatal: %s", e)
        return False


def install(app=None):
    try:
        try:
            from db import olympiad_engine as oe
        except Exception:
            import olympiad_engine as oe
    except Exception as e:
        log.warning("oe import: %s", e)
        return

    eng = _engine()
    if eng is not None:
        from sqlalchemy import text

        try:
            with eng.begin() as conn:
                for col in ("answers_json", "score_map_json"):
                    try:
                        conn.execute(
                            text(
                                f"ALTER TABLE attempts ADD COLUMN IF NOT EXISTS {col} JSONB"
                            )
                        )
                    except Exception:
                        pass
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
                try:
                    conn.execute(
                        text(
                            "ALTER TABLE attempt_answers "
                            "ADD COLUMN IF NOT EXISTS selected_text TEXT"
                        )
                    )
                except Exception:
                    pass
        except Exception as e:
            log.warning("schema: %s", e)

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
                    sess = (oe_mod._load_sessions() or {}).get(str(session_id)) or {}
                    sm = sess.get("scoreMap") or {}
                    if sess is not None:
                        sess = dict(sess)
                        sess["answers"] = answers
                        sessions = oe_mod._load_sessions() or {}
                        sessions[str(session_id)] = sess
                        oe_mod._save_sessions(sessions)
                except Exception:
                    pass
                persist(str(session_id), answers, sm)
            except Exception as e:
                log.error("post-submit: %s", e)
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

    print("[boot] patch_answers_durable: engine.begin answers_json + attempt_answers")
    log.info("patch_answers_durable installed")
