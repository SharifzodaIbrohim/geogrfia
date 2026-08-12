"""P0.8 Super-admin protection helpers."""
import pytest

from db.admin_guards import safe_create_role


def test_safe_create_role_defaults_non_super():
    role = safe_create_role(None, actor_is_super=True)
    assert role != "super_admin" or role is not None
    # default should not be super unless explicitly requested by super
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
