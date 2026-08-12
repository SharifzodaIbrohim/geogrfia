"""
Test Matrix — Admin RBAC
  quiz_admin → quiz only
  monitor → monitoring only
  content_admin → content only
  random role → DENY
"""
from __future__ import annotations

from db.rbac import admin_can, normalize_role, role_permissions


def test_quiz_admin_quiz_only():
    admin = {"role": "quiz_admin"}
    assert admin_can(admin, "quizzes.read")
    assert admin_can(admin, "quizzes.write")
    assert admin_can(admin, "results.read")
    assert not admin_can(admin, "olympiads.write")
    assert not admin_can(admin, "admins.write")
    assert not admin_can(admin, "content.write")
    assert not admin_can(admin, "students.write")


def test_monitor_monitoring_only():
    admin = {"role": "monitor"}
    assert admin_can(admin, "monitor.read")
    assert admin_can(admin, "results.read")
    assert admin_can(admin, "olympiads.read")
    assert admin_can(admin, "students.read")
    assert not admin_can(admin, "olympiads.write")
    assert not admin_can(admin, "students.write")
    assert not admin_can(admin, "admins.write")
    assert not admin_can(admin, "content.write")


def test_content_admin_content_only():
    admin = {"role": "content_admin"}
    assert admin_can(admin, "content.read")
    assert admin_can(admin, "content.write")
    assert not admin_can(admin, "quizzes.write")
    assert not admin_can(admin, "students.read")
    assert not admin_can(admin, "monitor.read")


def test_random_role_deny():
    assert normalize_role("random_hacker") is None
    assert role_permissions("random_hacker") == set()
    assert admin_can({"role": "random_hacker"}, "monitor.read") is False
    assert admin_can({"role": ""}, "students.read") is False
    assert admin_can({"role": None}, "admins.read") is False


def test_user_admin_students_schools_not_quiz_write():
    admin = {"role": "user_admin"}
    assert admin_can(admin, "students.write")
    assert admin_can(admin, "schools.write")
    assert not admin_can(admin, "quizzes.write")
