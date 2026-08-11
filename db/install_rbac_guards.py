"""
P0.7 / P0.8 / P1.1 boot install:
  - Replace list/find admin so missing role ≠ super_admin
  - Guarded admin delete + role change with audit
  - Resolve admin from HttpOnly session cookie
"""
from __future__ import annotations

import logging

from flask import jsonify, request
from sqlalchemy import text

log = logging.getLogger("geografia.rbac_guards")


def install(app) -> None:
    _patch_repo_admin_lookups()
    _patch_admin_views(app)
    log.info("RBAC guards installed")


def _patch_repo_admin_lookups() -> None:
    try:
        from db import repo
        from db.connection import get_session
        from db.rbac import normalize_role

        def list_admins():
            if repo.use_pg():
                with get_session() as s:
                    rows = s.execute(text(
                        "SELECT id::text, login, name, role::text, created_by, created_at "
                        "FROM admins WHERE status = 'active' OR status IS NULL "
                        "ORDER BY created_at"
                    )).mappings().all()
                    return [{
                        "id": r["id"],
                        "login": r["login"],
                        "name": r["name"],
                        "role": normalize_role(r.get("role")),
                        "createdBy": r.get("created_by"),
                        "createdAt": r["created_at"].isoformat() if r.get("created_at") else None,
                    } for r in rows]
            out = []
            for a in repo._load_json(repo.ADMINS_FILE):
                out.append({
                    "id": a.get("id"),
                    "login": a.get("login"),
                    "name": a.get("name"),
                    "role": normalize_role(a.get("role")),
                    "createdBy": a.get("createdBy"),
                    "createdAt": a.get("createdAt"),
                })
            return out

        def find_admin_by_login(login: str):
            login_l = (login or "").strip().lower()
            if not login_l:
                return None
            if repo.use_pg():
                try:
                    with get_session() as s:
                        r = s.execute(text(
                            "SELECT id::text, login, name, role::text, salt, password_hash, "
                            "created_by, created_at, status::text "
                            "FROM admins WHERE lower(login) = :login LIMIT 1"
                        ), {"login": login_l}).mappings().first()
                        if not r:
                            return None
                        if r.get("status") and str(r["status"]) not in ("active", "Active"):
                            return None
                        return {
                            "id": r["id"],
                            "login": r["login"],
                            "name": r["name"],
                            "role": normalize_role(r.get("role")),
                            "salt": r.get("salt") or "",
                            "passwordHash": r.get("password_hash") or "",
                            "createdBy": r.get("created_by"),
                            "createdAt": r["created_at"].isoformat() if r.get("created_at") else None,
                        }
                except Exception as e:
                    log.error("find_admin_by_login: %s", e)
                    return None
            for a in repo._load_json(repo.ADMINS_FILE):
                if (a.get("login") or "").lower() == login_l:
                    return {
                        "id": a.get("id"),
                        "login": a.get("login"),
                        "name": a.get("name"),
                        "role": normalize_role(a.get("role")),
                        "salt": a.get("salt") or "",
                        "passwordHash": a.get("passwordHash") or a.get("password_hash") or "",
                        "createdBy": a.get("createdBy"),
                        "createdAt": a.get("createdAt"),
                    }
            return None

        repo.list_admins = list_admins
        repo.find_admin_by_login = find_admin_by_login
    except Exception as e:
        log.warning("repo admin lookup patch: %s", e)


def _patch_admin_views(app) -> None:
    from db.rbac import normalize_role
    from db.admin_role import (
        enrich_admin,
        update_admin_role,
        delete_admin_safe,
    )

    def _actor():
        try:
            from db import session_cookies as sc
            admin = enrich_admin(sc.current_admin(request))
            if admin:
                return admin
        except Exception:
            pass
        try:
            from db.auth_tokens import admin_from_token
            token = request.headers.get("X-Admin-Token") or ""
            admin = enrich_admin(admin_from_token(token))
            if admin:
                return admin
        except Exception:
            pass
        try:
            import sys
            token = request.headers.get("X-Admin-Token") or ""
            for modname in ("server_12d7430", "server_core_remote", "__main__"):
                mod = sys.modules.get(modname)
                if not mod:
                    continue
                tokens = getattr(mod, "ADMIN_TOKENS", None)
                if tokens and token in tokens:
                    return enrich_admin(dict(tokens[token]))
        except Exception:
            pass
        return None

    def admin_delete_admin(admin_id: str):
        actor = _actor()
        if not actor:
            return jsonify({"error": "Дастрасӣ рад шуд."}), 401
        try:
            ok = delete_admin_safe(
                admin_id,
                actor=actor,
                ip=request.headers.get("X-Forwarded-For", request.remote_addr),
            )
            if not ok:
                return jsonify({"error": "Ёфт нашуд."}), 404
            return jsonify({"ok": True})
        except PermissionError as e:
            code = str(e)
            msgs = {
                "super_admin_required": "Танҳо Super Admin.",
                "cannot_self_delete": "Шумо худро нест карда наметавонед.",
                "cannot_delete_last_super_admin": "Охирин Super Admin-ро нест кардан мумкин нест.",
            }
            return jsonify({"error": msgs.get(code, code), "reason": code}), 403
        except ValueError as e:
            if str(e) == "not_found":
                return jsonify({"error": "Ёфт нашуд."}), 404
            return jsonify({"error": str(e)}), 400

    def admin_patch_role(admin_id: str):
        actor = _actor()
        if not actor:
            return jsonify({"error": "Дастрасӣ рад шуд."}), 401
        payload = request.get_json(silent=True) or {}
        new_role = payload.get("role")
        try:
            ok = update_admin_role(
                admin_id,
                new_role,
                actor=actor,
                ip=request.headers.get("X-Forwarded-For", request.remote_addr),
            )
            if not ok:
                return jsonify({"error": "Ёфт нашуд."}), 404
            return jsonify({"ok": True, "role": normalize_role(new_role)})
        except PermissionError as e:
            code = str(e)
            msgs = {
                "super_admin_required": "Танҳо Super Admin.",
                "cannot_demote_last_super_admin": "Охирин Super Admin-ро паст кардан мумкин нест.",
            }
            return jsonify({"error": msgs.get(code, code), "reason": code}), 403
        except ValueError as e:
            code = str(e)
            msgs = {
                "invalid_role": "Нақши нодуруст.",
                "not_found": "Ёфт нашуд.",
            }
            status = 404 if code == "not_found" else 400
            return jsonify({"error": msgs.get(code, code), "reason": code}), status

    for name, fn, rule, methods in [
        ("admin_delete_admin", admin_delete_admin, "/api/admin/admins/<admin_id>", ["DELETE"]),
        ("admin_patch_role", admin_patch_role, "/api/admin/admins/<admin_id>/role", ["PATCH"]),
    ]:
        if name in app.view_functions:
            app.view_functions[name] = fn
        else:
            try:
                app.add_url_rule(rule, name, fn, methods=methods)
            except AssertionError:
                app.view_functions[name] = fn
