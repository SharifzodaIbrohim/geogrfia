"""
Student portal APIs used by /student (login + olympiad list).

Routes:
  POST /api/student/login          { studentId }
  GET  /api/student/olympiads?studentId=
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from flask import jsonify, request

log = logging.getLogger("geografia.student_portal")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _window_status(oly: dict) -> str:
    """open | not_started | ended | closed"""
    if not oly.get("isActive"):
        return "closed"
    now = _now()
    st = oly.get("startTime") or oly.get("start_at")
    et = oly.get("endTime") or oly.get("end_at")

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

    start = parse(st)
    end = parse(et)
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
    from db import student_access

    def student_login():
        payload = request.get_json(silent=True) or {}
        code = str(
            payload.get("studentId")
            or payload.get("id")
            or payload.get("code")
            or ""
        ).strip()
        if not code:
            return jsonify({"error": "ID-и хонанда лозим аст."}), 400
        st = find_student_by_code(code)
        if not st:
            return jsonify({
                "error": "ID нодуруст аст ё хонанда ёфт нашуд.",
                "reason": "student_not_found",
            }), 401
        pub = _public_student(st)
        return jsonify({"ok": True, "student": pub})

    def student_olympiads():
        code = str(
            request.args.get("studentId")
            or (request.get_json(silent=True) or {}).get("studentId")
            or ""
        ).strip()
        if not code:
            return jsonify({"error": "studentId лозим аст."}), 400
        st = find_student_by_code(code)
        if not st:
            return jsonify({"error": "Хонанда ёфт нашуд.", "olympiads": [], "quizzes": []}), 401

        olympiads = []
        quizzes = []
        try:
            items = list_olympiads() or []
        except Exception as e:
            log.warning("list_olympiads: %s", e)
            items = []

        for o in items:
            if not o.get("isActive"):
                continue
            window = _window_status(o)
            access = student_access.student_has_olympiad_access(str(o.get("id")), code)
            if not access.get("allowed"):
                continue
            card = {
                "id": o.get("id"),
                "title": o.get("title"),
                "description": o.get("description") or "",
                "type": o.get("type") or "olympiad",
                "passScore": o.get("passScore") or 70,
                "questionCount": o.get("questionCount") or len(o.get("questions") or []),
                "isActive": True,
                "isOpen": window == "open",
                "windowStatus": window,
                "startTime": o.get("startTime"),
                "endTime": o.get("endTime"),
                "durationSec": o.get("durationSec"),
            }
            if (o.get("type") or "olympiad").lower() == "quiz":
                quizzes.append(card)
            else:
                olympiads.append(card)

        return jsonify({
            "ok": True,
            "student": _public_student(st),
            "olympiads": olympiads + quizzes,  # JS filters by type; also include all
            "quizzes": quizzes,
        })

    for rule, ep, fn, methods in [
        ("/api/student/login", "student_portal_login", student_login, ["POST"]),
        ("/api/student/olympiads", "student_portal_olympiads", student_olympiads, ["GET"]),
    ]:
        # Override any existing handler for the same path
        for r in list(app.url_map.iter_rules()):
            if r.rule == rule:
                app.view_functions[r.endpoint] = fn
        if ep in app.view_functions:
            app.view_functions[ep] = fn
        else:
            try:
                app.add_url_rule(rule, ep, fn, methods=methods)
            except AssertionError:
                # path exists under another endpoint — replace it
                for r in list(app.url_map.iter_rules()):
                    if r.rule == rule:
                        app.view_functions[r.endpoint] = fn

    log.info("student portal routes installed")
    print("[boot] student portal: /api/student/login + /api/student/olympiads")
