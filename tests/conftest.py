"""Shared fixtures for Geografia unit tests (no live DB required)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("FLASK_ENV", "testing")
os.environ.setdefault("ALLOW_JSON_BACKEND", "1")
os.environ.pop("DATABASE_URL", None)
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-key-at-least-32-chars-long!!")


@pytest.fixture
def super_admin() -> dict:
    return {"id": "a1", "login": "root", "role": "super_admin", "name": "Root"}


@pytest.fixture
def olympiad_admin() -> dict:
    return {"id": "a2", "login": "oly", "role": "olympiad_admin", "name": "Oly"}


@pytest.fixture
def monitor_admin() -> dict:
    return {"id": "a3", "login": "mon", "role": "monitor", "name": "Mon"}


@pytest.fixture
def sample_questions() -> list:
    return [
        {
            "id": "q1",
            "text": "Пойтахти Тоҷикистон?",
            "options": [
                {"text": "Душанбе", "is_correct": True},
                {"text": "Хуҷанд", "is_correct": False},
                {"text": "Кӯлоб", "is_correct": False},
            ],
            "answer": 0,
        },
        {
            "id": "q2",
            "text": "Калонтарин кӯл?",
            "options": ["Каракул", "Искандаркӯл", "Сарез"],
            "answer": 0,
        },
    ]
