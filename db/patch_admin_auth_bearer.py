"""Accept Authorization: Bearer for admin APIs (in addition to X-Admin-Token).

Root cause: server_core require_admin only reads X-Admin-Token.
Some clients / intermediate code send Bearer → "Дастрасӣ рад шуд" after login.
"""
from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger("geografia.patch_admin_auth_bearer")


def install(app=None) -> None:
    try:
        from flask import request, g
    except Exception as e:
        log.warning("flask missing: %s", e)
        return

    def _extract_admin_token() -> str:
        for name in (
            request.cookies.get("__Host-geografia_admin") or "",
            request.cookies.get("geografia_admin") or "",
            request.cookies.get("__Host-geografia_session") or "",
        ):
            if name and name.strip():
                return name.strip()
        for h in ("X-Admin-Token", "X-Admin-Auth"):
            v = (request.headers.get(h) or "").strip()
            if v:
                return v
        auth = (request.headers.get("Authorization") or "").strip()
        if auth.lower().startswith("bearer "):
            return auth[7:].strip()
        if auth and not auth.lower().startswith("basic "):
            return auth
        return ""

    def _admin_from_any_token(tok: str) -> dict | None:
        if not tok:
            return None
        try:
            from db.auth_tokens import admin_from_token
            admin = admin_from_token(tok)
            if admin:
                return admin
        except Exception as e:
            log.debug("admin_from_token: %s", e)
        try:
            import sys
            for modname in ("server_core", "server_12d7430", "__main__", "server"):
                mod = sys.modules.get(modname)
                if not mod:
                    continue
                tokens = getattr(mod, "ADMIN_TOKENS", None)
                if isinstance(tokens, dict) and tok in tokens:
                    return dict(tokens[tok])
        except Exception:
            pass
        return None

    import sys
    patched = 0
    for modname in list(sys.modules.keys()) + ["__main__"]:
        mod = sys.modules.get(modname)
        if not mod or not hasattr(mod, "require_admin"):
            continue
        try:
            orig = getattr(mod, "require_admin")
            if getattr(orig, "_bearer_patched", False):
                continue

            def _wrap(orig_fn):
                def require_admin(*args, **kwargs):
                    tok = _extract_admin_token()
                    admin = _admin_from_any_token(tok)
                    if admin:
                        try:
                            g.session_admin = admin
                            g.admin = admin
                        except Exception:
                            pass
                        return admin
                    return orig_fn(*args, **kwargs)
                require_admin._bearer_patched = True  # type: ignore
                return require_admin

            setattr(mod, "require_admin", _wrap(orig))
            patched += 1
        except Exception as e:
            log.debug("skip %s: %s", modname, e)

    if app is not None:
        try:
            app.extensions = getattr(app, "extensions", {}) or {}
            app.extensions["admin_bearer_patch"] = True
        except Exception:
            pass

    print(f"[boot] patch_admin_auth_bearer: patched require_admin in {patched} module(s)")
    log.info("patch_admin_auth_bearer installed (patched=%s)", patched)
