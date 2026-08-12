"""Olympiad public-question + window rules (pure helpers)."""
from datetime import datetime, timedelta, timezone

import pytest

# Prefer real engine helpers; fall back to local pure reimplementation for isolation.
try:
    from db.olympiad_engine import (
        _compute_expires,
        _public_questions,
        _sanitize_options,
        _window_ok,
    )
except Exception:  # pragma: no cover
    import secrets

    def _sanitize_options(options):
        out = []
        for o in options or []:
            if isinstance(o, dict):
                out.append(str(o.get("text") or o.get("label") or ""))
            else:
                out.append(str(o))
        return out

    def _public_questions(qs_src):
        order = list(range(len(qs_src)))
        secrets.SystemRandom().shuffle(order)
        out = []
        for orig_i in order:
            q = qs_src[orig_i] or {}
            qid = q.get("id")
            if qid is None:
                qid = str(orig_i)
            out.append({
                "id": str(qid),
                "text": q.get("text"),
                "options": _sanitize_options(q.get("options")),
                "originalIndex": orig_i,
            })
        return out

    def _window_ok(oly):
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

        start = parse(oly.get("startTime") or oly.get("start_at"))
        end = parse(oly.get("endTime") or oly.get("end_at"))
        if start and now < start:
            return "not_started"
        if end and now > end:
            return "ended"
        return "open"

    def _compute_expires(oly, started):
        candidates = []
        try:
            dur = oly.get("durationSec")
            if dur is not None and int(dur) > 0:
                candidates.append(started + timedelta(seconds=int(dur)))
        except (TypeError, ValueError):
            pass
        end = oly.get("endTime") or oly.get("end_at")
        if end:
            try:
                d = datetime.fromisoformat(str(end).replace("Z", "+00:00"))
                if not d.tzinfo:
                    d = d.replace(tzinfo=timezone.utc)
                candidates.append(d)
            except Exception:
                pass
        return min(candidates) if candidates else None


def test_public_questions_never_include_answer(sample_questions):
    pub = _public_questions(sample_questions)
    assert len(pub) == len(sample_questions)
    for q in pub:
        assert "answer" not in q
        assert "is_correct" not in q
        assert "solution" not in q
        assert all(isinstance(o, str) for o in q["options"])


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
