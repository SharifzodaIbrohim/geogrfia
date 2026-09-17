"""Post-core boot: PUBLIC_PATHS + patches. Called via exec from server.py."""
_EXTRA_PUBLIC = {
    "index.html", "admin.html", "student.html", "profile.html", "quiz.html",
    "courses.html", "leaderboard.html", "countries.html", "css.css",
    "css/admin.css", "css/student.css", "css/quiz.css", "css/platform.css", "css/profile.css",
    "js.js", "js/i18n.js", "js/platform-home.js", "js/quiz-platform.js", "js/profile.js",
    "js/admin.js", "js/admin-session.js", "js/admin-fixes.js", "js/admin-gmail.js",
    "js/admin-content.js", "js/admin-leaderboard.js", "js/admin-olympiad.js",
    "js/admin-matching-simple.js",
    "js/admin-students-reg.js", "js/admin-davotnoma-print.js", "js/admin-rbac-ui.js",
    "js/admin-audit.js", "js/admin-export.js", "js/admin-results-review.js",
    "js/admin-results-click-fix.js", "js/student.js", "js/student-confirm.js",
    "favicon.svg", "favicon.png", "robots.txt", "sitemap.xml", "og-default.png",
}
for _i in range(24):
    _EXTRA_PUBLIC.add(f"_asr_x{_i}.txt")
# Davotnoma logos (Cyrillic filenames in repo root)
_EXTRA_PUBLIC.add("Аз_тарафи_чап.jpg")
_EXTRA_PUBLIC.add("Аз_тарафи_рост.jpg")
_EXTRA_PUBLIC.add("logo-left.jpg")
_EXTRA_PUBLIC.add("logo-right.jpg")
for _i in range(4):
    _EXTRA_PUBLIC.add(f"_st_b64_{_i}.txt")
    _EXTRA_PUBLIC.add(f"_st_p{_i}.txt")
for _i in range(10):
    _EXTRA_PUBLIC.add(f"js/_sh{_i}.txt")
    _EXTRA_PUBLIC.add(f"_sh{_i}.txt")
for _i in range(10):
    _EXTRA_PUBLIC.add(f"js/_i18{_i}.txt")
    _EXTRA_PUBLIC.add(f"_i18{_i}.txt")
for _i in range(9):
    _EXTRA_PUBLIC.add(f"js/_aj{_i}.txt")
    _EXTRA_PUBLIC.add(f"_aj{_i}.txt")
try:
    if isinstance(globals().get("PUBLIC_PATHS"), set):
        PUBLIC_PATHS |= _EXTRA_PUBLIC
    elif isinstance(globals().get("PUBLIC_PATHS"), (list, tuple)):
        PUBLIC_PATHS = list(PUBLIC_PATHS) + sorted(_EXTRA_PUBLIC)
except Exception:
    pass

# --- safety: google login never 500 ---
try:
    from flask import jsonify, request

    def _google_login_safe():
        try:
            from db.google_auth import google_login_handler
            return google_login_handler()
        except Exception as e:
            return jsonify({"error": "Google login unavailable", "detail": str(e)[:200]}), 503

    bound = 0
    for rule in list(app.url_map.iter_rules()):
        if "google" in str(rule.rule) and "login" in str(rule.rule):
            app.view_functions[rule.endpoint] = _google_login_safe
            bound += 1
    if "google_login" in app.view_functions:
        app.view_functions["google_login"] = _google_login_safe
        bound += 1
    print(f"[boot] safety-net: google_login bound={bound}")
except Exception as e:
    print("[boot] safety-net failed:", e)

