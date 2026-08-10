"""
Phase 4–5 — Super Admin + RBAC
Roles match schema admin_role enum.
Unknown role = zero privileges (never escalate to super_admin).
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


def normalize_role(role: str | None) -> str | None:
    """Unknown role = None (zero privileges). Never escalate to super_admin."""
    if not role:
        return None
    r = str(role).strip().lower()
    return r if r in ROLE_PERMISSIONS else None


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
        return False
    if ROLE_PERMISSIONS.get(role) == "*":
        return True
    return permission in role_permissions(role)


def admin_can_any(admin: dict | None, permissions: Iterable[str]) -> bool:
    return any(admin_can(admin, p) for p in permissions)


def deny_message(permission: str) -> str:
    return f"Ҳуқуқи кофӣ нест ({permission})."
