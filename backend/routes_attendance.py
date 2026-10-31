import hashlib
import secrets
from datetime import date, datetime, time, timedelta
from typing import Literal, Optional

import asyncpg
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field, field_validator

from core import get_pool, err, audit, rows, row, today_wib, now_wib, get_settings, ensure_open_date, rate_limit, client_ip, WIB, invalidate_settings
from kiosk_security import kiosk_pin_scope, pin_scope_locked, record_pin_attempt
from rules import compute_regular, compute_overtime, schedule_bounds
from security import current_user, require_admin, make_token, decode_token, verify_secret
from services import clock, create_early_pin, employee_state

router = APIRouter(prefix="/api")


@router.get("/time")
async def server_time():
    n = now_wib()
    return {"now": n.isoformat(), "date": n.date().isoformat(), "timezone": "WIB"}


@router.get("/attendance")
async def list_attendance(work_date: Optional[date] = None, user: dict = Depends(current_user)):
    t = today_wib()
    d = work_date or t
    if user["role"] != "admin" and d != t:
        err(403, "Operator hanya dapat melihat absensi hari ini")
    pool = await get_pool()
    async with pool.acquire() as c:
        cfg = await get_settings(c)
        emps = await c.fetch(
            "SELECT e.id, e.code, e.full_name, e.payroll_mode, e.active, d.name AS department FROM employees e "
            "LEFT JOIN departments d ON d.id=e.department_id "
            "WHERE e.active OR e.id IN (SELECT employee_id FROM attendance WHERE work_date=$1) ORDER BY e.code", d)
        att = {a["employee_id"]: a for a in await c.fetch("SELECT * FROM attendance WHERE work_date=$1", d)}
        open_prev = {a["employee_id"]: a for a in await c.fetch(
            "SELECT * FROM attendance WHERE status='hadir' AND check_out IS NULL AND work_date<$1", d)} if d == t else {}
        ots = {}
        for o in await c.fetch("SELECT * FROM overtime_sessions WHERE work_date=$1 OR check_out IS NULL ORDER BY check_in", d):
            ots.setdefault(o["employee_id"], []).append(o)
        closed_end = await c.fetchval("SELECT max(end_date) FROM payroll_periods")
    out = []
    for e in emps:
        a = att.get(e["id"]) or open_prev.get(e["id"])
        rec = row(a) if a else None
        if a and a["status"] == "hadir" and a["check_in"]:
            rec["calc"] = compute_regular(a["check_in"], a["check_out"], a["work_date"], cfg)
        ot_list = [{**row(o), "calc": compute_overtime(
            o["check_in"], o["check_out"], cfg, schedule_bounds(o["work_date"], cfg)[1]
        )} for o in ots.get(e["id"], [])]
        out.append({**row(e), "attendance": rec, "overtime": ot_list,
                    "overtime_open": any(o["check_out"] is None for o in ots.get(e["id"], []))})
    return {"date": d.isoformat(), "today": t.isoformat(), "locked": bool(closed_end and d <= closed_end),
            "overtime_enabled": cfg.get("overtime_enabled"), "rows": out}


class ClockIn(BaseModel):
    employee_id: int
    mode: Literal["regular", "overtime"] = "regular"
    action: Literal["in", "out"]
    early_pin: Optional[str] = Field(default=None, pattern=r"^\d{6}$")


def _validate_clock_time(value):
    if value is not None:
        try:
            h, m = map(int, value.split(":"))
            time(h, m)
        except (ValueError, AttributeError):
            raise ValueError("Jam harus berupa waktu valid dengan format HH:MM")
    return value


def _check_result(res):
    if res.get("error"):
        err(403, res["error"])
    return res


@router.post("/attendance/clock")
async def staff_clock(body: ClockIn, request: Request, user: dict = Depends(current_user)):
    if body.early_pin:
        rate_limit(request, f"pin:{body.employee_id}", 10, 300)
    pool = await get_pool()
    async with pool.acquire() as c:
        return _check_result(await clock(c, body.employee_id, body.mode, body.action, user["username"], "panel", body.early_pin))


