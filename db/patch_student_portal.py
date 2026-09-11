"""Student portal: login + olympiads with one-attempt flags."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from flask import jsonify, request

log = logging.getLogger("geografia.patch_student_portal")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _window_status(oly: dict) -> str:
    if oly.get("isActive") is False:
        return "closed"
    now = _now()

    def parse(v):
        if not v:
            return None
        if isinstance(v, datetime):
            return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
        try:
            s = str(v).replace("Z", "+00:00")
            d = datetime.fromisoformat(s)
            return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
        except Exception:
            return None

    start = parse(oly.get("startTime") or oly.get("start_at"))
    end = parse(oly.get("endTime") or oly.get("end_at"))
    if start and now < start:
        return "not_started"
    if end and now > end:
        return "ended"
    return "open"


def _public_student(st: dict | None) -> dict | None:
    if not st:
        return None
    return {
        "id": st.get("id") or st.get("student_code"),
        "fullName": st.get("fullName") or st.get("full_name"),
        "className": st.get("className") or st.get("class_name"),
        "school": st.get("school") or st.get("school_name") or "",
    }


def install(app) -> None:
    from db.repo import find_student_by_code, list_olympiads

    def student_login():
        payload = request.get_json(silent=True) or {}
        code = str(
            payload.get("studentId") or payload.get("id") or payload.get("code") or ""
        ).strip()
        if not code:
            return jsonify({"error": "ID-и хонанда лозим аст."}), 400
        st = find_student_by_code(code)
        if not st:
            return jsonify({"error": "ID нодуруст аст ё хонанда ёфт нашуд.", "reason": "student_not_found"}), 401
        return jsonify({"ok": True, "student": _public_student(st)})

    def student_olympiads():
        code = str(
            request.args.get("studentId")
            or request.args.get("id")
            or request.headers.get("X-Student-Id")
            or ""
        ).strip()
        if not code:
            body = request.get_json(silent=True) or {}
            code = str(body.get("studentId") or body.get("id") or body.get("code") or "").strip()
        if not code:
            return jsonify({"error": "studentId лозим аст."}), 400
        st = find_student_by_code(code)
        if not st:
            return jsonify({"error": "Хонанда ёфт нашуд.", "reason": "student_not_found"}), 401

        try:
            items = list_olympiads() or []
        except Exception as e:
            log.warning("list_olympiads: %s", e)
            items = []

        olympiads, quizzes = [], []
        for o in items:
            if not isinstance(o, dict) or o.get("isActive") is False:
                continue
            oid = str(o.get("id") or "")
            if not oid:
                continue
            window = _window_status(o)
            access = {"allowed": True, "reason": "open"}
            try:
                from db.student_access import student_has_olympiad_access
                access = student_has_olympiad_access(oid, code)
            except Exception as e:
                log.warning("access check %s: %s", oid, e)
            allowed = bool(access.get("allowed"))

            att_status, already = None, False
            try:
                from sqlalchemy import text as _t
                from db.connection import get_engine
                _eng = get_engine()
                if _eng is not None:
                    with _eng.connect() as _conn:
                        _row = _conn.execute(
                            _t(
                                """SELECT CAST(status AS text) AS status, finished_at
                                   FROM attempts
                                   WHERE olympiad_id::text = :oid
                                     AND (
                                       student_id::text = :code
                                       OR TRIM(COALESCE(student_name,'')) = :code
                                       OR student_id IN (
                                         SELECT id FROM students
                                         WHERE student_code = :code OR id::text = :code
                                       )
                                     )
                                   ORDER BY CASE WHEN finished_at IS NOT NULL THEN 0 ELSE 1 END,
                                            finished_at DESC NULLS LAST
                                   LIMIT 1"""
                            ),
                            {"oid": oid, "code": code},
                        ).mappings().first()
                        if _row:
                            att_status = str(_row.get("status") or "").lower()
                            if att_status in (
                                "finished", "passed", "failed", "timeout", "submitted",
                                "complete", "completed",
                            ) or _row.get("finished_at") is not None:
                                already = True
            except Exception as e:
                log.warning("attempt status %s: %s", oid, e)

            card = {
                "id": oid,
                "title": o.get("title") or "Бе ном",
                "description": o.get("description") or "",
                "type": (o.get("type") or "olympiad").lower(),
                "passScore": o.get("passScore") or 70,
                "questionCount": o.get("questionCount") or len(o.get("questions") or []),
                "isActive": o.get("isActive") is not False,
                "isOpen": window == "open" and allowed and not already,
                "windowStatus": window if allowed else ("locked" if window == "open" else window),
                "accessAllowed": allowed,
                "accessReason": access.get("reason"),
                "startTime": o.get("startTime"),
                "endTime": o.get("endTime"),
                "durationSec": o.get("durationSec"),
                "attemptStatus": att_status,
                "alreadySubmitted": already,
                "finished": already,
                "submitted": already,
            }
            (quizzes if card["type"] == "quiz" else olympiads).append(card)

        return jsonify({
            "ok": True,
            "student": _public_student(st),
            "olympiads": olympiads,
            "quizzes": quizzes,
        })

    def _bind(rule, ep, fn, methods):
        for r in list(app.url_map.iter_rules()):
            if r.rule == rule:
                app.view_functions[r.endpoint] = fn
        if ep in app.view_functions:
            app.view_functions[ep] = fn
        try:
            app.add_url_rule(rule, ep, fn, methods=methods)
        except Exception:
            pass

    _bind("/api/student/login", "student_portal_login", student_login, ["POST"])
    if "student_login" in app.view_functions:
        app.view_functions["student_login"] = student_login
    _bind("/api/student/olympiads", "student_portal_olympiads", student_olympiads, ["GET"])
    print("[boot] patch_student_portal: login + olympiads + one-attempt-ui")
