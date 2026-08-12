"""Answer selection resolution for submit scoring."""


def _resolve_selection(ans, q, session_questions, index):
    candidates = [
        str(q.get("id")) if q.get("id") is not None else None,
        str(index),
        index,
        str(q.get("originalIndex")) if q.get("originalIndex") is not None else None,
    ]
    for sq in session_questions:
        if sq.get("originalIndex") == index or str(sq.get("id")) == str(q.get("id")):
            if sq.get("id") is not None:
                candidates.append(str(sq.get("id")))
            if sq.get("originalIndex") is not None:
                candidates.append(str(sq.get("originalIndex")))
    for k in candidates:
        if k is None:
            continue
        if k in ans:
            return ans[k]
        if str(k) in ans:
            return ans[str(k)]
    return None


def test_resolve_selection_by_id():
    assert _resolve_selection({"q1": 2}, {"id": "q1"}, [], 0) == 2


def test_resolve_selection_by_index():
    assert _resolve_selection({"0": 1}, {"id": "other"}, [], 0) == 1


def test_resolve_selection_by_original_index_in_session():
    ans = {"5": 3}
    q = {"id": "uuid-1"}
    session_qs = [{"id": "uuid-1", "originalIndex": 5}]
    assert _resolve_selection(ans, q, session_qs, 0) == 3


def test_resolve_missing_returns_none():
    assert _resolve_selection({}, {"id": "x"}, [], 0) is None
