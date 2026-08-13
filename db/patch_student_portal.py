"""Student portal: /api/student/login + /api/student/olympiads.

Ensures students see active olympiads/quizzes and can start them.
Empty participant list → open to any valid Student ID (school mode).
"""
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
        return jsonify({"ok": True, "student": _public_student(st)})

    def student_olympiads():
        code = str(
            request.args.get("studentId")
            or request.args.get("id")
            or request.headers.get("X-Student-Id")
            or (request.get_json(silent=True) or {}).get("studentId")
            or (request.get_json(silent=True) or {}).get("id")
            or ""
        ).strip()
        if not code:
            return jsonify({"error": "studentId лозим аст.", "olympiads": [], "quizzes": []}), 400
        st = find_student_by_code(code)
        if not st:
            return jsonify({
                "error": "Хонанда ёфт нашуд.",
                "olympiads": [],
                "quizzes": [],
            }), 401

        olympiads = []
        quizzes = []
        seen = set()
        try:
            items = list_olympiads() or []
        except Exception as e:
            log.warning("list_olympiads: %s", e)
            items = []

        for o in items:
            oid = str(o.get("id") or "")
            if not oid or oid in seen:
                continue
            if o.get("isActive") is False:
                continue
            window = _window_status(o)
            seen.add(oid)
            card = {
                "id": oid,
                "title": o.get("title") or "Бе ном",
                "description": o.get("description") or "",
                "type": (o.get("type") or "olympiad").lower(),
                "passScore": o.get("passScore") or 70,
                "questionCount": o.get("questionCount") or len(o.get("questions") or []),
                "isActive": o.get("isActive") is not False,
                "isOpen": window == "open",
                "windowStatus": window,
                "startTime": o.get("startTime"),
                "endTime": o.get("endTime"),
                "durationSec": o.get("durationSec"),
            }
            if card["type"] == "quiz":
                quizzes.append(card)
            else:
                olympiads.append(card)

        return jsonify({
            "ok": True,
            "student": _public_student(st),
            "olympiads": olympiads,
            "quizzes": quizzes,
        })

    def _bind(rule: str, ep: str, fn, methods: list[str]):
        bound = False
        for r in list(app.url_map.iter_rules()):
            if r.rule == rule:
                app.view_functions[r.endpoint] = fn
                bound = True
        if ep in app.view_functions:
            app.view_functions[ep] = fn
            bound = True
        if not bound:
            try:
                app.add_url_rule(rule, ep, fn, methods=methods)
            except AssertionError:
                for r in list(app.url_map.iter_rules()):
                    if r.rule == rule:
                        app.view_functions[r.endpoint] = fn

    _bind("/api/student/login", "student_portal_login", student_login, ["POST"])
    if "student_login" in app.view_functions:
        app.view_functions["student_login"] = student_login
    _bind("/api/student/olympiads", "student_portal_olympiads", student_olympiads, ["GET"])

    try:
        from db import student_access as sa

        def _open_access(olympiad_id, student_code):
            student_code = (student_code or "").strip()
            student = None
            try:
                from db.repo import find_student_by_code
                student = find_student_by_code(student_code) if student_code else None
            except Exception:
                pass
            if not student_code:
                return {"allowed": False, "reason": "student_id_required"}
            if student_code.startswith(("g:", "gmail:")) and not student:
                return {"allowed": False, "reason": "student_id_required"}
            if not student:
                return {"allowed": False, "reason": "student_not_found"}
            try:
                parts = sa.list_olympiad_participants(olympiad_id)
            except Exception:
                parts = []
            if parts:
                assigned = any(
                    str(p.get("id") or p.get("student_code") or "") == student_code
                    and p.get("status", "assigned") == "assigned"
                    for p in parts
                )
                if not assigned:
                    return {"allowed": False, "reason": "not_assigned"}
            return {"allowed": True, "reason": "open_or_assigned", "student": student}

        sa.student_has_olympiad_access = _open_access
        log.info("student_has_olympiad_access relaxed (empty list open)")
    except Exception as e:
        log.warning("could not patch student_access: %s", e)

    log.info("student portal routes installed")
    print("[boot] patch_student_portal: login + olympiads list")
