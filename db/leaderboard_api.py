"""Global public leaderboard from user ratings + olympiad results."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_RATING = 1200

_DEMO = [
    {"id": "demo-1", "name": "Ализода Фарход", "school": "Литсей №1", "className": "11А", "rating": 1480, "solved": 12, "contests": 5},
    {"id": "demo-2", "name": "Каримова Дилбар", "school": "МТМУ №15", "className": "10Б", "rating": 1410, "solved": 9, "contests": 4},
    {"id": "demo-3", "name": "Раҳимов Ҷамолиддин", "school": "Литсей №2", "className": "11Б", "rating": 1365, "solved": 8, "contests": 3},
    {"id": "demo-4", "name": "Саидова Малика", "school": "МТМУ №3", "className": "9А", "rating": 1290, "solved": 6, "contests": 3},
    {"id": "demo-5", "name": "Ҳасанов Беҳрӯз", "school": "Литсей №1", "className": "10А", "rating": 1245, "solved": 5, "contests": 2},
]

def _data_dir() -> Path:
    for p in [Path(__file__).resolve().parent.parent / "data", Path.cwd() / "data", Path("/opt/render/project/src/data")]:
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
PROFILES_FILE = DATA_DIR / "user_profiles.json"
USERS_FILE = DATA_DIR / "users.json"
STUDENTS_FILE = DATA_DIR / "students.json"
RESULTS_FILE = DATA_DIR / "results.json"

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

def get_settings() -> dict:
    data = _load(SETTINGS_FILE)
    if not isinstance(data, dict):
        data = {"public": True, "title": "Leaderboard \u00b7 Top Rated", "showSchool": True, "showClass": True, "pinned": [], "useDemo": True}
        _save(SETTINGS_FILE, data)
    return data

def update_settings(payload: dict) -> dict:
    s = get_settings()
    if "public" in payload: s["public"] = bool(payload["public"])
    if "title" in payload and str(payload["title"]).strip(): s["title"] = str(payload["title"]).strip()[:80]
    if "showSchool" in payload: s["showSchool"] = bool(payload["showSchool"])
    if "showClass" in payload: s["showClass"] = bool(payload["showClass"])
    if "useDemo" in payload: s["useDemo"] = bool(payload["useDemo"])
    if "pinned" in payload and isinstance(payload["pinned"], list): s["pinned"] = payload["pinned"][:50]
    _save(SETTINGS_FILE, s)
    return s

def _profiles_list() -> list:
    try:
        from db import profile_api as pa
        if hasattr(pa, "list_gmail_users"):
            items = pa.list_gmail_users(limit=500) or []
            if items: return items
    except Exception:
        pass
    for path in (PROFILES_FILE, USERS_FILE):
        data = _load(path)
        if isinstance(data, dict):
            items = list(data.values())
            if items: return items
        if isinstance(data, list) and data:
            return data
    return []

def _students_list() -> list:
    try:
        from db.repo import list_students
        rows = list_students() or []
        if rows: return rows
    except Exception:
        pass
    data = _load(STUDENTS_FILE)
    return data if isinstance(data, list) else []

def _results_list() -> list:
    try:
        from db.repo import list_results
        try:
            rows = list_results() or []
            if rows: return rows
        except TypeError:
            pass
    except Exception:
        pass
    data = _load(RESULTS_FILE)
    return data if isinstance(data, list) else []

def _display_name(u: dict) -> str:
    name = (u.get("name") or u.get("fullName") or u.get("displayName") or "").strip()
    if name and not name.lower().startswith("gmail"):
        return name
    email = (u.get("email") or "").strip()
    if email and "@" in email:
        return email.split("@")[0]
    return name or "Иштирокчӣ"

def build_global_leaderboard(*, limit: int = 100, public_only: bool = True) -> dict:
    settings = get_settings()
    if public_only and settings.get("public") is False:
        return {"public": False, "title": settings.get("title") or "Leaderboard", "entries": [], "total": 0, "message": "Leaderboard ҳоло ғайри оммавӣ аст.", "settings": settings}

    by_key = {}
    for u in _profiles_list():
        uid = str(u.get("id") or u.get("userId") or "")
        if not uid: continue
        rating = int(u.get("rating") or u.get("maxRating") or DEFAULT_RATING)
        by_key["u:" + uid] = {"id": uid, "kind": "user", "name": _display_name(u), "school": u.get("school") or u.get("schoolName") or "", "className": u.get("className") or u.get("class") or "", "region": u.get("region") or "", "rating": rating, "maxRating": int(u.get("maxRating") or rating), "contests": int(u.get("contests") or 0), "solved": int(u.get("solved") or 0)}

    for st in _students_list():
        sid = str(st.get("id") or "")
        if not sid: continue
        name = (st.get("fullName") or st.get("name") or "").strip() or "Хонанда"
        by_key["s:" + sid] = {"id": sid, "kind": "student", "name": name, "school": st.get("school") or st.get("schoolName") or "", "className": st.get("className") or st.get("class") or "", "region": st.get("region") or "", "rating": int(st.get("rating") or DEFAULT_RATING), "maxRating": int(st.get("maxRating") or DEFAULT_RATING), "contests": 0, "solved": 0}

    for r in _results_list():
        try:
            sc_i = int(float(r.get("score") or 0))
        except (TypeError, ValueError):
            continue
        sid = str(r.get("studentId") or r.get("studentCode") or "")
        uid = str(r.get("userId") or "")
        key = None
        if uid: key = "u:" + uid
        elif sid.startswith(("g:", "gmail:")): key = "u:" + sid.split(":", 1)[-1]
        elif sid: key = "s:" + sid
        if not key: continue
        entry = by_key.get(key)
        if not entry:
            nm = (r.get("studentName") or "").strip()
            if not nm or nm.lower().startswith("gmail"): nm = "Иштирокчӣ"
            entry = {"id": key.split(":", 1)[-1], "kind": "user" if key.startswith("u:") else "student", "name": nm, "school": r.get("studentSchool") or r.get("school") or "", "className": r.get("studentClass") or r.get("className") or "", "region": "", "rating": DEFAULT_RATING, "maxRating": DEFAULT_RATING, "contests": 0, "solved": 0}
            by_key[key] = entry
        entry["contests"] = int(entry.get("contests") or 0) + 1
        entry["rating"] = max(int(entry.get("rating") or DEFAULT_RATING), DEFAULT_RATING + max(0, sc_i - 50))
        if sc_i >= 70: entry["solved"] = int(entry.get("solved") or 0) + 1

    rows = list(by_key.values())
    demo_used = False
    if not rows and settings.get("useDemo", True):
        demo_used = True
        for d in _DEMO:
            rows.append({"id": d["id"], "kind": "demo", "name": d["name"], "school": d.get("school") or "", "className": d.get("className") or "", "region": "", "rating": int(d.get("rating") or DEFAULT_RATING), "maxRating": int(d.get("rating") or DEFAULT_RATING), "contests": int(d.get("contests") or 0), "solved": int(d.get("solved") or 0)})

    rows.sort(key=lambda x: (-int(x.get("rating") or 0), -int(x.get("solved") or 0), x.get("name") or ""))

    pinned = settings.get("pinned") or []
    entries = []
    if pinned and not demo_used:
        pin_map = {str(p.get("userId") or p.get("id")): p for p in pinned if p.get("rank")}
        fixed, rest = [], []
        for r in rows:
            p = pin_map.get(str(r.get("id")))
            if p:
                r = dict(r); r["_pin"] = int(p["rank"])
                if p.get("name"): r["name"] = p["name"]
                fixed.append(r)
            else: rest.append(r)
        fixed.sort(key=lambda x: x["_pin"])
        fi = ri = 0; rank = 1
        while len(entries) < limit and (fi < len(fixed) or ri < len(rest)):
            if fi < len(fixed) and fixed[fi]["_pin"] == rank:
                e = fixed[fi]; e.pop("_pin", None); e["rank"] = rank; entries.append(e); fi += 1; rank += 1
            elif ri < len(rest):
                e = dict(rest[ri]); e["rank"] = rank; entries.append(e); ri += 1; rank += 1
            else:
                rank += 1
                if rank > limit + 20: break
        entries = entries[:limit]
    else:
        for i, r in enumerate(rows[:limit], start=1):
            e = dict(r); e["rank"] = i; entries.append(e)

    return {"public": True, "title": settings.get("title") or "Leaderboard \u00b7 Top Rated", "showSchool": bool(settings.get("showSchool", True)), "showClass": bool(settings.get("showClass", True)), "entries": entries, "total": len(rows), "demo": demo_used, "settings": settings}
