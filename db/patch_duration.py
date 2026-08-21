"""durationMin (minutes) <-> durationSec; 0 = unlimited."""
from __future__ import annotations
import logging
log = logging.getLogger("geografia.patch_duration")

def _to_sec(payload: dict):
    if not isinstance(payload, dict):
        return None
    if payload.get("durationSec") not in (None, ""):
        try:
            return int(payload["durationSec"])
        except (TypeError, ValueError):
            return None
    if "durationMin" in payload:
        try:
            dm = int(payload.get("durationMin"))
            return None if dm <= 0 else max(1, dm) * 60
        except (TypeError, ValueError):
            return None
    return None

def _enrich(o: dict) -> dict:
    if not isinstance(o, dict):
        return o
    sec = o.get("durationSec")
    if sec is None and o.get("durationMin") is not None:
        try:
            dm = int(o["durationMin"])
            sec = None if dm <= 0 else dm * 60
            o["durationSec"] = sec
        except (TypeError, ValueError):
            pass
    if sec is not None:
        try:
            sec = int(sec)
            o["durationSec"] = sec
            o["durationMin"] = 0 if sec <= 0 else max(1, sec // 60)
        except (TypeError, ValueError):
            pass
    return o

def install(app=None):
    try:
        import db.repo as repo
    except Exception as e:
        log.warning("repo import: %s", e)
        return

    if hasattr(repo, "create_olympiad"):
        _orig_c = repo.create_olympiad
        def create_olympiad(data):
            data = dict(data or {})
            if "durationMin" in data or "durationSec" in data:
                data["durationSec"] = _to_sec(data)
            return _orig_c(data)
        repo.create_olympiad = create_olympiad

    if hasattr(repo, "update_olympiad"):
        _orig_u = repo.update_olympiad
        def update_olympiad(oid, patch):
            patch = dict(patch or {})
            if "durationMin" in patch or "durationSec" in patch:
                patch["durationSec"] = _to_sec(patch)
            return _orig_u(oid, patch)
        repo.update_olympiad = update_olympiad

    if hasattr(repo, "list_olympiads"):
        _orig_l = repo.list_olympiads
        def list_olympiads():
            return [_enrich(dict(x)) for x in (_orig_l() or [])]
        repo.list_olympiads = list_olympiads

    if hasattr(repo, "get_olympiad"):
        _orig_g = repo.get_olympiad
        def get_olympiad(oid):
            o = _orig_g(oid)
            return _enrich(dict(o)) if o else o
        repo.get_olympiad = get_olympiad

    log.info("patch_duration installed")
    print("[boot] patch_duration: durationMin/Sec + unlimited(0)")
