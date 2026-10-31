import io
import hashlib
import json
from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from typing import Literal

from pydantic import BaseModel, Field, field_validator
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from core import get_pool, err, rows, row, today_wib, audit, WIB
from security import require_admin
from services import next_period, build_payroll, finalize_closing

router = APIRouter(prefix="/api/payroll")


class PeriodComponentIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    amount: int = Field(ge=0, le=9_000_000_000_000_000)
    volume: Decimal = Field(default=Decimal("1"), ge=0, max_digits=10, decimal_places=2)
    note: Optional[str] = Field(default=None, max_length=200)

    @field_validator("name")
    @classmethod
    def trim_name(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Nama komponen tidak boleh kosong")
        return value

    @field_validator("note")
    @classmethod
    def trim_note(cls, value):
        return value.strip() or None if value is not None else None


class AdjustIn(BaseModel):
    kasbon_deduction: Optional[int] = Field(default=None, ge=0)
    other_deduction: Optional[int] = Field(default=0, ge=0)
    components: Optional[list[PeriodComponentIn]] = Field(default=None, max_length=50)


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
    out = {}
    for eid, value in adj.items():
        item = value.model_dump(exclude_none=True)
        if value.components is not None:
            item["components"] = [{**component.model_dump(), "volume": float(component.volume)} for component in value.components]
        out[eid] = item
    return out


def _finalize_payload_hash(end_date: date, adjustments: dict) -> str:
    normalized = {"end_date": end_date.isoformat(), "adjustments": _ov(adjustments)}
    encoded = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


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
    adjustments = _ov(body.adjustments)
    payload_hash = _finalize_payload_hash(body.end_date, body.adjustments)
    async with pool.acquire() as c:
        return await finalize_closing(c, body.end_date, body.idempotency_key, adjustments, admin["username"], payload_hash)


DELTA_SQL = "CASE WHEN kind='deduction' THEN -amount ELSE amount END"


@router.get("/periods")
async def periods(admin: dict = Depends(require_admin)):
    pool = await get_pool()
    return rows(await pool.fetch(
        "SELECT p.id, p.start_date, p.end_date, p.totals, p.closed_by, p.closed_at, 'closed' AS status, "
        f"(SELECT coalesce(sum({DELTA_SQL}),0) FROM payroll_adjustments a WHERE a.period_id=p.id) AS adjustment_net, "
        "(SELECT count(*) FROM payroll_adjustments a WHERE a.period_id=p.id) AS adjustment_count "
        "FROM payroll_periods p ORDER BY p.end_date DESC"))


def _apply_adjustments(ln: dict, adjs: list) -> dict:
    mine = [a for a in adjs if a["employee_id"] == ln["employee_id"]]
    s = {k: sum(a["amount"] for a in mine if a["kind"] == k) for k in ("earning", "deduction", "kasbon_reversal")}
    net_adj = s["earning"] - s["deduction"] + s["kasbon_reversal"]
    return {**ln, "adj_earning": s["earning"], "adj_deduction": s["deduction"], "adj_kasbon_reversal": s["kasbon_reversal"],
            "adj_net": net_adj, "adj_count": len(mine), "net_effective": ln["net_final"] + net_adj,
            "kasbon_effective": ln["kasbon_deduction"] - s["kasbon_reversal"]}


async def _period(pid: int):
    pool = await get_pool()
    p = await pool.fetchrow("SELECT * FROM payroll_periods WHERE id=$1", pid)
    if not p:
        err(404, "Periode tidak ditemukan")
    snaps = await pool.fetch("SELECT employee_id, data FROM payroll_snapshots WHERE period_id=$1 ORDER BY id", pid)
    adjs = [dict(a) for a in await pool.fetch(
        "SELECT a.*, e.code, e.full_name FROM payroll_adjustments a JOIN employees e ON e.id=a.employee_id "
        "WHERE a.period_id=$1 ORDER BY a.id", pid)]
    return p, [_apply_adjustments(s["data"], adjs) for s in snaps], adjs


@router.get("/periods/{pid}")
async def period_detail(pid: int, admin: dict = Depends(require_admin)):
    p, lines, adjs = await _period(pid)
    out = row(p)
    out.pop("idempotency_key", None)
    out.pop("finalize_payload_hash", None)
    for a in adjs:
        a.pop("idempotency_key", None)
    return {**out, "lines": lines, "adjustments": rows(adjs),
            "adjustment_net": sum(ln["adj_net"] for ln in lines),
            "net_effective_total": sum(ln["net_effective"] for ln in lines)}


KIND_LABEL = {"earning": "Tambahan (kurang bayar)", "deduction": "Potongan (lebih bayar)",
              "kasbon_reversal": "Pembatalan potongan kasbon"}


class AdjustmentIn(BaseModel):
    employee_id: int
    kind: Literal["earning", "deduction", "kasbon_reversal"]
    amount: int = Field(gt=0, le=1_000_000_000)


class AdjustmentCreate(AdjustmentIn):
    reason: str = Field(min_length=5, max_length=500)
    idempotency_key: str = Field(min_length=8, max_length=80)

    @field_validator("reason")
    @classmethod
    def reason_text(cls, v):
        if len(v.strip()) < 5:
            raise ValueError("Alasan minimal 5 karakter")
        return v.strip()


async def _impact(c, pid: int, body: AdjustmentIn) -> dict:
    snap = await c.fetchrow(
        "SELECT s.net_final, s.kasbon_deduction, e.code, e.full_name FROM payroll_snapshots s JOIN employees e ON e.id=s.employee_id "
        "WHERE s.period_id=$1 AND s.employee_id=$2", pid, body.employee_id)
    if not snap:
        err(404, "Karyawan tidak ada dalam snapshot periode ini")
    agg = await c.fetchrow(
        "SELECT coalesce(sum(amount) FILTER (WHERE kind='earning'),0) AS e, coalesce(sum(amount) FILTER (WHERE kind='deduction'),0) AS d, "
        "coalesce(sum(amount) FILTER (WHERE kind='kasbon_reversal'),0) AS r FROM payroll_adjustments WHERE period_id=$1 AND employee_id=$2",
        pid, body.employee_id)
    balance = await c.fetchval(f"SELECT coalesce(sum({DELTA_SQL}),0) FROM cash_advances WHERE employee_id=$1", body.employee_id)
    balance = int(balance)  # sum(bigint) -> numeric/Decimal; Decimal is not JSON serializable for JSONB insert
    cur_net = int(snap["net_final"] + agg["e"] - agg["d"] + agg["r"])
    cur_kasbon = int(snap["kasbon_deduction"] - agg["r"])
    if body.kind == "deduction" and body.amount > cur_net:
        err(422, f"Potongan koreksi melebihi gaji bersih efektif ({rp(cur_net)})")
    if body.kind == "kasbon_reversal" and body.amount > cur_kasbon:
        err(422, f"Pembatalan melebihi potongan kasbon efektif periode ini ({rp(cur_kasbon)})")
    delta = -body.amount if body.kind == "deduction" else body.amount
    rev = body.amount if body.kind == "kasbon_reversal" else 0
    return {
        "employee": {"id": body.employee_id, "code": snap["code"], "full_name": snap["full_name"]},
        "kind": body.kind, "kind_label": KIND_LABEL[body.kind], "amount": body.amount, "delta_net": delta,
        "original": {"net_final": snap["net_final"], "kasbon_deduction": snap["kasbon_deduction"]},
        "before": {"net_final": cur_net, "kasbon_deduction": cur_kasbon, "kasbon_balance": balance},
        "after": {"net_final": cur_net + delta, "kasbon_deduction": cur_kasbon - rev, "kasbon_balance": balance + rev},
    }


@router.post("/periods/{pid}/adjustments/preview")
async def adjustment_preview(pid: int, body: AdjustmentIn, admin: dict = Depends(require_admin)):
    pool = await get_pool()
    async with pool.acquire() as c:
        if not await c.fetchval("SELECT 1 FROM payroll_periods WHERE id=$1", pid):
            err(404, "Periode tidak ditemukan")
        return await _impact(c, pid, body)


@router.post("/periods/{pid}/adjustments")
async def adjustment_create(pid: int, body: AdjustmentCreate, admin: dict = Depends(require_admin)):
    pool = await get_pool()
    async with pool.acquire() as c, c.transaction():
        await c.execute("SELECT pg_advisory_xact_lock(3003, $1)", pid)
        dup = await c.fetchrow("SELECT id, period_id, employee_id, kind, amount FROM payroll_adjustments WHERE idempotency_key=$1", body.idempotency_key)
        if dup:
            if (dup["period_id"], dup["employee_id"], dup["kind"], dup["amount"]) != (pid, body.employee_id, body.kind, body.amount):
                err(409, "Kunci transaksi sudah dipakai untuk koreksi lain")
            return {"id": dup["id"], "duplicate": True}
        if not await c.fetchval("SELECT 1 FROM payroll_periods WHERE id=$1", pid):
            err(404, "Periode tidak ditemukan")
        imp = await _impact(c, pid, body)
        kasbon_tx = None
        if body.kind == "kasbon_reversal":
            kasbon_tx = await c.fetchval(
                "INSERT INTO cash_advances(employee_id, kind, amount, tx_date, note, period_id, created_by) "
                "VALUES($1,'reversal',$2,$3,$4,$5,$6) RETURNING id", body.employee_id, body.amount, today_wib(),
                f"Koreksi periode #{pid}: {body.reason.strip()}"[:200], pid, admin["username"])
        aid = await c.fetchval(
            "INSERT INTO payroll_adjustments(period_id, employee_id, kind, amount, reason, before, after, cash_advance_id, idempotency_key, created_by) "
            "VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10) RETURNING id", pid, body.employee_id, body.kind, body.amount, body.reason.strip(),
            imp["before"], imp["after"], kasbon_tx, body.idempotency_key, admin["username"])
        await audit(c, admin["username"], "payroll_adjusted", "payroll_period", pid,
                    before={"employee": imp["employee"]["code"], **imp["before"]},
                    after={"employee": imp["employee"]["code"], "kind": body.kind, "amount": body.amount, "reason": body.reason.strip(),
                           "adjustment_id": aid, **imp["after"]})
    return {"id": aid, "duplicate": False, **imp}


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
            Paragraph(f"Snapshot final #{p['id']} · ditutup oleh {p['closed_by']} pada {p['closed_at'].astimezone(WIB):%d/%m/%Y %H:%M} WIB", ss["Italic"]),
            Spacer(1, 6 * mm)]


