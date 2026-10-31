import io
from datetime import date, timedelta
from typing import Optional
from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from core import get_pool, err, get_settings, today_wib, WIB
from rules import compute_regular, compute_overtime, schedule_bounds
from security import require_admin

router = APIRouter(prefix="/api/reports")


def _active_at_shift_start(events, work_date: date, cfg: dict) -> bool:
    shift_start, _ = schedule_bounds(work_date, cfg)
    active = True  # Employees are created active; subsequent transitions are audit events.
    for event in events:
        changed_at = event["created_at"].astimezone(WIB)
        if changed_at > shift_start:
            break
        active = event["action"] == "employee_activated"
    return active


async def _attendance_data(start_date: date, end_date: date, employee_id: Optional[int]):
    if end_date < start_date:
        err(422, "Tanggal akhir harus sama atau setelah tanggal awal")
    if end_date > today_wib():
        err(422, "Tanggal laporan tidak boleh melebihi hari ini")
    if (end_date - start_date).days > 365:
        err(422, "Rentang laporan maksimal 366 hari")

    pool = await get_pool()
    async with pool.acquire() as c:
        cfg = await get_settings(c)
        employees = await c.fetch(
            "SELECT e.id, e.code, e.full_name, e.join_date, e.active FROM employees e "
            "WHERE e.join_date <= $1 AND ($2::int IS NULL OR e.id=$2) ORDER BY e.code",
            end_date, employee_id)
        if employee_id is not None and not employees:
            if not await c.fetchval("SELECT 1 FROM employees WHERE id=$1", employee_id):
                err(404, "Karyawan tidak ditemukan")
        status_events = await c.fetch(
            "SELECT entity_id, action, created_at FROM audit_logs WHERE entity='employee' "
            "AND action IN ('employee_activated','employee_deactivated') AND entity_id ~ '^[0-9]+$' "
            "AND entity_id=ANY($1::text[]) "
            "ORDER BY created_at, id", [str(e["id"]) for e in employees]) if employees else []
        attendance = await c.fetch(
            "SELECT * FROM attendance WHERE work_date BETWEEN $1 AND $2 "
            "AND ($3::int IS NULL OR employee_id=$3)", start_date, end_date, employee_id)
        overtime = await c.fetch(
            "SELECT * FROM overtime_sessions WHERE work_date BETWEEN $1 AND $2 "
            "AND ($3::int IS NULL OR employee_id=$3) ORDER BY check_in", start_date, end_date, employee_id)

    by_attendance = {(a["employee_id"], a["work_date"]): a for a in attendance}
    by_overtime = {}
    for session in overtime:
        by_overtime.setdefault((session["employee_id"], session["work_date"]), []).append(session)

    events_by_employee = {}
    for event in status_events:
        events_by_employee.setdefault(int(event["entity_id"]), []).append(event)

    work_days = set(cfg.get("work_days", []))
    report_rows = []
    counts = {"hadir": 0, "sakit": 0, "izin": 0, "alfa_manual": 0, "inferred_absence": 0}
    totals = {"regular_minutes": 0, "overtime_minutes": 0, "late_minutes": 0, "sessions_over_24h": 0}
    for employee in employees:
        d = start_date
        while d <= end_date:
            if d < employee["join_date"]:
                d += timedelta(days=1)
                continue
            att = by_attendance.get((employee["id"], d))
            ot_sessions = by_overtime.get((employee["id"], d), [])
            scheduled_workday = d.isoweekday() in work_days
            if not scheduled_workday and att is None and not ot_sessions:
                d += timedelta(days=1)
                continue
            active_at_shift_start = scheduled_workday and _active_at_shift_start(
                events_by_employee.get(employee["id"], []), d, cfg
            )
            if att is None and not ot_sessions and not active_at_shift_start:
                d += timedelta(days=1)
                continue
            inferred = att is None and not ot_sessions and active_at_shift_start
            status = att["status"] if att else ("tanpa_catatan" if inferred else "—")
            regular = compute_regular(att["check_in"], att["check_out"], d, cfg) if att and att["status"] == "hadir" and att["check_in"] else None
            late = regular["late_minutes"] if regular else 0
            regular_minutes = regular["raw_minutes"] if regular else 0
            overtime_minutes = 0
            overtime_open = False
            for session in ot_sessions:
                calc = compute_overtime(session["check_in"], session["check_out"], cfg, schedule_bounds(d, cfg)[1])
                overtime_minutes += calc["raw_minutes"]
                overtime_open = overtime_open or calc["incomplete"]
            duration_over_24h = regular_minutes > 1440 or overtime_minutes > 1440
            if att:
                counts[att["status"] if att["status"] != "alfa" else "alfa_manual"] += 1
            elif inferred:
                counts["inferred_absence"] += 1
            totals["regular_minutes"] += regular_minutes
            totals["overtime_minutes"] += overtime_minutes
            totals["late_minutes"] += late
            totals["sessions_over_24h"] += int(duration_over_24h)
            report_rows.append({
                "employee_id": employee["id"], "code": employee["code"], "full_name": employee["full_name"],
                "work_date": d.isoformat(), "status": status,
                "attendance_source": att["source"] if att else ("inferred" if inferred else None),
                "regular_minutes": regular_minutes, "overtime_minutes": overtime_minutes,
                "late_minutes": late, "regular_open": bool(regular and regular["incomplete"]),
                "overtime_open": overtime_open, "inferred_absence": inferred,
                "duration_over_24h": duration_over_24h,
            })
            d += timedelta(days=1)
    return {"start_date": start_date.isoformat(), "end_date": end_date.isoformat(),
            "employee_id": employee_id, "summary": {**counts, **totals}, "rows": report_rows}


