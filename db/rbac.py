"""
Phase 4–5 / P0.7 — Super Admin + RBAC

SECURITY RULE:
  Unknown role = zero privileges.
  Never escalate unknown → super_admin.
"""
from __future__ import annotations

from typing import Iterable

PERMISSIONS = {
    "admins.read",
    "admins.write",
    "students.read",
    "students.write",
    "schools.read",
    "schools.write",
    "olympiads.read",
    "olympiads.write",
    "participants.write",
    "results.read",
    "monitor.read",
    "quizzes.read",
    "quizzes.write",
    "content.read",
    "content.write",
}

ROLE_PERMISSIONS: dict[str, set[str] | str] = {
    "super_admin": "*",
    "user_admin": {
        "admins.read",
        "students.read",
        "students.write",
        "schools.read",
        "schools.write",
    },
    "quiz_admin": {
        "quizzes.read",
        "quizzes.write",
        "results.read",
    },
    "olympiad_admin": {
        "olympiads.read",
        "olympiads.write",
        "participants.write",
        "results.read",
        "monitor.read",
        "students.read",
    },
    "monitor": {
        "monitor.read",
        "results.read",
        "olympiads.read",
        "students.read",
    },
    "content_admin": {
        "content.read",
        "content.write",
    },
}

VALID_ROLES = tuple(ROLE_PERMISSIONS.keys())
DEFAULT_NEW_ADMIN_ROLE = "olympiad_admin"  # never super_admin by default


def normalize_role(role: str | None) -> str | None:
    """
    Map role string to a known role key, or None.

    P0.7: invalid / empty / garbage → None (deny all).
    NEVER returns super_admin for unknown input.
    """
    if role is None:
        return None
    r = str(role).strip().lower()
    if not r or r in ("none", "null", "undefined", "invalid", "unknown"):
        return None
    if r not in ROLE_PERMISSIONS:
        return None
    return r


def is_valid_role(role: str | None) -> bool:
    return normalize_role(role) is not None


def is_super_admin(admin: dict | None) -> bool:
    if not admin:
        return False
    return normalize_role(admin.get("role")) == "super_admin"


def role_permissions(role: str | None) -> set[str]:
    r = normalize_role(role)
    if not r:
        return set()
    perms = ROLE_PERMISSIONS[r]
    if perms == "*":
        return set(PERMISSIONS)
    return set(perms)


def admin_can(admin: dict | None, permission: str) -> bool:
    if not admin:
        return False
    role = normalize_role(admin.get("role"))
    if not role:
        return False  # unknown / missing role → zero privileges
    if ROLE_PERMISSIONS.get(role) == "*":
        return True
    return permission in role_permissions(role)


def admin_can_any(admin: dict | None, permissions: Iterable[str]) -> bool:
    return any(admin_can(admin, p) for p in permissions)


def deny_message(permission: str) -> str:
    return f"Ҳуқуқи кофӣ нест ({permission})."


def require_known_role(role: str | None) -> str:
    """Raise ValueError if role is not a known RBAC role."""
    r = normalize_role(role)
    if not r:
        raise ValueError("invalid_role")
    return r
