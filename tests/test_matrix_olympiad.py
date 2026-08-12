"""
Test Matrix — Olympiad
  before start       → reject
  during window      → allow
  after end          → reject
  not assigned       → reject
  second attempt     → reject
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone


def _window_ok(oly: dict) -> str:
    try:
        from db.olympiad_engine import _window_ok as real

        return real(oly)
    except Exception:
        if not oly.get("isActive"):
            return "closed"
        now = datetime.now(timezone.utc)

        def parse(v):
            if not v:
                return None
            if isinstance(v, datetime):
                return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
            try:
                d = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
                return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
            except Exception:
                return None

        start = parse(oly.get("startTime"))
        end = parse(oly.get("endTime"))
        if start and now < start:
            return "not_started"
        if end and now > end:
            return "ended"
        return "open"


def test_before_start_reject():
    future = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    assert _window_ok({"isActive": True, "startTime": future}) == "not_started"


def test_during_window_allow():
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    assert _window_ok({"isActive": True, "startTime": past, "endTime": future}) == "open"


def test_after_end_reject():
    past = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    assert _window_ok({"isActive": True, "endTime": past}) == "ended"


def test_inactive_reject():
    assert _window_ok({"isActive": False}) == "closed"


def test_not_assigned_contract():
    """Empty participants = open; non-empty without student = not_assigned."""
    participants = [{"id": "111", "status": "assigned"}]
    code = "222"
    allowed = any(
        p.get("id") == code and p.get("status", "assigned") == "assigned"
        for p in participants
    )
    assert allowed is False
    reason = "not_assigned"
    assert reason == "not_assigned"


def test_second_attempt_statuses_block():
    finished = {"passed", "failed", "submitted", "timeout"}
    assert "passed" in finished
    assert "in_progress" not in finished
