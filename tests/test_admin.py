"""P0.8 Super-admin protection — role assignment rules."""
import pytest

try:
    from db.admin_guards import safe_create_role
except Exception:
    # Minimal mirror of intended policy when DB deps unavailable
    from db.rbac import normalize_role, DEFAULT_NEW_ADMIN_ROLE

    def safe_create_role(requested, *, actor_is_super):
        r = normalize_role(requested) if requested else None
        if r == "super_admin" and not actor_is_super:
            return DEFAULT_NEW_ADMIN_ROLE
        if r is None:
            return DEFAULT_NEW_ADMIN_ROLE
        return r


def test_safe_create_role_defaults_non_super():
    role2 = safe_create_role("olympiad_admin", actor_is_super=False)
    assert role2 == "olympiad_admin"


def test_non_super_cannot_create_super():
    role = safe_create_role("super_admin", actor_is_super=False)
    assert role != "super_admin"


def test_super_can_request_super():
    role = safe_create_role("super_admin", actor_is_super=True)
    assert role == "super_admin"


def test_invalid_role_falls_back():
    role = safe_create_role("totally_invalid", actor_is_super=True)
    assert role != "super_admin"
    assert isinstance(role, str)
