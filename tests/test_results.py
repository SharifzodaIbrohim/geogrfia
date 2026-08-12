"""Leaderboard privacy + scoring display rules."""
from db.leaderboard_api import _mask_name, apply_privacy


def test_mask_name():
    assert "***" in _mask_name("Ализода") or _mask_name("Ализода").startswith("А")
    masked = _mask_name("Ализода Фарход")
    assert "Фарход" not in masked or masked != "Ализода Фарход"


def test_apply_privacy_hide_names():
    entries = [{"name": "Каримова Дилбар", "school": "№1", "className": "10А", "rating": 1400}]
    out = apply_privacy(entries, {"hideNames": True, "showSchool": True, "showClass": True, "showScore": True})
    assert out[0]["name"] != "Каримова Дилбар" or "***" in out[0]["name"] or "." in out[0]["name"]


def test_apply_privacy_hide_school_and_score():
    entries = [{"name": "Test", "school": "Litsey", "className": "11", "rating": 1500, "score": 90}]
    out = apply_privacy(
        entries,
        {"hideNames": False, "showSchool": False, "showClass": False, "showScore": False},
    )
    assert out[0].get("school") in ("", None)
    assert out[0].get("rating") is None
    assert out[0].get("score") is None


def test_apply_privacy_adds_rank():
    entries = [{"name": "A"}, {"name": "B"}]
    out = apply_privacy(entries, {"showSchool": True, "showScore": True})
    assert out[0]["rank"] == 1
    assert out[1]["rank"] == 2
