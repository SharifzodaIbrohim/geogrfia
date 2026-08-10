"""Public /api/quizzes = standalone quizzes + olympiad rows with type=quiz only.
Never lists type=olympiad events.
"""
from __future__ import annotations


def install(app) -> None:
    from flask import jsonify

    def public_list_quizzes():
        from db import quiz_api
        from db.repo import list_olympiads

        safe = []
        seen = set()

        # 1) Real quiz table rows
        try:
            items = quiz_api.list_quizzes(include_draft=False)
        except Exception:
            items = []
        for q in items:
            if q.get("source") == "olympiad":
                continue
            qid = q.get("id")
            if not qid or qid in seen:
                continue
            seen.add(qid)
            safe.append({
                "id": qid,
                "title": q.get("title"),
                "description": q.get("description"),
                "passScore": q.get("passScore"),
                "timeLimitSec": q.get("timeLimitSec"),
                "accessMode": q.get("accessMode") or "public",
                "schoolName": q.get("schoolName"),
                "questionCount": q.get("questionCount") or 0,
                "source": "quiz",
            })

        # 2) Olympiad table rows with type=quiz (admin "Викторина") — show as quiz
        try:
            for o in list_olympiads():
                if (o.get("type") or "olympiad").lower() != "quiz":
                    continue
                if not o.get("isActive"):
                    continue
                oid = o.get("id")
                if not oid or oid in seen:
                    continue
                seen.add(oid)
                safe.append({
                    "id": oid,
                    "title": o.get("title"),
                    "description": o.get("description") or "",
                    "passScore": o.get("passScore") or 70,
                    "timeLimitSec": o.get("durationSec"),
                    "accessMode": "school",  # Student ID
                    "schoolName": None,
                    "questionCount": o.get("questionCount") or 0,
                    "source": "quiz",
                    "eventKind": "olympiad_quiz",
                })
        except Exception:
            pass

        return jsonify({"quizzes": safe})

    app.view_functions["public_list_quizzes"] = public_list_quizzes

    has_rule = False
    for r in list(app.url_map.iter_rules()):
        if r.rule == "/api/quizzes" and "GET" in (r.methods or set()):
            app.view_functions[r.endpoint] = public_list_quizzes
            has_rule = True
    if not has_rule:
        try:
            app.add_url_rule(
                "/api/quizzes",
                "public_list_quizzes",
                public_list_quizzes,
                methods=["GET"],
            )
        except AssertionError:
            app.view_functions["public_list_quizzes"] = public_list_quizzes

    for name, fn in list(app.view_functions.items()):
        if name == "public_list_quizzes" or getattr(fn, "__name__", "") == "public_list_quizzes":
            app.view_functions[name] = public_list_quizzes
