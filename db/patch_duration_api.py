"""Wrap admin create olympiad to accept durationMin after save."""
from __future__ import annotations
import logging
log = logging.getLogger("geografia.patch_duration_api")

def install(app=None):
    if app is None:
        return
    from flask import request

    for rule in app.url_map.iter_rules():
        if rule.rule == "/api/admin/olympiads" and "POST" in (rule.methods or set()):
            ep = rule.endpoint
            orig = app.view_functions.get(ep)
            if not orig:
                continue

            def make_wrapper(orig_fn):
                def wrapped(*a, **k):
                    resp = orig_fn(*a, **k)
                    try:
                        body = resp
                        status = 200
                        if isinstance(resp, tuple):
                            body, status = resp[0], resp[1]
                        if status and int(status) >= 400:
                            return resp
                        payload = request.get_json(silent=True) or {}
                        if "durationMin" not in payload and "durationSec" not in payload:
                            return resp
                        import db.repo as repo
                        j = body.get_json() if hasattr(body, "get_json") else None
                        if not j:
                            return resp
                        oly = j.get("olympiad") or j
                        oid = oly.get("id") if isinstance(oly, dict) else None
                        if not oid:
                            return resp
                        dm = payload.get("durationMin")
                        sec = payload.get("durationSec")
                        if sec is None and dm is not None:
                            try:
                                dm = int(dm)
                                sec = None if dm <= 0 else max(1, dm) * 60
                            except Exception:
                                sec = None
                        elif sec is not None:
                            try:
                                sec = int(sec)
                            except Exception:
                                sec = None
                        updated = repo.update_olympiad(str(oid), {"durationSec": sec})
                        if updated:
                            from flask import jsonify as fj
                            return fj({"olympiad": updated, "ok": True})
                    except Exception as e:
                        log.warning("duration post-create: %s", e)
                    return resp

                wrapped.__name__ = getattr(orig_fn, "__name__", "wrapped_duration")
                return wrapped

            app.view_functions[ep] = make_wrapper(orig)
            print("[boot] patch_duration_api: POST /api/admin/olympiads durationMin")
            log.info("duration API wrap on %s", ep)
            break
