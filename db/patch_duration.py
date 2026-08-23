"""durationMin (minutes) <-> durationSec; 0 = unlimited.
Also wraps olympiad_engine.start_exam so timer uses durationSec correctly.
"""
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


def _duration_min_from_oly(oly: dict) -> int:
    if not isinstance(oly, dict):
        return 60
    sec = oly.get("durationSec")
    if sec is not None and sec != "":
        try:
            sec = int(sec)
            if sec <= 0:
                return 0
            return max(1, (sec + 59) // 60)
        except (TypeError, ValueError):
            pass
    for key in ("durationMin", "duration"):
        if oly.get(key) is not None and oly.get(key) != "":
            try:
                dm = int(oly[key])
                return 0 if dm <= 0 else max(1, dm)
            except (TypeError, ValueError):
                pass
    return 60


def _remaining_sec_from_oly(oly: dict):
    if not isinstance(oly, dict):
        return 3600
    sec = oly.get("durationSec")
    if sec is not None and sec != "":
        try:
            sec = int(sec)
            return None if sec <= 0 else max(1, sec)
        except (TypeError, ValueError):
            pass
    dm = _duration_min_from_oly(oly)
    return None if dm <= 0 else dm * 60


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

    for finder_name in ("find_olympiad", "get_olympiad"):
        if hasattr(repo, finder_name):
            _orig_f = getattr(repo, finder_name)

            def _make_find(orig):
                def find_olympiad(oid):
                    o = orig(oid)
                    return _enrich(dict(o)) if o else o
                return find_olympiad

            setattr(repo, finder_name, _make_find(_orig_f))

    try:
        from db import olympiad_engine as oe

        _orig_start = oe.start_exam

        def start_exam(olympiad_id, student_code, fingerprint=None, **kwargs):
            try:
                oly = None
                if hasattr(oe, "find_olympiad"):
                    oly = oe.find_olympiad(olympiad_id)
                if oly is None:
                    oly = repo.find_olympiad(str(olympiad_id))
                if oly:
                    _enrich(oly)
                    dm = _duration_min_from_oly(oly)
                    oly["durationMin"] = dm
                    if hasattr(oe, "find_olympiad"):
                        _oe_find = oe.find_olympiad
                        def _find_patched(oid, _oly=oly, _id=str(olympiad_id), _orig=_oe_find):
                            if str(oid) == _id:
                                return _oly
                            return _orig(oid)
                        oe.find_olympiad = _find_patched
            except Exception as e:
                log.warning("duration pre-start enrich: %s", e)

            result = _orig_start(olympiad_id, student_code, fingerprint=fingerprint, **kwargs)

            try:
                if isinstance(result, dict) and result.get("ok") and not result.get("resumed"):
                    oly = repo.find_olympiad(str(olympiad_id)) or {}
                    _enrich(oly)
                    rem = _remaining_sec_from_oly(oly)
                    dm = _duration_min_from_oly(oly)
                    if rem is not None:
                        result["remainingSec"] = rem
                        result["durationMin"] = dm
                    else:
                        result["remainingSec"] = None
                        result["durationMin"] = 0
            except Exception as e:
                log.warning("duration post-start fix: %s", e)

            return result

        oe.start_exam = start_exam
        log.info("start_exam durationSec wrap installed")
        print("[boot] patch_duration: start_exam uses durationSec")
    except Exception as e:
        log.warning("patch_duration start wrap: %s", e)

    log.info("patch_duration installed")
    print("[boot] patch_duration: durationMin/Sec + unlimited(0) + start_exam")
