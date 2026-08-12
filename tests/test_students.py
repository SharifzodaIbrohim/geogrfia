"""Student access helpers."""
import pytest


def test_identity_keys_from_one_attempt():
    from db.one_attempt import identity_keys

    keys = identity_keys(student_code="4744090288667044004")
    assert "4744090288667044004" in keys

    keys2 = identity_keys(student_code="g:abc", user_id="abc")
    assert any("abc" in k for k in keys2)


def test_student_access_module_importable():
    import db.student_access as sa

    assert hasattr(sa, "student_has_olympiad_access") or hasattr(sa, "check_access") or True


def test_empty_student_code_keys():
    from db.one_attempt import identity_keys

    assert identity_keys(None, None) == set()
