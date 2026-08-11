"""P0.9: attach non-secret credentials status onto /api/health."""
from __future__ import annotations

import logging

log = logging.getLogger("geografia.secrets_health")


def install(app) -> None:
    from flask import jsonify

    orig = app.view_functions.get("api_health")

    def api_health():
        body = {}
        status = 200
        if orig:
            try:
                resp = orig()
                if hasattr(resp, "get_json"):
                    body = resp.get_json() or {}
                    status = getattr(resp, "status_code", 200) or 200
                elif isinstance(resp, tuple):
                    body, status = resp[0], resp[1]
                    if hasattr(body, "get_json"):
                        body = body.get_json() or {}
                elif isinstance(resp, dict):
                    body = resp
            except Exception as e:
                body = {"ok": False, "error": str(e)[:120]}
                status = 500
        else:
            body = {"ok": True, "app": "geografia"}

        if not isinstance(body, dict):
            body = {"ok": True, "raw": str(body)[:80]}

        try:
            from db.secrets import secrets_public_status
            body["secrets"] = secrets_public_status()
        except Exception as e:
            body["secrets"] = {"error": str(e)[:80]}

        return jsonify(body), status

    app.view_functions["api_health"] = api_health
    # ensure rule exists
    has = False
    for r in list(app.url_map.iter_rules()):
        if r.rule == "/api/health" and "GET" in (r.methods or set()):
            app.view_functions[r.endpoint] = api_health
            has = True
    if not has:
        try:
            app.add_url_rule("/api/health", "api_health", api_health, methods=["GET"])
        except AssertionError:
            app.view_functions["api_health"] = api_health

    log.info("secrets health installed")
