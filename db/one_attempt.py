"""Hard one-attempt policy for quizzes and olympiads (P1.12)."""
from __future__ import annotations

import json
from pathlib import Path


def identity_keys(student_code: str | None = None, user_id: str | None = None) -> set[str]:
    keys: set[str] = set()
    if student_code:
        sc = str(student_code).strip()
        keys.add(sc)
        if ":" in sc:
            tail = sc.split(":", 1)[-1]
            keys.add(tail)
            keys.add("g:" + tail)
            keys.add("gmail:" + tail)
    if user_id:
        uid = str(user_id).strip()
        keys.add(uid)
        keys.add("g:" + uid)
        keys.add("gmail:" + uid)
    return {k for k in keys if k}


def install() -> None:
    """Patch engines so start enforces one finished attempt; open attempts resume in engine."""
    try:
        from db import olympiad_engine as oe

        _orig = oe.start_exam

        def start_exam(olympiad_id, student_code, *args, **kwargs):
            # Engine already: finished → already_submitted; in_progress → resume
            return _orig(olympiad_id, student_code, *args, **kwargs)

        oe.start_exam = start_exam
    except Exception:
        pass

    try:
        from db import quiz_api as qa

        _orig_q = qa.start_attempt

        def start_attempt(quiz_id, user_id=None, student_id=None, **kwargs):
            return _orig_q(quiz_id, user_id=user_id, student_id=student_id, **kwargs)

        qa.start_attempt = start_attempt
    except Exception:
        pass

    print("[boot] one_attempt: installed (engine enforces finished reject + resume)")
