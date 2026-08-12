"""One-attempt + selection resolution."""
from db.olympiad_engine import _resolve_selection


def test_resolve_selection_by_id():
    ans = {"q1": 2}
    q = {"id": "q1", "answer": 0}
    assert _resolve_selection(ans, q, [], 0) == 2


def test_resolve_selection_by_index():
    ans = {"0": 1, 0: 1}
    q = {"id": "other"}
    assert _resolve_selection(ans, q, [], 0) == 1


def test_resolve_selection_by_original_index_in_session():
    ans = {"5": 3}
    q = {"id": "uuid-1"}
    session_qs = [{"id": "uuid-1", "originalIndex": 5}]
    assert _resolve_selection(ans, q, session_qs, 0) == 3


def test_resolve_missing_returns_none():
    assert _resolve_selection({}, {"id": "x"}, [], 0) is None
