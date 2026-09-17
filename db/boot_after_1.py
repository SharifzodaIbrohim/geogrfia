try:
    from db.patch_student_portal import install as _isp
    _isp(app)
except Exception as e:
    print("[boot] patch_student_portal failed:", e)
try:
    from db.patch_admin_create_role import install as _iac
    _iac(app)
except Exception as e:
    print("[boot] patch_admin_create_role failed:", e)
try:
    from db.patch_admin_auth_bearer import install as _iab
    _iab(app)
except Exception as e:
    print("[boot] patch_admin_auth_bearer failed:", e)
try:
    from db.patch_names import install as _in
    _in(app)
except Exception as e:
    print("[boot] patch_names failed:", e)
try:
    from db.patch_monitor_durable import install as _imd
    _imd(app)
except Exception as e:
    print("[boot] patch_monitor_durable failed:", e)
try:
    from db.patch_score_text import install as _ist
    _ist(app)
    print("[boot] patch_score_text installed")
except Exception as e:
    print("[boot] patch_score_text failed:", e)
try:
    from db.patch_olympiad_builder import install as _iob
    _iob(app)
except Exception as e:
    print("[boot] patch_olympiad_builder failed:", e)
try:
    from db.patch_olympiad_questions_pg import install as _iqpg
    _iqpg(app)
    print("[boot] patch_olympiad_questions_pg installed")
except Exception as e:
    print("[boot] patch_olympiad_questions_pg failed:", e)
try:
    from db.patch_answers_durable import install as _iad
    _iad(app)
except Exception as e:
    print("[boot] patch_answers_durable failed:", e)
try:
    from db.patch_attempt_review import install as _iar
    _iar(app)
except Exception as e:
    print("[boot] patch_attempt_review failed:", e)
try:
    from db.patch_review_multitype import install as _irm
    _irm(app)
    print("[boot] patch_review_multitype installed")
except Exception as e:
    print("[boot] patch_review_multitype failed:", e)
try:
    from db.patch_results_score_fix import install as _irsf
    _irsf(app)
except Exception as e:
    print("[boot] patch_results_score_fix failed:", e)
try:
    from db.patch_clear_recent import install as _icr
    _icr(app)
except Exception as e:
    print("[boot] patch_clear_recent failed:", e)
try:
    from db.patch_admin_export import install as _iax
    _iax(app)
    print("[boot] patch_admin_export installed")
except Exception as e:
    print("[boot] patch_admin_export failed:", e)
try:
    from db.patch_ui_batch import install as _iub
    _iub(app)
    print("[boot] patch_ui_batch installed")
except Exception as e:
    print("[boot] patch_ui_batch failed:", e)
try:
    from db.bootstrap_admin import install_bootstrap
    install_bootstrap()
except Exception as e:
    print("[boot] bootstrap_admin failed:", e)
