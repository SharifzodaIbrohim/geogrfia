"""Admin XLSX export — /api/admin/export/* (openpyxl). Student ID as text."""
from __future__ import annotations

import io
import logging
from datetime import datetime, timezone
from typing import Any

log = logging.getLogger("geografia.export")

STATUS_TJ = {
    "passed": "Гузашт",
    "pass": "Гузашт",
    "failed": "Нагузашт",
    "fail": "Нагузашт",
    "timeout": "Вақт тамом",
    "submitted": "Супорида шуд",
    "in_progress": "Дар ҷараён",
}


def _status_label(st: Any) -> str:
    s = str(st or "").lower()
    return STATUS_TJ.get(s, str(st or "—"))


def _sid(row: dict) -> str:
    v = (
        row.get("studentCode")
        or row.get("studentId")
        or row.get("student_id")
        or row.get("id")
        or ""
    )
    return str(v)


def _name(row: dict) -> str:
    return str(
        row.get("fullName")
        or row.get("studentName")
        or row.get("name")
        or row.get("full_name")
        or "—"
    )


def _school(row: dict) -> str:
    return str(row.get("school") or row.get("studentSchool") or row.get("schoolName") or "—")


def _class(row: dict) -> str:
    return str(row.get("className") or row.get("studentClass") or row.get("class_name") or "—")


def _oly(row: dict) -> str:
    return str(row.get("olympiadTitle") or row.get("title") or row.get("olympiad_title") or "—")


def _score_pct(row: dict) -> Any:
    if row.get("score") is not None:
        return row.get("score")
    c, t = row.get("correct"), row.get("total")
    try:
        if t and float(t) > 0:
            return round(100.0 * float(c or 0) / float(t), 1)
    except Exception:
        pass
    return ""