class ManualIn(BaseModel):
    employee_id: int
    status: Literal["hadir", "sakit", "izin", "alfa"]
    note: Optional[str] = Field(default=None, max_length=300)
    work_date: Optional[date] = None
    check_in: Optional[str] = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    check_out: Optional[str] = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    check_out_next_day: bool = False
    reason: Optional[str] = Field(default=None, max_length=300)

    @field_validator("check_in", "check_out")
    @classmethod
    def valid_clock_time(cls, value):
        return _validate_clock_time(value)


def _ts(d: date, hm: Optional[str], next_day=False):
    if not hm:
        return None
    h, m = map(int, hm.split(":"))
    return datetime.combine(d + timedelta(days=1 if next_day else 0), time(h, m), tzinfo=WIB)


def _is_early_leave(work_date: date, check_out: Optional[datetime], cfg: dict) -> bool:
    return bool(check_out and check_out < schedule_bounds(work_date, cfg)[1])


@router.post("/attendance/manual")
async def manual_entry(body: ManualIn, user: dict = Depends(current_user)):
    t = today_wib()
    is_admin = user["role"] == "admin"
    d = body.work_date or t
    custom_times = body.check_in or body.check_out
    if not is_admin and (d != t or custom_times):
        err(403, "Operator hanya dapat mencatat absensi hari ini dengan waktu server")
    if d > t:
        err(422, "Tanggal tidak boleh melebihi hari ini")
    if is_admin and (d != t or custom_times) and not (body.reason and body.reason.strip()):
        err(422, "Alasan wajib diisi untuk input historis atau waktu manual")
    pool = await get_pool()
    async with pool.acquire() as c:
        await ensure_open_date(c, d)
        cin, cout = None, None
        if body.status == "hadir":
            cin = _ts(d, body.check_in) if body.check_in else (now_wib() if d == t else None)
            if cin is None:
                err(422, "Jam Masuk wajib diisi untuk input historis")
            cout = _ts(d, body.check_out, body.check_out_next_day)
            if cout and cout < cin:
                err(422, "Jam Keluar tidak boleh sebelum jam Masuk")
            if cin > now_wib() or (cout and cout > now_wib()):
                err(422, "Waktu tidak boleh melebihi waktu server saat ini")
        try:
            async with c.transaction():
                # Serialize every attendance entry path with kiosk/clock so manual input
                # cannot create a regular session beside an open overtime session.
                await c.execute("SELECT pg_advisory_xact_lock(1001, $1)", body.employee_id)
                emp = await c.fetchrow("SELECT active FROM employees WHERE id=$1 FOR UPDATE", body.employee_id)
                if not emp:
                    err(404, "Karyawan tidak ditemukan")
                if not emp["active"]:
                    err(409, "Karyawan nonaktif tidak dapat melakukan absensi")
                if cin and not cout and await c.fetchval(
                    "SELECT 1 FROM overtime_sessions WHERE employee_id=$1 AND check_out IS NULL",
                    body.employee_id,
                ):
                    err(409, "Tutup sesi lembur terlebih dahulu sebelum membuka sesi reguler")
                early_leave = _is_early_leave(d, cout, await get_settings(c)) if body.status == "hadir" else False
                r = await c.fetchrow(
                    "INSERT INTO attendance(employee_id, work_date, status, check_in, check_out, early_leave, source, note, created_by) "
                    "VALUES($1,$2,$3,$4,$5,$6,'manual',$7,$8) ON CONFLICT (employee_id, work_date) DO NOTHING RETURNING id",
                    body.employee_id, d, body.status, cin, cout, early_leave, body.note, user["username"])
                if not r:
                    err(409, "Absensi karyawan pada tanggal ini sudah tercatat")
                fmt = lambda v: v.astimezone(WIB).strftime("%Y-%m-%d %H:%M") if v else None  # noqa: E731
                await audit(c, user["username"], "attendance_manual", "attendance", r["id"],
                            after={"status": body.status, "date": d.isoformat(), "check_in": fmt(cin),
                                   "check_out": fmt(cout), "early_leave": early_leave, "reason": body.reason})
        except asyncpg.UniqueViolationError:
            err(409, "Masih ada sesi Masuk yang belum ditutup")
    return {"id": r["id"]}


