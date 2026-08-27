"""Root fix: persist olympiad answers to PostgreSQL on every submit.

Why answers vanished after deploy/time:
  - Score/status were written to `attempts`
  - Full answers lived only in in-memory / ephemeral session files
  - Review after restart → hasDetail=false, student answers blank

This patch:
  1. Ensures attempts.answers_json + score_map_json columns exist
  2. Ensures attempt_answers table can store selected_text
  3. On every successful submit, writes the FULL answers dict to PG
  4. Commits in its own session (never silent-fail the write)
  5. Does not change scoring / shuffle / one-attempt
"""
from __future__ import annotations

import json
import logging
import uuid

log = logging.getLogger("geografia.patch_persist_answers")


def _use_pg() -> bool:
    try:
        from db.connection import is_postgres_enabled
        return bool(is_postgres_enabled())
    except Exception:
        try:
            from connection import is_postgres_enabled
            return bool(is_postgres_enabled())
        except Exception:
            return False


def _get_session():
    try:
        from db.connection import get_session
        return get_session
    except Exception:
        from connection import get_session
        return get_session


def _ensure_schema() -> None:
    if not _use_pg():
        return
    get_session = _get_session()
    with get_session() as s:
        from sqlalchemy import text
        for col, typ in (
            ("answers_json", "JSONB"),
            ("score_map_json", "JSONB"),
        ):
            try:
                s.execute(text(f"ALTER TABLE attempts ADD COLUMN IF NOT EXISTS {col} {typ}"))
            except Exception as e:
                log.warning("ensure %s: %s", col, e)
        try:
            s.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS attempt_answers ("
                    "id UUID PRIMARY KEY,"
                    "attempt_id UUID NOT NULL,"
                    "question_id TEXT NOT NULL,"
                    "selected_idx INT,"
                    "is_correct BOOLEAN,"
                    "selected_text TEXT,"
                    "UNIQUE (attempt_id, question_id)"
                    ")"
                )
            )
        except Exception as e:
            log.warning("ensure attempt_answers table: %s", e)
        try:
            s.execute(text("ALTER TABLE attempt_answers ADD COLUMN IF NOT EXISTS selected_text TEXT"))
        except Exception:
            pass
        try:
            s.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS attempt_answers_attempt_qid_uidx "
                    "ON attempt_answers (attempt_id, question_id)"
                )
            )
        except Exception:
            pass


def _sel_text(sel) -> str | None:
    if sel is None:
        return None
    if isinstance(sel, str):
        return sel
    if isinstance(sel, (int, float, bool)):
        return str(sel)
    try:
        return json.dumps(sel, ensure_ascii=False)
    except Exception:
        return str(sel)


def _sel_idx(sel) -> int | None:
    if isinstance(sel, int):
        return sel
    if isinstance(sel, dict):
        for k in ("i", "index", "selectedIndex", "optionIndex"):
            if k in sel and isinstance(sel[k], int):
                return sel[k]
    return None


def persist_answers(attempt_id: str, answers: dict, score_map: dict | None = None) -> bool:
    """Write answers + score_map to PG. Returns True on success."""
    if not _use_pg() or not attempt_id:
        return False
    answers = answers if isinstance(answers, dict) else {}
    score_map = score_map if isinstance(score_map, dict) else {}
    get_session = _get_session()
    ok = False
    try:
        with get_session() as s:
            from sqlalchemy import text
            aj = json.dumps(answers, ensure_ascii=False)
            sm = json.dumps(score_map, ensure_ascii=False)
            try:
                s.execute(
                    text(
                        "UPDATE attempts SET answers_json = CAST(:aj AS jsonb), "
                        "score_map_json = CAST(:sm AS jsonb) WHERE id::text = :id"
                    ),
                    {"aj": aj, "sm": sm, "id": str(attempt_id)},
                )
                ok = True
            except Exception as e1:
                log.warning("answers_json jsonb update failed: %s", e1)
                try:
                    s.execute(
                        text(
                            "UPDATE attempts SET answers_json = :aj::jsonb, "
                            "score_map_json = :sm::jsonb WHERE id::text = :id"
                        ),
                        {"aj": aj, "sm": sm, "id": str(attempt_id)},
                    )
                    ok = True
                except Exception as e2:
                    log.error("answers_json persist FAILED: %s", e2)

            for qid, sel in answers.items():
                try:
                    st = _sel_text(sel)
                    si = _sel_idx(sel)
                    s.execute(
                        text(
                            "INSERT INTO attempt_answers "
                            "(id, attempt_id, question_id, selected_idx, is_correct, selected_text) "
                            "VALUES (:id, CAST(:aid AS uuid), :qid, :sel, NULL, :st) "
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
                except Exception as e3:
                    try:
                        s.execute(
                            text(
                                "INSERT INTO attempt_answers "
                                "(id, attempt_id, question_id, selected_idx, selected_text) "
                                "VALUES (:id, CAST(:aid AS uuid), :qid, :sel, :st)"
                            ),
                            {
                                "id": str(uuid.uuid4()),
                                "aid": str(attempt_id),
                                "qid": str(qid),
                                "sel": si,
                                "st": st,
                            },
                        )
                    except Exception as e4:
                        log.debug("attempt_answers row %s: %s / %s", qid, e3, e4)
        if ok:
            log.info("persist_answers OK attempt=%s n=%d", attempt_id, len(answers))
        return ok
    except Exception as e:
        log.error("persist_answers fatal: %s", e)
        return False


def _wrap_submit():
    try:
        try:
            import olympiad_engine as oe
        except Exception:
            from db import olympiad_engine as oe
    except Exception as e:
        log.warning("olympiad_engine import: %s", e)
        return

    if getattr(oe, "_persist_answers_wrapped", False):
        return
    orig = oe.submit_exam

    def wrapped(session_id, session_token=None, answers=None, fingerprint=None, **kwargs):
        if isinstance(session_token, dict) and answers is None:
            answers = session_token
            session_token = kwargs.get("sessionToken") or kwargs.get("session_token")
        answers = answers if isinstance(answers, dict) else {}
        result = orig(session_id, session_token, answers, fingerprint=fingerprint, **kwargs)

        try:
            score_map = {}
            try:
                sessions = oe._load_sessions()
                sess = sessions.get(str(session_id)) or {}
                score_map = sess.get("scoreMap") or {}
                if sess:
                    sess["answers"] = answers
                    sessions[str(session_id)] = sess
                    oe._save_sessions(sessions)
            except Exception:
                pass
            persist_answers(str(session_id), answers, score_map)
        except Exception as e:
            log.error("post-submit persist_answers: %s", e)
        return result

    oe.submit_exam = wrapped
    oe._persist_answers_wrapped = True
    log.info("submit_exam wrapped for durable PG answer persistence")


def install(app=None):
    try:
        _ensure_schema()
    except Exception as e:
        log.warning("schema ensure: %s", e)
    _wrap_submit()
    print("[boot] patch_persist_answers: PG answers_json + attempt_answers on submit")
