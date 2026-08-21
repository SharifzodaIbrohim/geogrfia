"""Boot patch: ensure attempts INSERT always includes kind (NOT NULL)."""
from __future__ import annotations
import logging

log = logging.getLogger("geografia.patch_attempts_kind")


def install(app=None):
    try:
        from db import olympiad_engine as oe
    except Exception as e:
        print("[boot] patch_attempts_kind: engine import failed:", e)
        return

    orig = getattr(oe, "start_exam", None)
    if not callable(orig):
        print("[boot] patch_attempts_kind: no start_exam")
        return

    def wrapped_start_exam(olympiad_id, student_code, fingerprint=None, **kwargs):
        result = orig(olympiad_id, student_code, fingerprint=fingerprint, **kwargs)
        try:
            from db.connection import get_session, is_postgres_enabled
            from sqlalchemy import text
            if not is_postgres_enabled() or not isinstance(result, dict):
                return result
            sid = result.get("sessionId") or result.get("id") or result.get("attemptId")
            if not sid:
                return result
            with get_session() as s:
                s.execute(
                    text(
                        "UPDATE attempts SET kind = 'olympiad' "
                        "WHERE id::text = :id AND (kind IS NULL OR kind = '')"
                    ),
                    {"id": str(sid)},
                )
                row = s.execute(
                    text("SELECT id FROM attempts WHERE id::text = :id"),
                    {"id": str(sid)},
                ).fetchone()
                if not row:
                    su = None
                    try:
                        su = oe._student_uuid(student_code)
                    except Exception:
                        pass
                    try:
                        s.execute(
                            text(
                                "INSERT INTO attempts "
                                "(id, kind, olympiad_id, student_id, status, started_at, session_token) "
                                "VALUES (:id, 'olympiad', :oid, :sid, 'in_progress', NOW(), :tok) "
                                "ON CONFLICT (id) DO UPDATE SET kind = COALESCE(attempts.kind, 'olympiad')"
                            ),
                            {
                                "id": str(sid),
                                "oid": str(olympiad_id),
                                "sid": su,
                                "tok": result.get("sessionToken"),
                            },
                        )
                    except Exception as e2:
                        log.warning("patch_attempts_kind insert: %s", e2)
        except Exception as e:
            log.warning("patch_attempts_kind post-fix: %s", e)
        return result

    oe.start_exam = wrapped_start_exam
    print("[boot] patch_attempts_kind: start_exam wrapped (kind NOT NULL fix)")
    log.info("patch_attempts_kind installed")
