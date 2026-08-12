"""Olympiad engine — public questions + window + expires."""
from datetime import datetime, timedelta, timezone

from db.olympiad_engine import (
    _compute_expires,
    _public_questions,
    _sanitize_options,
    _window_ok,
)


def test_public_questions_never_include_answer(sample_questions):
    pub = _public_questions(sample_questions)
    assert len(pub) == len(sample_questions)
    for q in pub:
        assert "answer" not in q
        assert "is_correct" not in q
        assert "solution" not in q
        assert "options" in q
        assert all(isinstance(o, str) for o in q["options"])
        assert "originalIndex" in q


def test_sanitize_options_dict():
    assert _sanitize_options([{"text": "X", "is_correct": True}]) == ["X"]


def test_window_closed_when_inactive():
    assert _window_ok({"isActive": False}) == "closed"


def test_window_open_when_active_no_bounds():
    assert _window_ok({"isActive": True}) == "open"


def test_window_not_started():
    future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    assert _window_ok({"isActive": True, "startTime": future}) == "not_started"


def test_window_ended():
    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    assert _window_ok({"isActive": True, "endTime": past}) == "ended"


def test_compute_expires_uses_duration():
    started = datetime.now(timezone.utc)
    exp = _compute_expires({"durationSec": 600}, started)
    assert exp is not None
    assert abs((exp - started).total_seconds() - 600) < 1


def test_compute_expires_min_of_duration_and_end():
    started = datetime.now(timezone.utc)
    end = started + timedelta(seconds=100)
    exp = _compute_expires(
        {"durationSec": 600, "endTime": end.isoformat()},
        started,
    )
    assert exp is not None
    assert abs((exp - started).total_seconds() - 100) < 1
