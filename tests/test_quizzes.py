"""P1.10 — public quiz payload never leaks is_correct."""
from db.public_quiz_sanitize import sanitize_options, sanitize_question, sanitize_quiz_payload


def test_sanitize_options_strips_dict_flags():
    opts = [
        {"text": "A", "is_correct": True},
        {"text": "B", "is_correct": False},
        "C",
    ]
    out = sanitize_options(opts)
    assert out == ["A", "B", "C"]
    assert all(isinstance(x, str) for x in out)


def test_sanitize_question_no_answer_keys(sample_questions):
    q = sanitize_question(sample_questions[0])
    assert "answer" not in q
    assert "is_correct" not in q
    assert "options" in q
    assert all(isinstance(o, str) for o in q["options"])


def test_sanitize_quiz_payload():
    quiz = {
        "id": "qz1",
        "title": "Geo",
        "answer": 0,
        "questions": [
            {
                "id": 1,
                "text": "Q?",
                "options": [{"text": "yes", "is_correct": True}, {"text": "no"}],
                "answer": 0,
            }
        ],
    }
    clean = sanitize_quiz_payload(quiz)
    assert clean is not None
    assert "answer" not in clean
    q0 = clean["questions"][0]
    assert "answer" not in q0
    assert "is_correct" not in str(q0)