@router.get("/attendance")
async def attendance_report(start_date: date, end_date: date, employee_id: Optional[int] = None,
                            admin: dict = Depends(require_admin)):
    return await _attendance_data(start_date, end_date, employee_id)


@router.get("/attendance.pdf")
async def attendance_report_pdf(start_date: date = Query(...), end_date: date = Query(...),
                                employee_id: Optional[int] = None, admin: dict = Depends(require_admin)):
    report = await _attendance_data(start_date, end_date, employee_id)
    pool = await get_pool()
    async with pool.acquire() as c:
        cfg = await get_settings(c)
    styles = getSampleStyleSheet()
    title = styles["Title"].clone("attendance-title", textColor=colors.HexColor("#0B1F3A"), fontSize=15,
                                    alignment=0, spaceAfter=3)
    summary = report["summary"]
    story = [Paragraph(escape(cfg.get("company_name", "MAKARE")), title),
             Paragraph("Rekap Kehadiran", styles["Heading2"]),
             Paragraph(f"Periode {start_date:%d/%m/%Y} s.d. {end_date:%d/%m/%Y} · "
                       f"Hadir {summary['hadir']} · Sakit {summary['sakit']} · Izin {summary['izin']} · "
                       f"Alfa manual {summary['alfa_manual']} · Tanpa catatan {summary['inferred_absence']}", styles["Normal"]),
             Spacer(1, 5 * mm)]
    data = [["Tanggal", "ID", "Nama", "Status", "Reguler", "Lembur", "Terlambat", "Sumber", "Peringatan"]]
    label = {"hadir": "Hadir", "sakit": "Sakit", "izin": "Izin", "alfa": "Alfa manual", "tanpa_catatan": "Tanpa catatan"}
    for item in report["rows"]:
        work_date = date.fromisoformat(item["work_date"])
        hm = lambda value: f"{value // 60}j {value % 60:02d}m"
        source = "Inferensi" if item["inferred_absence"] else (item["attendance_source"] or "—")
        data.append([work_date.strftime("%d/%m/%Y"), escape(item["code"]), escape(item["full_name"]),
                     label.get(item["status"], item["status"]), hm(item["regular_minutes"]),
                     hm(item["overtime_minutes"]), hm(item["late_minutes"]), escape(source),
                     "Periksa durasi >24 jam" if item["duration_over_24h"] else "—"])
    table = Table(data, colWidths=[23 * mm, 18 * mm, 54 * mm, 28 * mm, 22 * mm, 22 * mm, 22 * mm, 19 * mm, 32 * mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#174EA6")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7), ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D9E2EF")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F7FB")]),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(table)
    buffer = io.BytesIO()
    SimpleDocTemplate(buffer, pagesize=landscape(A4), leftMargin=10 * mm, rightMargin=10 * mm,
                      topMargin=10 * mm, bottomMargin=10 * mm).build(story)
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/pdf",
                             headers={"Content-Disposition": 'attachment; filename="rekap-kehadiran.pdf"'})
