"""Last-write wins: public /api/quizzes lists only standalone quizzes."""
from __future__ import annotations


def install(app) -> None:
    from flask import jsonify

    def public_list_quizzes():
        from db import quiz_api

        items = quiz_api.list_quizzes(include_draft=False)
        safe = []
        for q in items:
            safe.append(
                {
                    "id": q["id"],
                    "title": q.get("title"),
                    "description": q.get("description"),
                    "passScore": q.get("passScore"),
                    "timeLimitSec": q.get("timeLimitSec"),
                    "accessMode": q.get("accessMode") or "public",
                    "schoolName": q.get("schoolName"),
                    "questionCount": q.get("questionCount") or 0,
                    "source": "quiz",
                }
            )
        return jsonify({"quizzes": safe})

    # Override whatever was registered earlier (including server.py patches)
    app.view_functions["public_list_quizzes"] = public_list_quizzes
    # Also bind common endpoint names if Flask registered differently
    for name, fn in list(app.view_functions.items()):
        if name in ("public_list_quizzes",) or getattr(fn, "__name__", "") == "public_list_quizzes":
            app.view_functions[name] = public_list_quizzes