def _wb_results(rows: list) -> io.BytesIO:
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = "Натиҷаҳо"

    headers = [
        "Ном",
        "Student ID",
        "Мактаб",
        "Синф",
        "Олимпиада",
        "Хол (%)",
        "Дуруст",
        "Ҳама",
        "Статус",
        "Санаи анҷом",
    ]
    header_fill = PatternFill("solid", fgColor="1B4332")
    header_font = Font(bold=True, color="FFFFFF")
    thin = Border(
        left=Side(style="thin", color="CCCCCC"),
        right=Side(style="thin", color="CCCCCC"),
        top=Side(style="thin", color="CCCCCC"),
        bottom=Side(style="thin", color="CCCCCC"),
    )

    for col, h in enumerate(headers, 1):
        cell = ws.cell(1, col, h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin

    for r_i, row in enumerate(rows, 2):
        vals = [
            _name(row),
            _sid(row),
            _school(row),
            _class(row),
            _oly(row),
            _score_pct(row),
            row.get("correct") if row.get("correct") is not None else "",
            row.get("total") if row.get("total") is not None else "",
            _status_label(row.get("status")),
            str(row.get("finishedAt") or row.get("finished_at") or "")[:19],
        ]
        for c_i, v in enumerate(vals, 1):
            cell = ws.cell(r_i, c_i, v)
            cell.border = thin
            if c_i == 2:
                cell.number_format = "@"
                cell.alignment = Alignment(horizontal="left")

    widths = [28, 22, 18, 10, 24, 10, 10, 10, 14, 20]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{max(1, len(rows)+1)}"
    ws.freeze_panes = "A2"

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def _wb_students(rows: list) -> io.BytesIO:
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = "Хонандагон"
    headers = ["Student ID", "Ном", "Мактаб", "Синф", "Санаи бақайд"]
    header_fill = PatternFill("solid", fgColor="1B4332")
    header_font = Font(bold=True, color="FFFFFF")
    thin = Border(
        left=Side(style="thin", color="CCCCCC"),
        right=Side(style="thin", color="CCCCCC"),
        top=Side(style="thin", color="CCCCCC"),
        bottom=Side(style="thin", color="CCCCCC"),
    )
    for col, h in enumerate(headers, 1):
        cell = ws.cell(1, col, h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")
        cell.border = thin
    for r_i, row in enumerate(rows, 2):
        vals = [
            str(row.get("id") or row.get("studentId") or ""),
            str(row.get("fullName") or row.get("name") or "—"),
            str(row.get("school") or "—"),
            str(row.get("className") or "—"),
            str(row.get("createdAt") or "")[:19],
        ]
        for c_i, v in enumerate(vals, 1):
            cell = ws.cell(r_i, c_i, v)
            cell.border = thin
            if c_i == 1:
                cell.number_format = "@"
    for i, w in enumerate([22, 28, 18, 10, 20], 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A2"
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def _wb_full(results: list, students: list, olympiads: list) -> io.BytesIO:
    from openpyxl import Workbook, load_workbook
    from openpyxl.styles import Font, PatternFill
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = "Натиҷаҳо"
    buf_r = _wb_results(results)
    wb_r = load_workbook(buf_r)
    ws_src = wb_r.active
    for row in ws_src.iter_rows():
        for cell in row:
            ws.cell(cell.row, cell.column, cell.value)
            try:
                ws.cell(cell.row, cell.column).number_format = cell.number_format
            except Exception:
                pass
    for i, w in enumerate([28, 22, 18, 10, 24, 10, 10, 10, 14, 20], 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    ws2 = wb.create_sheet("Хонандагон")
    buf_s = _wb_students(students)
    wb_s = load_workbook(buf_s)
    for cell in wb_s.active._cells.values():
        ws2.cell(cell.row, cell.column, cell.value)
        if cell.column == 1:
            ws2.cell(cell.row, cell.column).number_format = "@"
    for i, w in enumerate([22, 28, 18, 10, 20], 1):
        ws2.column_dimensions[get_column_letter(i)].width = w

    ws3 = wb.create_sheet("Олимпиадаҳо")
    headers = ["ID", "Унвон", "Навъ", "Ҳад %", "Фаъол", "Сана"]
    fill = PatternFill("solid", fgColor="1B4332")
    font = Font(bold=True, color="FFFFFF")
    for c, h in enumerate(headers, 1):
        cell = ws3.cell(1, c, h)
        cell.fill = fill
        cell.font = font
    for r_i, o in enumerate(olympiads, 2):
        ws3.cell(r_i, 1, str(o.get("id") or ""))
        ws3.cell(r_i, 1).number_format = "@"
        ws3.cell(r_i, 2, o.get("title") or "")
        ws3.cell(r_i, 3, o.get("type") or "")
        ws3.cell(r_i, 4, o.get("passScore") or o.get("pass_score") or "")
        ws3.cell(r_i, 5, "Ҳа" if o.get("active") else "Не")
        ws3.cell(r_i, 6, str(o.get("createdAt") or "")[:19])
    for i, w in enumerate([36, 28, 12, 10, 10, 20], 1):
        ws3.column_dimensions[get_column_letter(i)].width = w

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def _filter_rows(rows: list, args) -> list:
    school = (args.get("school") or "").strip().lower()
    class_name = (args.get("className") or "").strip().lower()
    status = (args.get("status") or "").strip().lower()
    q = (args.get("q") or "").strip().lower()
    oid = (args.get("olympiadId") or "").strip()
    try:
        smin = float(args.get("scoreMin")) if args.get("scoreMin") not in (None, "") else None
    except Exception:
        smin = None
    try:
        smax = float(args.get("scoreMax")) if args.get("scoreMax") not in (None, "") else None
    except Exception:
        smax = None

    out = []
    for r in rows:
        if oid and str(r.get("olympiadId") or "") != oid:
            continue
        if school and school not in _school(r).lower():
            continue
        if class_name and class_name not in _class(r).lower():
            continue
        if status and status not in str(r.get("status") or "").lower():
            continue
        if q:
            blob = " ".join([_name(r), _sid(r), _school(r), _class(r), _oly(r)]).lower()
            if q not in blob:
                continue
        sc = _score_pct(r)
        try:
            scf = float(sc) if sc != "" and sc is not None else None
        except Exception:
            scf = None
        if smin is not None and (scf is None or scf < smin):
            continue
        if smax is not None and (scf is None or scf > smax):
            continue
        out.append(r)
    return out


def install(app=None):
    from flask import request, send_file, jsonify

    if app is None:
        from flask import current_app

        app = current_app._get_current_object()

    def _auth_headers():
        h = {}
        tok = request.headers.get("X-Admin-Token") or ""
        auth = request.headers.get("Authorization") or ""
        if tok:
            h["X-Admin-Token"] = tok
        if auth:
            h["Authorization"] = auth
        return h

    def _get_json(path: str):
        with app.test_client() as client:
            for k, v in request.cookies.items():
                client.set_cookie("localhost", k, v)
            r = client.get(path, headers=_auth_headers())
            if r.status_code == 401:
                return None, 401
            if r.status_code >= 400:
                return None, r.status_code
            try:
                return r.get_json(silent=True) or {}, 200
            except Exception:
                return {}, 200

    def _send_xlsx(buf: io.BytesIO, filename: str):
        return send_file(
            buf,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=filename,
        )

    @app.get("/api/admin/export/preview")
    def admin_export_preview():
        data, code = _get_json("/api/admin/results?" + request.query_string.decode())
        if code == 401:
            return jsonify({"error": "Дастрасӣ рад шуд."}), 401
        rows = (data or {}).get("results") or (data or {}).get("items") or []
        rows = _filter_rows(rows, request.args)
        return jsonify({"count": len(rows), "total": len(rows)})

    @app.get("/api/admin/export/results")
    def admin_export_results():
        data, code = _get_json("/api/admin/results?" + request.query_string.decode())
        if code == 401:
            return jsonify({"error": "Дастрасӣ рад шуд."}), 401
        rows = (data or {}).get("results") or (data or {}).get("items") or []
        rows = _filter_rows(rows, request.args)
        buf = _wb_results(rows)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
        return _send_xlsx(buf, f"Geografia_Results_{stamp}.xlsx")

    @app.get("/api/admin/export/olympiad/<oid>")
    def admin_export_olympiad(oid):
        data, code = _get_json(f"/api/admin/olympiads/{oid}/results")
        if code == 401:
            return jsonify({"error": "Дастрасӣ рад шуд."}), 401
        if code >= 400:
            data, code = _get_json(f"/api/admin/results?olympiadId={oid}")
            if code == 401:
                return jsonify({"error": "Дастрасӣ рад шуд."}), 401
        rows = (data or {}).get("results") or (data or {}).get("items") or []
        buf = _wb_results(rows)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
        return _send_xlsx(buf, f"Geografia_Olympiad_{stamp}.xlsx")

    @app.get("/api/admin/export/students")
    def admin_export_students():
        data, code = _get_json("/api/admin/students")
        if code == 401:
            return jsonify({"error": "Дастрасӣ рад шуд."}), 401
        rows = (data or {}).get("students") or (data or {}).get("items") or []
        buf = _wb_students(rows)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
        return _send_xlsx(buf, f"Geografia_Students_{stamp}.xlsx")

    @app.get("/api/admin/export/full")
    def admin_export_full():
        res_data, code = _get_json("/api/admin/results")
        if code == 401:
            return jsonify({"error": "Дастрасӣ рад шуд."}), 401
        st_data, _ = _get_json("/api/admin/students")
        ol_data, _ = _get_json("/api/admin/olympiads")
        results = (res_data or {}).get("results") or []
        students = (st_data or {}).get("students") or []
        olympiads = (ol_data or {}).get("olympiads") or (ol_data if isinstance(ol_data, list) else [])
        buf = _wb_full(results, students, olympiads)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
        return _send_xlsx(buf, f"Geografia_Full_{stamp}.xlsx")

    print("[boot] patch_admin_export: XLSX routes /api/admin/export/* installed")
    return True