class CorrectionIn(BaseModel):
    status: Literal["hadir", "sakit", "izin", "alfa"]
    check_in: Optional[str] = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    check_out: Optional[str] = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    check_out_next_day: bool = False
    note: Optional[str] = Field(default=None, max_length=300)
    reason: str = Field(min_length=3, max_length=300)

    @field_validator("check_in", "check_out")
    @classmethod
    def valid_clock_time(cls, value):
        return _validate_clock_time(value)

    @field_validator("reason")
    @classmethod
    def reason_text(cls, value):
        value = value.strip()
        if len(value) < 3:
            raise ValueError("Alasan minimal 3 karakter")
        return value


@router.put("/attendance/{aid}")
async def correct_attendance(aid: int, body: CorrectionIn, admin: dict = Depends(require_admin)):
    pool = await get_pool()
    async with pool.acquire() as c:
        try:
            async with c.transaction():
                employee_id = await c.fetchval("SELECT employee_id FROM attendance WHERE id=$1", aid)
                if employee_id is None:
                    err(404, "Data absensi tidak ditemukan")
                await c.execute("SELECT pg_advisory_xact_lock(1001, $1)", employee_id)
                a = await c.fetchrow("SELECT * FROM attendance WHERE id=$1 FOR UPDATE", aid)
                if not a:
                    err(404, "Data absensi tidak ditemukan")
                await ensure_open_date(c, a["work_date"])
                cin = _ts(a["work_date"], body.check_in) if body.status == "hadir" else None
                cout = _ts(a["work_date"], body.check_out, body.check_out_next_day) if body.status == "hadir" else None
                if body.status == "hadir" and not cin:
                    err(422, "Jam Masuk wajib untuk status Hadir")
                if cout and cout < cin:
                    err(422, "Jam Keluar tidak boleh sebelum jam Masuk")
                if (cin and cin > now_wib()) or (cout and cout > now_wib()):
                    err(422, "Waktu tidak boleh melebihi waktu server saat ini")
                if cin and not cout and await c.fetchval(
                    "SELECT 1 FROM overtime_sessions WHERE employee_id=$1 AND check_out IS NULL",
                    a["employee_id"],
                ):
                    err(409, "Tutup sesi lembur terlebih dahulu sebelum membuka sesi reguler")
                early = _is_early_leave(a["work_date"], cout, await get_settings(c)) if body.status == "hadir" else False
                await c.execute("UPDATE attendance SET status=$2, check_in=$3, check_out=$4, note=$5, early_leave=$6 WHERE id=$1",
                                aid, body.status, cin, cout, body.note, early)
                fmt = lambda v: v.astimezone(WIB).strftime("%Y-%m-%d %H:%M") if v else None  # noqa: E731
                await audit(c, admin["username"], "attendance_corrected", "attendance", aid,
                            before={"status": a["status"], "check_in": fmt(a["check_in"]), "check_out": fmt(a["check_out"])},
                            after={"status": body.status, "check_in": fmt(cin), "check_out": fmt(cout), "reason": body.reason})
        except asyncpg.UniqueViolationError:
            err(409, "Karyawan masih memiliki sesi terbuka lain")
    return {"ok": True}


@router.post("/attendance/{aid}/early-pin")
async def early_pin(aid: int, admin: dict = Depends(require_admin)):
    pool = await get_pool()
    async with pool.acquire() as c:
        return await create_early_pin(c, aid, admin["username"])


# ---------------- Kiosk (public) ----------------

def _kt_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()[:16]


async def _kiosk_cfg(c, token: str, request: Request) -> dict:
    rate_limit(request, "kiosk", 240, 60)
    # Kiosk authorization must observe rotations/disablement immediately on every instance.
    cfg = await c.fetchval("SELECT value FROM settings WHERE key='app'") or {}
    if not cfg.get("kiosk_enabled") or not secrets.compare_digest(token, cfg.get("kiosk_token", "")):
        err(404, "Tautan kiosk tidak aktif")
    return cfg


