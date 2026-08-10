"""
P0.8 — Super Admin protection.

Rules:
  - Only super_admin may create admins, change roles, disable/delete admins, read full audit.
  - Super Admin cannot delete/disable themselves.
  - The last remaining super_admin cannot be deleted or demoted.
  - Every role change is audit-logged.
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import text

from db.rbac import is_super_admin, normalize_role, VALID_ROLES, DEFAULT_NEW_ADMIN_ROLE
from db.repo import use_pg, _load_json, _save_json, ADMINS_FILE

log = logging.getLogger("geografia.admin_guards")


def count_super_admins() -> int:
    if use_pg():
        try:
            from db.connection import get_session
            with get_session() as s:
                n = s.execute(
                    text(
                        "SELECT COUNT(*) FROM admins "
                        "WHERE role = CAST('super_admin' AS admin_role) "
                        "AND (status = 'active' OR status IS NULL)"
                    )
                ).scalar()
                return int(n or 0)
        except Exception as e:
            log.warning("count_super_admins: %s", e)
            return 0
    n = 0
    for a in _load_json(ADMINS_FILE):
        if normalize_role(a.get("role")) == "super_admin":
            if (a.get("status") or "active") == "active":
                n += 1
    return n


def get_admin_by_id(admin_id: str) -> dict | None:
    if not admin_id:
        return None
    if use_pg():
        try:
            from db.connection import get_session
            with get_session() as s:
                r = s.execute(
                    text(
                        "SELECT id::text, login, name, role::text, status::text, created_by, created_at "
                        "FROM admins WHERE id::text = :id"
                    ),
                    {"id": str(admin_id)},
                ).mappings().first()
                if not r:
                    return None
                return {
                    "id": r["id"],
                    "login": r["login"],
                    "name": r["name"],
                    "role": normalize_role(r.get("role")),
                    "status": r.get("status") or "active",
                    "createdBy": r.get("created_by"),
                    "createdAt": r["created_at"].isoformat() if r.get("created_at") else None,
                }
        except Exception as e:
            log.warning("get_admin_by_id: %s", e)
            return None
    for a in _load_json(ADMINS_FILE):
        if str(a.get("id")) == str(admin_id):
            out = dict(a)
            out["role"] = normalize_role(out.get("role"))
            return out
    return None


def assert_can_manage_admins(actor: dict | None) -> None:
    """Only super_admin may create/delete/disable/role-change admins."""
    if not is_super_admin(actor):
        raise PermissionError("super_admin_required")


def assert_can_delete_admin(actor: dict | None, target_id: str) -> dict:
    """
    Returns target admin if delete is allowed.
    Raises PermissionError / ValueError with stable reason codes.
    """
    assert_can_manage_admins(actor)
    target = get_admin_by_id(target_id)
    if not target:
        raise ValueError("not_found")

    # Self-delete forbidden
    if actor and str(actor.get("id")) == str(target_id):
        raise PermissionError("cannot_self_delete")
    if actor and (actor.get("login") or "").lower() == (target.get("login") or "").lower():
        raise PermissionError("cannot_self_delete")

    # Last super_admin cannot be deleted
    if normalize_role(target.get("role")) == "super_admin":
        if count_super_admins() <= 1:
            raise PermissionError("cannot_delete_last_super_admin")

    return target


def assert_can_change_role(
    actor: dict | None,
    target_id: str,
    new_role: str | None,
) -> tuple[dict, str]:
    """
    Returns (target, normalized_new_role) if allowed.
    """
    assert_can_manage_admins(actor)
    target = get_admin_by_id(target_id)
    if not target:
        raise ValueError("not_found")

    role = normalize_role(new_role)
    if not role:
        raise ValueError("invalid_role")

    old_role = normalize_role(target.get("role"))

    # Demoting the last super_admin forbidden
    if old_role == "super_admin" and role != "super_admin":
        if count_super_admins() <= 1:
            raise PermissionError("cannot_demote_last_super_admin")

    # Self-demote from super_admin when you are the last one — same rule
    if actor and str(actor.get("id")) == str(target_id):
        if old_role == "super_admin" and role != "super_admin":
            if count_super_admins() <= 1:
                raise PermissionError("cannot_demote_last_super_admin")

    return target, role


def assert_can_disable_admin(actor: dict | None, target_id: str) -> dict:
    """Disable is treated like soft-delete for protection rules."""
    return assert_can_delete_admin(actor, target_id)


def safe_create_role(requested: str | None, *, actor_is_super: bool) -> str:
    """
    Role for newly created admin.
    - Invalid → DEFAULT_NEW_ADMIN_ROLE
    - super_admin only if actor is super_admin
    """
    role = normalize_role(requested) or DEFAULT_NEW_ADMIN_ROLE
    if role == "super_admin" and not actor_is_super:
        return DEFAULT_NEW_ADMIN_ROLE
    return role


def audit_role_change(
    *,
    actor: dict | None,
    target: dict,
    old_role: str | None,
    new_role: str,
    ip: str | None = None,
) -> None:
    try:
        from db import audit
        audit.log_action(
            action="admin.role_change",
            admin=actor,
            target_type="admin",
            target_id=target.get("id"),
            meta={
                "targetLogin": target.get("login"),
                "oldRole": old_role,
                "newRole": new_role,
            },
            ip=ip,
        )
    except Exception as e:
        log.warning("audit_role_change failed: %s", e)


def audit_admin_delete(
    *,
    actor: dict | None,
    target: dict,
    ip: str | None = None,
) -> None:
    try:
        from db import audit
        audit.log_action(
            action="admin.delete",
            admin=actor,
            target_type="admin",
            target_id=target.get("id"),
            meta={"targetLogin": target.get("login"), "targetRole": target.get("role")},
            ip=ip,
        )
    except Exception as e:
        log.warning("audit_admin_delete failed: %s", e)
