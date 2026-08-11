"""Global public leaderboard + privacy settings (P1 admin completeness)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_RATING = 1200

_DEMO = [
    {"id": "demo-1", "name": "Ализода Фарход", "school": "Литсей №1", "className": "11А", "rating": 1480, "solved": 12, "contests": 5},
    {"id": "demo-2", "name": "Каримова Дилбар", "school": "МТМУ №15", "className": "10Б", "rating": 1410, "solved": 9, "contests": 4},
    {"id": "demo-3", "name": "Раҳимов Ҷамолиддин", "school": "Литсей №2", "className": "11Б", "rating": 1365, "solved": 8, "contests": 3},
]


def _data_dir() -> Path:
    for p in [
        Path(__file__).resolve().parent.parent / "data",
        Path.cwd() / "data",
        Path("/opt/render/project/src/data"),
    ]:
        try:
            p.mkdir(parents=True, exist_ok=True)
            return p
        except Exception:
            continue
    p = Path.cwd() / "data"
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return p


DATA_DIR = _data_dir()
SETTINGS_FILE = DATA_DIR / "leaderboard_settings.json"


def _load(path: Path):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return None


def _save(path: Path, data) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


_DEFAULT_SETTINGS = {
    "public": True,  # show_public_leaderboard
    "title": "Leaderboard · Top Rated",
    "hideNames": False,
    "showSchool": True,
    "showClass": True,
    "showScore": True,
    "pinned": [],
    "useDemo": True,
}


def get_settings() -> dict:
    data = _load(SETTINGS_FILE)
    if not isinstance(data, dict):
        data = dict(_DEFAULT_SETTINGS)
        _save(SETTINGS_FILE, data)
    # ensure all keys exist
    for k, v in _DEFAULT_SETTINGS.items():
        if k not in data:
            data[k] = v
    return data


def update_settings(payload: dict) -> dict:
    s = get_settings()
    if "public" in payload or "show_public_leaderboard" in payload:
        s["public"] = bool(payload.get("public", payload.get("show_public_leaderboard")))
    if "title" in payload and str(payload["title"]).strip():
        s["title"] = str(payload["title"]).strip()[:80]
    if "hideNames" in payload or "hide_names" in payload:
        s["hideNames"] = bool(payload.get("hideNames", payload.get("hide_names")))
    if "showSchool" in payload or "show_school" in payload:
        s["showSchool"] = bool(payload.get("showSchool", payload.get("show_school")))
    if "showClass" in payload:
        s["showClass"] = bool(payload["showClass"])
    if "showScore" in payload or "show_score" in payload:
        s["showScore"] = bool(payload.get("showScore", payload.get("show_score")))
    if "useDemo" in payload:
        s["useDemo"] = bool(payload["useDemo"])
    if "pinned" in payload and isinstance(payload["pinned"], list):
        s["pinned"] = payload["pinned"][:50]
    _save(SETTINGS_FILE, s)
    return s


def _mask_name(name: str) -> str:
    name = (name or "").strip() or "Иштирокчӣ"
    parts = name.split()
    if len(parts) == 1:
        return parts[0][:1] + "***"
    return parts[0] + " " + parts[-1][:1] + "."


def apply_privacy(entries: list, settings: dict | None = None) -> list:
    s = settings or get_settings()
    hide_names = bool(s.get("hideNames"))
    show_school = s.get("showSchool") is not False
    show_class = s.get("showClass") is not False
    show_score = s.get("showScore") is not False
    out = []
    for i, e in enumerate(entries or []):
        row = dict(e) if isinstance(e, dict) else {"name": str(e)}
        row["rank"] = int(row.get("rank") or (i + 1))
        if hide_names:
            row["name"] = _mask_name(str(row.get("name") or ""))
            row["displayName"] = row["name"]
        if not show_school:
            row["school"] = ""
            row.pop("schoolName", None)
        if not show_class:
            row["className"] = ""
            row.pop("class", None)
        if not show_score:
            row["rating"] = None
            row["score"] = None
            row["best"] = None
        out.append(row)
    return out


def build_global_leaderboard(*, limit: int = 100, public_only: bool = True) -> dict:
    settings = get_settings()
    if public_only and settings.get("public") is False:
        return {
            "public": False,
            "title": settings.get("title") or "Leaderboard",
            "entries": [],
            "total": 0,
            "message": "Leaderboard ҳоло ғайри оммавӣ аст.",
            "settings": {
                "public": False,
                "hideNames": settings.get("hideNames"),
                "showSchool": settings.get("showSchool"),
                "showClass": settings.get("showClass"),
                "showScore": settings.get("showScore"),
            },
        }

    rows = []
    try:
        from sqlalchemy import text
        from db.connection import get_session, is_postgres_enabled

        if is_postgres_enabled():
            with get_session() as s:
                rws = s.execute(
                    text(
                        "SELECT COALESCE(student_name, 'Иштирокчӣ') AS name, "
                        "student_school AS school, student_class AS class_name, "
                        "MAX(score) AS best, COUNT(*) AS contests "
                        "FROM attempts WHERE status IN ('passed','failed','submitted','timeout') "
                        "AND student_name IS NOT NULL "
                        "GROUP BY student_name, student_school, student_class "
                        "ORDER BY best DESC NULLS LAST LIMIT :lim"
                    ),
                    {"lim": int(limit) or 100},
                ).mappings().all()
                for r in rws:
                    rows.append({
                        "name": r["name"],
                        "school": r["school"] or "",
                        "className": r["class_name"] or "",
                        "rating": int(r["best"] or 0),
                        "score": int(r["best"] or 0),
                        "contests": int(r["contests"] or 0),
                        "solved": int(r["contests"] or 0),
                    })
    except Exception:
        pass

    demo_used = False
    if not rows and settings.get("useDemo", True):
        rows = [dict(x) for x in _DEMO]
        demo_used = True

    # pinned ranks
    pinned = settings.get("pinned") or []
    for p in pinned:
        rank = int(p.get("rank") or 0)
        if rank < 1:
            continue
        name = p.get("name") or p.get("userId") or "Pinned"
        entry = {"name": name, "school": "", "className": "", "rating": 0, "pinned": True}
        while len(rows) < rank:
            rows.append({"name": "—", "school": "", "className": "", "rating": 0})
        rows.insert(rank - 1, entry)

    entries = apply_privacy(rows[: int(limit) or 100], settings)
    return {
        "public": True,
        "title": settings.get("title") or "Leaderboard · Top Rated",
        "showSchool": bool(settings.get("showSchool", True)),
        "showClass": bool(settings.get("showClass", True)),
        "showScore": bool(settings.get("showScore", True)),
        "hideNames": bool(settings.get("hideNames", False)),
        "entries": entries,
        "total": len(entries),
        "demo": demo_used,
        "settings": settings,
    }


def build_leaderboard(**kwargs):
    return build_global_leaderboard(**kwargs).get("entries") or []
