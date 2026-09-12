"""Durable answers_json on submit — MUST wrap submit_exam."""
from __future__ import annotations
import json, logging, uuid
log = logging.getLogger("geografia.patch_answers_durable")

def _engine():
    try:
        from db.connection import engine, is_postgres_enabled
        if is_postgres_enabled() and engine is not None:
            return engine
    except Exception:
        pass
    return None

def ensure_schema(eng=None):
    eng = eng or _engine()
    if eng is None:
        return
    from sqlalchemy import text
    try:
        with eng.begin() as conn:
            for col in ("answers_json", "score_map_json"):
                try:
                    conn.execute(text(f"ALTER TABLE attempts ADD COLUMN IF NOT EXISTS {col} JSONB"))
                except Exception:
                    pass
            for stmt in (
                "ALTER TABLE attempt_answers ALTER COLUMN question_id TYPE TEXT USING question_id::text",
                "ALTER TABLE attempt_answers ADD COLUMN IF NOT EXISTS selected_text TEXT",
                "ALTER TABLE attempt_answers ADD COLUMN IF NOT EXISTS is_correct BOOLEAN",
            ):
                try:
                    conn.execute(text(stmt))
                except Exception:
                    pass
    except Exception as e:
        log.warning("ensure_schema: %s", e)

def persist(attempt_id, answers, score_map=None):
    eng = _engine()
    if eng is None or not attempt_id:
        return False
    answers = answers if isinstance(answers, dict) else {}
    from sqlalchemy import text
    aj = json.dumps(answers, ensure_ascii=False)
    sm = json.dumps(score_map or {}, ensure_ascii=False)
    ok = False
    try:
        with eng.begin() as conn:
            for sql in (
                "UPDATE attempts SET answers_json = CAST(:aj AS jsonb), score_map_json = CAST(:sm AS jsonb) WHERE id::text = :id",
                "UPDATE attempts SET answers_json = CAST(:aj AS jsonb), score_map_json = CAST(:sm AS jsonb) WHERE id = CAST(:id AS uuid)",
            ):
                try:
                    res = conn.execute(text(sql), {"aj": aj, "sm": sm, "id": str(attempt_id)})
                    if int(res.rowcount or 0) > 0:
                        ok = True
                        break
                except Exception as e:
                    log.warning("answers_json try: %s", e)
        if ok:
            log.info("answers_json OK attempt=%s n=%d", attempt_id, len(answers))
        else:
            log.error("answers_json UPDATE 0 rows attempt=%s", attempt_id)
    except Exception as e:
        log.error("answers_json fatal: %s", e)
    return ok

def install(app=None):
    ensure_schema()
    try:
        from db import olympiad_engine as oe
    except Exception as e:
        log.warning("oe import: %s", e)
        print("[boot] patch_answers_durable: no oe")
        return

    def _wrap(oe_mod):
        orig = getattr(oe_mod, "submit_exam", None)
        if not callable(orig):
            return
        if getattr(orig, "_durable_wrapped", False):
            return
        def wrapped(session_id, session_token=None, answers=None, fingerprint=None, **kwargs):
            if isinstance(session_token, dict) and answers is None:
                answers = session_token
                session_token = kwargs.get("sessionToken") or kwargs.get("session_token")
            answers = answers if isinstance(answers, dict) else {}
            result = orig(session_id, session_token, answers, fingerprint=fingerprint, **kwargs)
            try:
                sm = {}
                try:
                    sess = (oe_mod._load_sessions() or {}).get(str(session_id)) or {}
                    sm = sess.get("scoreMap") or {}
                except Exception:
                    pass
                persist(str(session_id), answers, sm)
                if not answers:
                    log.warning("submit EMPTY answers attempt=%s", session_id)
            except Exception as e:
                log.error("post-submit persist: %s", e)
            return result
        wrapped._durable_wrapped = True
        oe_mod.submit_exam = wrapped
        _as = getattr(oe_mod, "autosave", None)
        if callable(_as) and not getattr(_as, "_durable_wrapped", False):
            def as_wrapped(session_id, session_token, answers, fingerprint=None, **kwargs):
                r = _as(session_id, session_token, answers, fingerprint=fingerprint, **kwargs)
                try:
                    if isinstance(answers, dict) and answers:
                        persist(str(session_id), answers, None)
                except Exception as e:
                    log.warning("autosave persist: %s", e)
                return r
            as_wrapped._durable_wrapped = True
            oe_mod.autosave = as_wrapped

    _wrap(oe)
    if app is not None:
        @app.before_request
        def _rewrap():
            if getattr(app, "_durable_answers_rewrap", False):
                return
            app._durable_answers_rewrap = True
            try:
                from db import olympiad_engine as oe2
                _wrap(oe2)
            except Exception as e:
                log.warning("rewrap: %s", e)
    print("[boot] patch_answers_durable: submit+autosave wrap OK")
    log.info("patch_answers_durable installed")
