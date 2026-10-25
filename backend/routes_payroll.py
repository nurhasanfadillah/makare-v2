import io
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from core import get_pool, err, rows, row, today_wib
from security import require_admin
from services import next_period, build_payroll, finalize_closing

router = APIRouter(prefix="/api/payroll")


class AdjustIn(BaseModel):
    kasbon_deduction: Optional[int] = Field(default=None, ge=0)
    other_deduction: Optional[int] = Field(default=0, ge=0)


class PreviewIn(BaseModel):
    end_date: date
    adjustments: dict[str, AdjustIn] = {}


class FinalizeIn(PreviewIn):
    idempotency_key: str = Field(min_length=8, max_length=80)


@router.get("/next-period")
async def get_next_period(admin: dict = Depends(require_admin)):
    pool = await get_pool()
    async with pool.acquire() as c:
        return await next_period(c)


def _ov(adj):
    return {k: v.model_dump() for k, v in adj.items()}


@router.post("/preview")
async def preview(body: PreviewIn, admin: dict = Depends(require_admin)):
    pool = await get_pool()
    async with pool.acquire() as c:
        nxt = await next_period(c)
        start = date.fromisoformat(nxt["start_date"])
        if body.end_date < start or body.end_date > today_wib():
            err(422, f"Tanggal akhir harus antara {start} dan hari ini")
        return await build_payroll(c, start, body.end_date, _ov(body.adjustments))


@router.post("/finalize")
async def finalize(body: FinalizeIn, admin: dict = Depends(require_admin)):
    pool = await get_pool()
    async with pool.acquire() as c:
        return await finalize_closing(c, body.end_date, body.idempotency_key, _ov(body.adjustments), admin["username"])


@router.get("/periods")
async def periods(admin: dict = Depends(require_admin)):
    pool = await get_pool()
    return rows(await pool.fetch("SELECT id, start_date, end_date, totals, closed_by, closed_at FROM payroll_periods ORDER BY end_date DESC"))


async def _period(pid: int):
    pool = await get_pool()
    p = await pool.fetchrow("SELECT * FROM payroll_periods WHERE id=$1", pid)
    if not p:
        err(404, "Periode tidak ditemukan")
    snaps = await pool.fetch("SELECT employee_id, data FROM payroll_snapshots WHERE period_id=$1 ORDER BY id", pid)
    return p, [s["data"] for s in snaps]


@router.get("/periods/{pid}")
async def period_detail(pid: int, admin: dict = Depends(require_admin)):
    p, lines = await _period(pid)
    out = row(p)
    out.pop("idempotency_key", None)
    return {**out, "lines": lines}


def rp(v) -> str:
    return "Rp " + f"{int(v):,}".replace(",", ".")


def hm(m) -> str:
    m = int(m)
    sign = "-" if m < 0 else ""
    m = abs(m)
    return f"{sign}{m // 60}j {m % 60:02d}m"


NAVY = colors.HexColor("#0B1F3A")
BLUE = colors.HexColor("#174EA6")
GRID = colors.HexColor("#D9E2EF")


