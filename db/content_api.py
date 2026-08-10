"""Courses / books / articles content store — self-contained (no hard repo deps)."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _data_dir() -> Path:
    candidates = [
        Path(__file__).resolve().parent.parent / "data",
        Path.cwd() / "data",
        Path("/opt/render/project/src/data"),
        Path("/app/data"),
    ]
    for p in candidates:
        try:
            p.mkdir(parents=True, exist_ok=True)
            return p
        except Exception:
            continue
    p = Path.cwd() / "data"
    p.mkdir(parents=True, exist_ok=True)
    return p


DATA_DIR = _data_dir()
CONTENT_FILE = DATA_DIR / "content_items.json"

DEFAULT_BOOKS = [
    {"title": "География 7", "url": "/books/kitobkhon-net-geografiya-7.pdf", "type": "book", "lang": "tg"},
    {"title": "География 8 (2014)", "url": "/books/kitobkhon-net-8.-geografiya-2014.pdf", "type": "book", "lang": "tg"},
    {"title": "География 9 (2013)", "url": "/books/kitobkhon-net-9.-geografiya-2013.pdf", "type": "book", "lang": "tg"},
    {"title": "География 10", "url": "/books/kitobkhon-net-geografiya-10.pdf", "type": "book", "lang": "tg"},
    {"title": "География 11 (2015)", "url": "/books/kitobkhon-net-11.-geografiya-2015.pdf", "type": "book", "lang": "tg"},
]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _load_json(path: Path) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return []


def _save_json(path: Path, data: Any) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def _items() -> list[dict]:
    data = _load_json(CONTENT_FILE)
    if not isinstance(data, list):
        data = []
    if not data:
        now = _utc_now().isoformat()
        data = []
        for b in DEFAULT_BOOKS:
            data.append({
                "id": str(uuid.uuid4()),
                "type": b["type"],
                "title": b["title"],
                "description": "",
                "url": b["url"],
                "lang": b["lang"],
                "createdAt": now,
            })
        _save_json(CONTENT_FILE, data)
    return data


def list_content(kind: str | None = None, lang: str | None = None) -> list[dict]:
    rows = _items()
    if kind:
        rows = [r for r in rows if r.get("type") == kind]
    if lang:
        rows = [r for r in rows if r.get("lang") == lang or not r.get("lang")]
    return sorted(rows, key=lambda x: x.get("createdAt") or "", reverse=True)


def add_content(payload: dict) -> dict:
    title = str(payload.get("title") or "").strip()
    if len(title) < 2:
        raise ValueError("title_required")
    kind = str(payload.get("type") or "article").strip().lower()
    if kind not in ("book", "article", "magazine", "link"):
        kind = "article"
    item = {
        "id": str(uuid.uuid4()),
        "type": kind,
        "title": title,
        "description": str(payload.get("description") or "").strip(),
        "url": str(payload.get("url") or "").strip(),
        "lang": str(payload.get("lang") or "tg").strip()[:5],
        "createdAt": _utc_now().isoformat(),
    }
    rows = _items()
    rows.insert(0, item)
    _save_json(CONTENT_FILE, rows)
    return item


def delete_content(item_id: str) -> bool:
    rows = _items()
    n = len(rows)
    rows = [r for r in rows if r.get("id") != item_id]
    if len(rows) == n:
        return False
    _save_json(CONTENT_FILE, rows)
    return True