@router.get("/kiosk/{token}")
async def kiosk_info(token: str, request: Request):
    pool = await get_pool()
    async with pool.acquire() as c:
        cfg = await _kiosk_cfg(c, token, request)
    return {"company_name": cfg["company_name"], "overtime_enabled": cfg.get("overtime_enabled"),
            "now": now_wib().isoformat(), "start_time": cfg["start_time"], "end_time": cfg["end_time"]}


@router.get("/kiosk/{token}/employees")
async def kiosk_employees(token: str, request: Request, q: str = ""):
    pool = await get_pool()
    async with pool.acquire() as c:
        await _kiosk_cfg(c, token, request)
        if len(q.strip()) < 1:
            return []
        rs = await c.fetch(
            "SELECT e.id, e.code, e.full_name, d.name AS department FROM employees e LEFT JOIN departments d ON d.id=e.department_id "
            "WHERE e.active AND e.payroll_mode='hourly' AND (e.full_name ILIKE $1 OR e.code ILIKE $1) ORDER BY e.full_name LIMIT 12",
            f"%{q.strip()}%")
    return rows(rs)


@router.get("/kiosk/{token}/employees/{eid}/state")
async def kiosk_state(token: str, eid: int, request: Request):
    pool = await get_pool()
    async with pool.acquire() as c:
        await _kiosk_cfg(c, token, request)
        if not await c.fetchval("SELECT 1 FROM employees WHERE id=$1 AND active AND payroll_mode='hourly'", eid):
            err(404, "Karyawan tidak ditemukan")
        return await employee_state(c, eid)


@router.post("/kiosk/{token}/overtime-unlock")
async def kiosk_ot_unlock(token: str, body: dict, request: Request):
    rate_limit(request, "kiosk_pin", 5, 300)
    scope = kiosk_pin_scope(token, client_ip(request))
    pool = await get_pool()
    async with pool.acquire() as c:
        cfg = await _kiosk_cfg(c, token, request)
        if not cfg.get("overtime_enabled"):
            err(403, "Fitur lembur sedang nonaktif")
        pin = str(body.get("pin", ""))[:6]
        async with c.transaction():
            live = await c.fetchval("SELECT value FROM settings WHERE key='app' FOR UPDATE")
            attempts = live.get("ot_pin_attempts_by_source", {})
            if pin_scope_locked(attempts, scope, now_wib().timestamp()):
                err(429, "Terlalu banyak PIN salah. Mode lembur dikunci sementara.")
            ok = bool(live.get("overtime_pin_hash")) and verify_secret(pin, live["overtime_pin_hash"])
            attempts = record_pin_attempt(attempts, scope, now_wib().timestamp(), ok)
            live["ot_pin_attempts_by_source"] = attempts
            # Drop the old application-wide lockout state during the first write after upgrade.
            live.pop("ot_pin_failures", None)
            live.pop("ot_pin_locked_until", None)
            await c.execute("UPDATE settings SET value=$1 WHERE key='app'", live)
            invalidate_settings()
            await audit(c, "kiosk", "overtime_unlocked" if ok else "overtime_unlock_failed", "kiosk", result="success" if ok else "failed")
        if not ok:
            err(403, "PIN lembur salah")
    return {"ot_token": make_token({"typ": "kiosk_ot", "kt": _kt_hash(token)}, 12)}


class KioskClockIn(ClockIn):
    ot_token: Optional[str] = None


@router.post("/kiosk/{token}/clock")
async def kiosk_clock(token: str, body: KioskClockIn, request: Request):
    rate_limit(request, "kiosk_clock", 30, 60)
    if body.early_pin:
        rate_limit(request, f"pin:{body.employee_id}", 10, 300)
    pool = await get_pool()
    async with pool.acquire() as c:
        await _kiosk_cfg(c, token, request)
        if body.mode == "overtime":
            claims = decode_token(body.ot_token or "x") if body.ot_token else err(403, "Mode lembur terkunci")
            if claims.get("typ") != "kiosk_ot" or claims.get("kt") != _kt_hash(token):
                err(403, "Mode lembur terkunci")
        return _check_result(await clock(c, body.employee_id, body.mode, body.action, "kiosk", "kiosk", body.early_pin))