def _tbl(data, widths, header=True):
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    st = [("FONTSIZE", (0, 0), (-1, -1), 8), ("GRID", (0, 0), (-1, -1), 0.4, GRID),
          ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if header:
        st += [("BACKGROUND", (0, 0), (-1, 0), BLUE), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold")]
    t.setStyle(TableStyle(st))
    return t


def _pdf(story, size, name):
    buf = io.BytesIO()
    SimpleDocTemplate(buf, pagesize=size, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=12 * mm, bottomMargin=12 * mm).build(story)
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{name}"'})


def _head(p, title):
    ss = getSampleStyleSheet()
    cfg = p["settings_snapshot"]
    h = ss["Title"].clone("h", textColor=NAVY, fontSize=15, alignment=0, spaceAfter=2)
    return [Paragraph(cfg.get("company_name", "MAKARE"), h),
            Paragraph(f"{title} — Periode {p['start_date']:%d/%m/%Y} s.d. {p['end_date']:%d/%m/%Y}", ss["Normal"]),
            Paragraph(f"Snapshot final #{p['id']} · ditutup oleh {p['closed_by']} pada {p['closed_at']:%d/%m/%Y %H:%M} WIB", ss["Italic"]),
            Spacer(1, 6 * mm)]


@router.get("/periods/{pid}/recap.pdf")
async def recap_pdf(pid: int, admin: dict = Depends(require_admin)):
    p, lines = await _period(pid)
    data = [["ID", "Nama", "Mode", "Jam Dibayar", "Lembur", "Gaji Kotor", "Potongan Lain", "Bersih Sblm Kasbon", "Kasbon", "Gaji Bersih"]]
    for ln in lines:
        data.append([ln["code"], ln["full_name"][:28], "Harian Jam" if ln["payroll_mode"] == "hourly" else "Manual",
                     hm(ln["durations"]["paid_minutes"]), hm(ln["overtime_minutes"]), rp(ln["gross"]), rp(ln["other_deduction"]),
                     rp(ln["net_before_kasbon"]), rp(ln["kasbon_deduction"]), rp(ln["net_final"])])
    t = p["totals"]
    data.append(["", "TOTAL", "", "", "", rp(t.get("gross", 0)), rp(t.get("other_deduction", 0)), rp(t.get("net_before_kasbon", 0)),
                 rp(t.get("kasbon_deduction", 0)), rp(t.get("net_final", 0))])
    tbl = _tbl(data, [18 * mm, 52 * mm, 20 * mm, 22 * mm, 20 * mm, 28 * mm, 26 * mm, 32 * mm, 26 * mm, 28 * mm])
    tbl.setStyle(TableStyle([("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"), ("ALIGN", (3, 1), (-1, -1), "RIGHT")]))
    return _pdf(_head(p, "Rekap Gaji") + [tbl], landscape(A4), f"rekap-gaji-{pid}.pdf")


@router.get("/periods/{pid}/slip/{eid}.pdf")
async def slip_pdf(pid: int, eid: int, admin: dict = Depends(require_admin)):
    p, lines = await _period(pid)
    ln = next((x for x in lines if x["employee_id"] == eid), None)
    if not ln:
        err(404, "Slip tidak ditemukan")
    d = ln["durations"]
    c = ln["counts"]
    info = _tbl([["Karyawan", f"{ln['code']} — {ln['full_name']}"], ["Departemen", ln.get("department") or "-"],
                 ["Mode Payroll", "Harian Berbasis Jam" if ln["payroll_mode"] == "hourly" else "Manual"],
                 ["Kehadiran", f"Hadir {c['hadir']} · Sakit {c['sakit']} · Izin {c['izin']} · Alfa {c['alfa']} · Terlambat {c['late']}"]],
                [40 * mm, 130 * mm], header=False)
    det = [["Rincian", "Nilai"]]
    if ln["payroll_mode"] == "hourly":
        det += [["Durasi aktual", hm(d["raw_minutes"])], ["Durasi istirahat", hm(d["break_minutes"])],
                ["Penyesuaian keterlambatan", hm(d["late_adjustment_minutes"])], ["Durasi memenuhi syarat", hm(d["eligible_minutes"])],
                ["Hasil pembulatan", hm(d["rounded_minutes"])], ["Jam dibayar", hm(d["paid_minutes"])],
                [f"Gaji reguler ({rp(ln['regular_rate'])}/jam)", rp(ln["regular_amount"])],
                [f"Lembur {hm(ln['overtime_minutes'])} ({rp(ln['overtime_rate'])}/jam)", rp(ln["overtime_amount"])]]
    for comp in ln["components"]:
        det.append([f"{comp['name']} ({rp(comp['amount'])} × {comp['volume']:g})", rp(comp["amount"] * comp["volume"])])
    det += [["Gaji kotor", rp(ln["gross"])], ["Potongan lain", "- " + rp(ln["other_deduction"])],
            ["Gaji bersih sebelum kasbon", rp(ln["net_before_kasbon"])], ["Saldo kasbon", rp(ln["kasbon_balance"])],
            ["Potongan kasbon", "- " + rp(ln["kasbon_deduction"])], ["Sisa kasbon", rp(ln["kasbon_after"])],
            ["GAJI BERSIH AKHIR", rp(ln["net_final"])]]
    t = _tbl(det, [110 * mm, 60 * mm])
    t.setStyle(TableStyle([("ALIGN", (1, 1), (1, -1), "RIGHT"), ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                           ("FONTSIZE", (0, -1), (-1, -1), 10), ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#EAF0FB"))]))
    return _pdf(_head(p, "Slip Gaji") + [info, Spacer(1, 5 * mm), t], A4, f"slip-{ln['code']}-{pid}.pdf")
