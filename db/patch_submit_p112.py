"""P1.12 — Force submit to close attempts (status finished + score).

Legacy server_core submit only wrote repo.save_result and left attempts.in_progress.
This patch rebinds the Flask view after boot so olympiad_engine.submit_exam always runs.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from flask import jsonify, request

log = logging.getLogger("geografia.patch_submit")


def install(app) -> None:
    try:
        from db import olympiad_engine as oe
        from db import repo
    except Exception as e:
        log.error("patch_submit imports failed: %s", e)
        return

    def _student_id(payload: dict) -> str:
        return str(
            payload.get("studentId")
            or payload.get("id")
            or request.headers.get("X-Student-Id")
            or ""
        ).strip()

    def _normalize_answers(answers: Any) -> dict:
        if isinstance(answers, list):
            amap: dict = {}
            for i, a in enumerate(answers):
                if isinstance(a, dict):
                    qid = a.get("questionId", a.get("id", i))
                    sel = a.get("selected", a.get("selectedIndex", a.get("answer")))
                    if qid is not None and sel is not None:
                        amap[str(qid)] = sel
                else:
                    try:
                        amap[str(i)] = int(a)
                    except (TypeError, ValueError):
                        pass
            return amap
        if isinstance(answers, dict):
            return {str(k): v for k, v in answers.items()}
        return {}

    def submit_olympiad(olympiad_id: str):
        payload = request.get_json(silent=True) or {}
        student_id = _student_id(payload)
        session_id = str(payload.get("sessionId") or payload.get("attemptId") or "").strip()
        session_token = str(payload.get("sessionToken") or "").strip()
        answers = _normalize_answers(payload.get("answers"))

        try:
            if not session_id or not session_token:
                resolved = oe.resolve_session_for_submit(
                    olympiad_id,
                    student_code=student_id or None,
                    session_id=session_id or None,
                )
                if not resolved:
                    return jsonify({
                        "error": "Сессия ёфт нашуд. Аввал start кунед.",
                        "reason": "session_not_found",
                    }), 400
                session_id = resolved["sessionId"]
                session_token = resolved["sessionToken"]
                if not student_id:
                    student_id = str(resolved.get("studentId") or "")

            out = oe.submit_exam(session_id, session_token, answers)
            res = out.get("result") or out

            try:
                student = repo.find_student_by_code(student_id) if student_id else None
                olympiad = repo.find_olympiad(olympiad_id) or {}
                legacy = {
                    "id": res.get("attemptId") or session_id or str(uuid.uuid4()),
                    "studentId": student_id,
                    "studentName": (student or {}).get("fullName"),
                    "studentClass": (student or {}).get("className"),
                    "studentSchool": (student or {}).get("school"),
                    "className": (student or {}).get("className"),
                    "school": (student or {}).get("school"),
                    "olympiadId": olympiad_id,
                    "olympiadTitle": olympiad.get("title"),
                    "score": res.get("score"),
                    "correct": res.get("correct"),
                    "total": res.get("total"),
                    "passScore": res.get("passScore"),
                    "status": res.get("status"),
                    "finishedAt": res.get("finishedAt"),
                }
                repo.save_result(legacy)
            except Exception as e:
                log.warning("legacy save_result: %s", e)

            return jsonify({
                "ok": True,
                "result": {
                    "score": res.get("score"),
                    "correct": res.get("correct"),
                    "total": res.get("total"),
                    "passScore": res.get("passScore"),
                    "status": res.get("status"),
                    "finishedAt": res.get("finishedAt"),
                    "attemptId": res.get("attemptId") or session_id,
                },
            })
        except ValueError as e:
            code = str(e)
            messages = {
                "already_submitted": "Аллакай супорида шудааст.",
                "session_not_found": "Сессия ёфт нашуд.",
                "not_found": "Ёфт нашуд.",
                "timeout": "Вақт ба охир расид.",
            }
            return jsonify({"error": messages.get(code, code), "reason": code}), 400
        except Exception as e:
            log.exception("submit_olympiad patch failed")
            return jsonify({"error": "Хатои дохилӣ.", "reason": str(e)[:200]}), 500

    app.view_functions["submit_olympiad"] = submit_olympiad
    for name in list(app.view_functions.keys()):
        if name in ("olympiad_submit", "olympiad_exam_submit"):
            app.view_functions[name] = submit_olympiad

    log.info("P1.12 patch_submit installed — submit closes attempts")
    print("[boot] P1.12 patch_submit: submit closes attempts")
