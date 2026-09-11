"""Durable answers on submit — answers_json MUST survive even if attempt_answers fails.

History / root causes:
  - attempt_answers.question_id is UUID in schema
  - client may send answer as index string "0" / "1" (not option text)
  - INSERT failed → whole engine.begin() rolled back → answers_json never saved
  - score was written in a separate transaction → score exists, answers blank

Fix:
  1. Ensure schema columns
  2. Write answers_json in its own commit (never share tx with row inserts)
  3. attempt_answers best-effort with savepoints
  4. Map pure digit / letter answers → selected_idx
"""
from __future__ import annotations
import json, logging, uuid
from sqlalchemy import text

log = logging.getLogger("geografia.patch_answers_durable")

def _eng():
    try:
        from db.connection import get_engine
        e = get_engine()
        if e is not None:
            return e
    except Exception:
        pass
    from db import connection as c
    return getattr(c, "engine", None)

def ensure_schema(eng=None):
    eng = eng or _eng()
    if eng is None:
        return
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
            try:
                conn.execute(text(
                    "CREATE TABLE IF NOT EXISTS attempt_answers ("
                    "id TEXT PRIMARY KEY, attempt_id UUID, "
                    "question_id TEXT NOT NULL, selected_idx INT, "
                    "is_correct BOOLEAN, selected_text TEXT, "
                    "UNIQUE (attempt_id, question_id))"
                ))
            except Exception:
                pass
    except Exception as e:
        log.warning("ensure_schema: %s", e)

def persist(attempt_id, answers, score_map=None):
    eng = _eng()
    if eng is None:
        return False
    attempt_id = str(attempt_id or "").strip()
    if not attempt_id:
        return False
    answers = answers if isinstance(answers, dict) else {}
    ensure_schema(eng)
    aj = json.dumps(answers, ensure_ascii=False)
    sm = json.dumps(score_map or {}, ensure_ascii=False)
    try:
        with eng.begin() as conn:
            updated = 0
            for stmt in (
                "UPDATE attempts SET answers_json = CAST(:aj AS jsonb), score_map_json = CAST(:sm AS jsonb) WHERE id::text = :id",
                "UPDATE attempts SET answers_json = :aj::jsonb WHERE id::text = :id",
            ):
                try:
                    r = conn.execute(text(stmt), {"aj": aj, "sm": sm, "id": attempt_id})
                    updated = r.rowcount or 0
                    if updated:
                        break
                except Exception as e:
                    log.warning("answers_json try: %s", e)
            if updated:
                log.info("answers_json OK attempt=%s n=%d", attempt_id, len(answers))
            else:
                log.error("answers_json UPDATE 0 rows attempt=%s — row missing?", attempt_id)
    except Exception as e:
        log.error("answers_json fatal: %s", e)

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
                    st = None
                elif isinstance(sel, str):
                    s = sel.strip()
                    if s.isdigit():
                        try:
                            si = int(s)
                            st = None  # text resolved at review from opts
                        except Exception:
                            st = s
                    elif len(s) == 1 and s.upper() in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                        si = ord(s.upper()) - 65
                        st = None
                    else:
                        st = s
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
                            "aid": attempt_id,
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
    return True

def install(app=None):
    ensure_schema()
    print("[boot] patch_answers_durable OK")