@router.get("/periods/{pid}/recap.pdf")
async def recap_pdf(pid: int, admin: dict = Depends(require_admin)):
    p, lines, _ = await _period(pid)
    data = [["ID", "Nama", "Jam Dibayar", "Lembur", "Gaji Kotor", "Pot. Lain", "Bersih Sblm Kasbon", "Kasbon", "Gaji Bersih", "Koreksi", "Bersih Efektif"]]
    for ln in lines:
        data.append([ln["code"], ln["full_name"][:26], hm(ln["durations"]["paid_minutes"]), hm(ln["overtime_minutes"]),
                     rp(ln["gross"]), rp(ln["other_deduction"]), rp(ln["net_before_kasbon"]), rp(ln["kasbon_deduction"]),
                     rp(ln["net_final"]), rp(ln["adj_net"]), rp(ln["net_effective"])])
    t = p["totals"]
    data.append(["", "TOTAL", "", "", rp(t.get("gross", 0)), rp(t.get("other_deduction", 0)), rp(t.get("net_before_kasbon", 0)),
                 rp(t.get("kasbon_deduction", 0)), rp(t.get("net_final", 0)), rp(sum(x["adj_net"] for x in lines)),
                 rp(sum(x["net_effective"] for x in lines))])
    tbl = _tbl(data, [17 * mm, 46 * mm, 20 * mm, 18 * mm, 26 * mm, 22 * mm, 28 * mm, 24 * mm, 26 * mm, 24 * mm, 26 * mm])
    tbl.setStyle(TableStyle([("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"), ("ALIGN", (3, 1), (-1, -1), "RIGHT")]))
    return _pdf(_head(p, "Rekap Gaji") + [tbl], landscape(A4), f"rekap-gaji-{pid}.pdf")


