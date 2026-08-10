"""Last-write wins: public /api/quizzes lists only standalone quizzes.

Must both:
  1) set view_functions['public_list_quizzes']
  2) ensure a URL rule for /api/quizzes exists

If only (1) runs before register_quiz_routes, _safe_get skips add_url_rule → 404.
"""
from __future__ import annotations


def install(app) -> None:
    from flask import jsonify

    def public_list_quizzes():
        from db import quiz_api

        items = quiz_api.list_quizzes(include_draft=False)
        safe = []
        for q in items:
            if q.get("source") == "olympiad":
                continue
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

    # Always bind the view function name used by the rest of the app
    app.view_functions["public_list_quizzes"] = public_list_quizzes

    # Ensure a real URL rule exists (view_functions alone is not enough)
    has_rule = False
    for r in list(app.url_map.iter_rules()):
        if r.rule == "/api/quizzes" and "GET" in (r.methods or set()):
            # Point existing rule's endpoint at our function
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
            # Endpoint name collision — override whatever is mapped
            app.view_functions["public_list_quizzes"] = public_list_quizzes

    # Also fix any endpoint whose function name is public_list_quizzes
    for name, fn in list(app.view_functions.items()):
        if name == "public_list_quizzes" or getattr(fn, "__name__", "") == "public_list_quizzes":
            app.view_functions[name] = public_list_quizzes
