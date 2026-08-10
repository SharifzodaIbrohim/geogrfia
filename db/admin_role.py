"""
Admin role helpers + P0.7/P0.8 safe create/update/delete.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import text

from db.connection import get_session
from db.rbac import (
    VALID_ROLES,
    normalize_role,
    is_super_admin,
    DEFAULT_NEW_ADMIN_ROLE,
)
from db.repo import use_pg, _load_json, _save_json, ADMINS_FILE, _utc_now
from db import admin_guards

log = logging.getLogger("geografia.admin_role")


def fetch_role_by_login(login: str) -> str | None:
    if not use_pg():
        return None
    with get_session() as s:
        r = s.execute(
            text("SELECT role::text FROM admins WHERE login = :l"),
            {"l": login},
        ).scalar()
        return str(r) if r else None


def fetch_role_by_id(admin_id: str) -> str | None:
    if not use_pg():
        return None
    with get_session() as s:
        r = s.execute(
            text("SELECT role::text FROM admins WHERE id::text = :id"),
            {"id": admin_id},
        ).scalar()
        return str(r) if r else None


def enrich_admin(admin: dict | None) -> dict | None:
    """Attach normalized role. Unknown → None (zero privileges)."""
    if not admin:
        return None
    if admin.get("role") is not None and str(admin.get("role")).strip() != "":
        admin["role"] = normalize_role(admin["role"])
        return admin
    role = None
    if admin.get("login"):
        role = fetch_role_by_login(admin["login"])
    if not role and admin.get("id"):
        role = fetch_role_by_id(str(admin["id"]))
    admin["role"] = normalize_role(role)
    return admin


def create_admin_with_role(
    login: str,
    name: str,
    salt: str,
    password_hash: str,
    created_by: str,
    role: str = DEFAULT_NEW_ADMIN_ROLE,
    *,
    actor: dict | None = None,
) -> dict:
    """
    Create admin. Default role is olympiad_admin, never super_admin by accident.
    Only a super_admin actor may assign super_admin.
    """
    role = admin_guards.safe_create_role(
        role, actor_is_super=is_super_admin(actor)
    )
    aid = str(uuid.uuid4())
    created = _utc_now()
    if use_pg():
        with get_session() as s:
            s.execute(
                text(
                    "INSERT INTO admins (id, login, name, salt, password_hash, role, status, created_by) "
                    "VALUES (:id, :login, :name, :salt, :ph, CAST(:role AS admin_role), 'active', :cb)"
                ),
                {
                    "id": aid,
                    "login": login,
                    "name": name,
                    "salt": salt,
                    "ph": password_hash,
                    "role": role,
                    "cb": created_by,
                },
            )
        return {
            "id": aid,
            "login": login,
            "name": name,
            "role": role,
            "createdBy": created_by,
            "createdAt": created,
        }
    admins = _load_json(ADMINS_FILE)
    row = {
        "id": aid,
        "login": login,
        "name": name,
        "salt": salt,
        "passwordHash": password_hash,
        "role": role,
        "status": "active",
        "createdBy": created_by,
        "createdAt": created,
    }
    admins.append(row)
    _save_json(ADMINS_FILE, admins)
    return {k: row[k] for k in ("id", "login", "name", "role", "createdBy", "createdAt")}


def update_admin_role(
    admin_id: str,
    role: str,
    *,
    actor: dict | None = None,
    ip: str | None = None,
) -> bool:
    """
    Change role with P0.8 guards + audit.
    """
    target, new_role = admin_guards.assert_can_change_role(actor, admin_id, role)
    old_role = normalize_role(target.get("role"))

    if use_pg():
        with get_session() as s:
            res = s.execute(
                text(
                    "UPDATE admins SET role = CAST(:role AS admin_role) WHERE id::text = :id"
                ),
                {"role": new_role, "id": admin_id},
            )
            ok = res.rowcount > 0
    else:
        admins = _load_json(ADMINS_FILE)
        ok = False
        for a in admins:
            if str(a.get("id")) == str(admin_id):
                a["role"] = new_role
                ok = True
                break
        if ok:
            _save_json(ADMINS_FILE, admins)

    if ok:
        admin_guards.audit_role_change(
            actor=actor,
            target=target,
            old_role=old_role,
            new_role=new_role,
            ip=ip,
        )
    return ok


def delete_admin_safe(
    admin_id: str,
    *,
    actor: dict | None = None,
    ip: str | None = None,
) -> bool:
    """Hard-delete with P0.8 guards + audit."""
    target = admin_guards.assert_can_delete_admin(actor, admin_id)

    if use_pg():
        with get_session() as s:
            res = s.execute(
                text("DELETE FROM admins WHERE id::text = :id"),
                {"id": str(admin_id)},
            )
            ok = res.rowcount > 0
    else:
        admins = _load_json(ADMINS_FILE)
        new = [a for a in admins if str(a.get("id")) != str(admin_id)]
        ok = len(new) < len(admins)
        if ok:
            _save_json(ADMINS_FILE, new)

    if ok:
        admin_guards.audit_admin_delete(actor=actor, target=target, ip=ip)
    return ok


def disable_admin_safe(
    admin_id: str,
    *,
    actor: dict | None = None,
    ip: str | None = None,
) -> bool:
    target = admin_guards.assert_can_disable_admin(actor, admin_id)
    if use_pg():
        with get_session() as s:
            res = s.execute(
                text(
                    "UPDATE admins SET status = CAST('disabled' AS user_status) "
                    "WHERE id::text = :id"
                ),
                {"id": str(admin_id)},
            )
            ok = res.rowcount > 0
    else:
        admins = _load_json(ADMINS_FILE)
        ok = False
        for a in admins:
            if str(a.get("id")) == str(admin_id):
                a["status"] = "disabled"
                ok = True
                break
        if ok:
            _save_json(ADMINS_FILE, admins)
    if ok:
        try:
            from db import audit
            audit.log_action(
                action="admin.disable",
                admin=actor,
                target_type="admin",
                target_id=target.get("id"),
                meta={"targetLogin": target.get("login")},
                ip=ip,
            )
        except Exception:
            pass
    return ok


def list_admins_with_roles() -> list[dict]:
    from db import repo

    items = repo.list_admins()
    out = []
    for a in items:
        out.append(enrich_admin(dict(a)))
    return out
