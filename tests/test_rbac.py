"""P0.7 RBAC — unknown role never escalates."""
from db.rbac import (
    admin_can,
    is_super_admin,
    is_valid_role,
    normalize_role,
    role_permissions,
)


def test_normalize_unknown_is_none():
    assert normalize_role("hacker") is None
    assert normalize_role("") is None
    assert normalize_role(None) is None
    assert normalize_role("SUPER_ADMIN_X") is None
    assert normalize_role("invalid") is None


def test_normalize_never_returns_super_for_garbage():
    for junk in ("admin", "root", "Administrator", "*", "true", "1"):
        assert normalize_role(junk) is not None or normalize_role(junk) is None
        assert normalize_role(junk) != "super_admin" or junk.lower() == "super_admin"
        if junk.lower() != "super_admin":
            assert normalize_role(junk) is None or normalize_role(junk) in (
                "user_admin",
                "quiz_admin",
                "olympiad_admin",
                "monitor",
                "content_admin",
            )


def test_normalize_valid_roles():
    assert normalize_role("super_admin") == "super_admin"
    assert normalize_role("Olympiad_Admin") == "olympiad_admin"
    assert normalize_role("MONITOR") == "monitor"


def test_unknown_role_zero_permissions():
    assert role_permissions(None) == set()
    assert role_permissions("nope") == set()
    assert admin_can({"role": "garbage"}, "students.read") is False
    assert admin_can(None, "students.read") is False


def test_super_admin_can_everything(super_admin):
    assert is_super_admin(super_admin)
    assert admin_can(super_admin, "admins.write")
    assert admin_can(super_admin, "olympiads.write")
    assert admin_can(super_admin, "content.write")


def test_olympiad_admin_scope(olympiad_admin):
    assert admin_can(olympiad_admin, "olympiads.write")
    assert admin_can(olympiad_admin, "students.read")
    assert not admin_can(olympiad_admin, "admins.write")
    assert not admin_can(olympiad_admin, "content.write")


def test_monitor_read_only(monitor_admin):
    assert admin_can(monitor_admin, "monitor.read")
    assert admin_can(monitor_admin, "results.read")
    assert not admin_can(monitor_admin, "olympiads.write")
    assert not admin_can(monitor_admin, "students.write")


def test_is_valid_role():
    assert is_valid_role("quiz_admin")
    assert not is_valid_role("boss")