@router.get("/periods/{pid}/slip/{eid}.pdf")
async def slip_pdf(pid: int, eid: int, admin: dict = Depends(require_admin)):
    p, lines, adjs = await _period(pid)
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
                ["Hasil pengakuan (jam penuh)", hm(d["rounded_minutes"])], ["Jam dibayar", hm(d["paid_minutes"])],
                [f"Gaji reguler ({rp(ln['regular_rate'])}/jam)", rp(ln["regular_amount"])],
                [f"Lembur {hm(ln['overtime_minutes'])} ({rp(ln['overtime_rate'])}/jam)", rp(ln["overtime_amount"])]]
    for comp in ln["components"]:
        det.append([f"{comp['name']} ({rp(comp['amount'])} × {comp['volume']:g})", rp(comp["amount"] * comp["volume"])])
    det += [["Gaji kotor", rp(ln["gross"])], ["Potongan lain", "- " + rp(ln["other_deduction"])],
            ["Gaji bersih sebelum kasbon", rp(ln["net_before_kasbon"])], ["Saldo kasbon", rp(ln["kasbon_balance"])],
            ["Potongan kasbon", "- " + rp(ln["kasbon_deduction"])], ["Sisa kasbon", rp(ln["kasbon_after"])],
            ["GAJI BERSIH AKHIR", rp(ln["net_final"])]]
    mine = [a for a in adjs if a["employee_id"] == eid]
    if mine:
        for a in mine:
            sign = "- " if a["kind"] == "deduction" else "+ "
            det.append([f"Koreksi #{a['id']} {a['created_at'].astimezone(WIB):%d/%m/%Y}: {KIND_LABEL[a['kind']]} — {a['reason'][:50]}", sign + rp(a["amount"])])
        det.append(["GAJI BERSIH SETELAH KOREKSI", rp(ln["net_effective"])])
    t = _tbl(det, [110 * mm, 60 * mm])
    t.setStyle(TableStyle([("ALIGN", (1, 1), (1, -1), "RIGHT"), ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                           ("FONTSIZE", (0, -1), (-1, -1), 10), ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#EAF0FB"))]))
    return _pdf(_head(p, "Slip Gaji") + [info, Spacer(1, 5 * mm), t], A4, f"slip-{ln['code']}-{pid}.pdf")
