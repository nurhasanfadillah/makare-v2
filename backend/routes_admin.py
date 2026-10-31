import io
import secrets
from datetime import date, time
from typing import Literal, Optional
from xml.sax.saxutils import escape

import asyncpg
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator, model_validator
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from core import get_pool, err, audit, rows, row, today_wib, get_settings, invalidate_settings
from schema import hash_secret
from security import current_user, require_admin

router = APIRouter(prefix="/api")


@router.get("/dashboard")
async def dashboard(user: dict = Depends(current_user)):
    pool = await get_pool()
    t = today_wib()
    async with pool.acquire() as c:
        cfg = await get_settings(c)
        from rules import compute_regular
        active = await c.fetchval("SELECT count(*) FROM employees WHERE active")
        today_rows = await c.fetch("SELECT status, check_in, check_out, work_date FROM attendance WHERE work_date=$1", t)
        late = sum(1 for r in today_rows if r["status"] == "hadir" and r["check_in"]
                   and compute_regular(r["check_in"], r["check_out"], r["work_date"], cfg)["is_late"])
        counts = {s: sum(1 for r in today_rows if r["status"] == s) for s in ["hadir", "sakit", "izin", "alfa"]}
        open_reg = await c.fetchval("SELECT count(*) FROM attendance WHERE status='hadir' AND check_out IS NULL")
        open_ot = await c.fetchval("SELECT count(*) FROM overtime_sessions WHERE check_out IS NULL")
        res = {"active_employees": active, "today": counts, "late_today": late, "open_sessions": open_reg,
               "open_overtime": open_ot, "date": t.isoformat(), "overtime_enabled": cfg.get("overtime_enabled")}
        if user["role"] == "admin":
            last = await c.fetchrow("SELECT id, start_date, end_date, closed_at, totals FROM payroll_periods ORDER BY end_date DESC LIMIT 1")
            res["last_period"] = row(last)
            from services import next_period
            res["next_period"] = await next_period(c)
            res["kasbon_outstanding"] = await c.fetchval(
                "SELECT coalesce(sum(CASE WHEN kind='deduction' THEN -amount ELSE amount END),0) FROM cash_advances")
            res["recent_activity"] = rows(await c.fetch(
                "SELECT actor, action, entity, entity_id, result, created_at FROM audit_logs WHERE action <> 'login' ORDER BY id DESC LIMIT 8"))
    return res


class ComponentIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    amount: int = Field(ge=0)
    volume: float = Field(ge=0, default=1)
    note: Optional[str] = Field(default=None, max_length=200)


class EmployeeIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    gender: Literal["L", "P"]
    address: Optional[str] = Field(default=None, max_length=300)
    birth_date: Optional[date] = None
    ktp: Optional[str] = Field(default=None, pattern=r"^\d{16}$")
    phone: Optional[str] = Field(default=None, max_length=20)
    department_id: Optional[int] = None
    join_date: date
    payroll_mode: Literal["hourly", "manual"]
    regular_rate: int = Field(ge=0, default=0)
    overtime_rate: int = Field(ge=0, default=0)
    components: list[ComponentIn] = []

    @field_validator("ktp", "phone", "address", mode="before")
    @classmethod
    def blank_none(cls, v):
        return v or None


EMP_PUBLIC = "e.id, e.code, e.full_name, e.department_id, d.name AS department, e.payroll_mode, e.active"
EMP_FULL = "e.*, d.name AS department"


@router.get("/employees")
async def list_employees(q: str = "", status: str = "all", department_id: Optional[int] = None, mode: str = "all",
                         user: dict = Depends(current_user)):
    cols = EMP_FULL if user["role"] == "admin" else EMP_PUBLIC
    sql = f"SELECT {cols} FROM employees e LEFT JOIN departments d ON d.id=e.department_id WHERE (e.full_name ILIKE $1 OR e.code ILIKE $1)"
    args = [f"%{q.strip()}%"]
    if status in ("active", "inactive"):
        sql += f" AND e.active = {'TRUE' if status == 'active' else 'FALSE'}"
    if mode in ("hourly", "manual"):
        args.append(mode)
        sql += f" AND e.payroll_mode=${len(args)}"
    if department_id:
        args.append(department_id)
        sql += f" AND e.department_id=${len(args)}"
    pool = await get_pool()
    return rows(await pool.fetch(sql + " ORDER BY e.code", *args))


@router.get("/employees/directory.pdf")
async def employee_directory_pdf(admin: dict = Depends(require_admin)):
    pool = await get_pool()
    async with pool.acquire() as c:
        employees = await c.fetch(
            "SELECT e.code, e.full_name, d.name AS department, e.payroll_mode, e.join_date, e.active "
            "FROM employees e LEFT JOIN departments d ON d.id=e.department_id ORDER BY e.code")
        settings = await get_settings(c)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), leftMargin=14 * mm, rightMargin=14 * mm,
                            topMargin=12 * mm, bottomMargin=12 * mm)
    styles = getSampleStyleSheet()
    title = styles["Title"].clone("directory-title", textColor=colors.HexColor("#0B1F3A"), fontSize=16,
                                    alignment=0, spaceAfter=3)
    story = [Paragraph(escape(settings.get("company_name", "MAKARE")), title),
             Paragraph("Direktori Karyawan", styles["Heading2"]),
             Paragraph(f"Dicetak {today_wib():%d/%m/%Y} WIB · {len(employees)} karyawan", styles["Normal"]),
             Spacer(1, 5 * mm)]
    data = [["ID Karyawan", "Nama", "Departemen", "Mode Payroll", "Tanggal Masuk", "Status"]]
    for employee in employees:
        data.append([escape(employee["code"] or ""), escape(employee["full_name"] or ""),
                     escape(employee["department"] or "—"),
                     "Harian berbasis jam" if employee["payroll_mode"] == "hourly" else "Manual",
                     employee["join_date"].strftime("%d/%m/%Y"), "Aktif" if employee["active"] else "Nonaktif"])
    table = Table(data, colWidths=[32 * mm, 65 * mm, 48 * mm, 42 * mm, 32 * mm, 24 * mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#174EA6")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8), ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D9E2EF")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F7FB")]),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(table)
    doc.build(story)
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/pdf",
                             headers={"Content-Disposition": 'attachment; filename="direktori-karyawan.pdf"'})


@router.get("/employees/{eid}")
async def get_employee(eid: int, admin: dict = Depends(require_admin)):
    pool = await get_pool()
    e = await pool.fetchrow(f"SELECT {EMP_FULL} FROM employees e LEFT JOIN departments d ON d.id=e.department_id WHERE e.id=$1", eid)
    if not e:
        err(404, "Karyawan tidak ditemukan")
    out = row(e)
    out["components"] = [{**dict(c), "volume": float(c["volume"])} for c in await pool.fetch(
        "SELECT name, amount, volume, note FROM employee_components WHERE employee_id=$1 ORDER BY id", eid)]
    out["kasbon_balance"] = await pool.fetchval(
        "SELECT coalesce(sum(CASE WHEN kind='deduction' THEN -amount ELSE amount END),0) FROM cash_advances WHERE employee_id=$1", eid)
    return out


@router.get("/employees/{eid}/history")
async def employee_history(eid: int, limit: int = Query(100, ge=1, le=500), admin: dict = Depends(require_admin)):
    pool = await get_pool()
    if not await pool.fetchval("SELECT 1 FROM employees WHERE id=$1", eid):
        err(404, "Karyawan tidak ditemukan")
    events = await pool.fetch(
        "SELECT id, actor, action, before, after, result, created_at FROM audit_logs "
        "WHERE entity='employee' AND entity_id=$1 ORDER BY id DESC LIMIT $2", str(eid), limit)
    safe_events = []
    for event in events:
        fields = set()
        for payload in (event["before"], event["after"]):
            if not isinstance(payload, dict):
                continue
            changed = payload.get("changed_fields")
            if isinstance(changed, list):
                fields.update(str(key) for key in changed)
            else:
                fields.update(str(key) for key in payload if key not in {"changed_fields", "components"})
        if event["action"] in {"employee_activated", "employee_deactivated"}:
            fields.add("active")
        safe_events.append({
            "id": event["id"],
            "actor": event["actor"],
            "action": event["action"],
            "result": event["result"],
            "created_at": event["created_at"].isoformat(),
            "changed_fields": sorted(fields),
        })
    return safe_events


class EmployeeNoteIn(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    category: str = Field(min_length=1, max_length=40)
    note_date: date
    body: str = Field(min_length=1, max_length=5000)

    @field_validator("title", "category", "body")
    @classmethod
    def trim_note_text(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Tidak boleh kosong")
        return value


@router.get("/employees/{eid}/notes")
async def list_employee_notes(eid: int, admin: dict = Depends(require_admin)):
    pool = await get_pool()
    if not await pool.fetchval("SELECT 1 FROM employees WHERE id=$1", eid):
        err(404, "Karyawan tidak ditemukan")
    return rows(await pool.fetch(
        "SELECT n.*, (SELECT count(*) FROM employee_note_revisions r WHERE r.note_id=n.id) AS revision_count "
        "FROM employee_notes n WHERE n.employee_id=$1 ORDER BY n.note_date DESC, n.id DESC", eid))


@router.post("/employees/{eid}/notes", status_code=201)
async def create_employee_note(eid: int, body: EmployeeNoteIn, admin: dict = Depends(require_admin)):
    pool = await get_pool()
    async with pool.acquire() as c, c.transaction():
        if not await c.fetchval("SELECT 1 FROM employees WHERE id=$1", eid):
            err(404, "Karyawan tidak ditemukan")
        note = await c.fetchrow(
            "INSERT INTO employee_notes(employee_id,title,category,note_date,body,created_by) "
            "VALUES($1,$2,$3,$4,$5,$6) RETURNING *",
            eid, body.title, body.category, body.note_date, body.body, admin["username"])
        await audit(c, admin["username"], "employee_note_created", "employee_note", note["id"],
                    after={"employee_id": eid, "title": body.title, "category": body.category})
    return row(note)


@router.get("/employee-notes/{note_id}/revisions")
async def employee_note_revisions(note_id: int, admin: dict = Depends(require_admin)):
    pool = await get_pool()
    if not await pool.fetchval("SELECT 1 FROM employee_notes WHERE id=$1", note_id):
        err(404, "Catatan tidak ditemukan")
    return rows(await pool.fetch("SELECT * FROM employee_note_revisions WHERE note_id=$1 ORDER BY changed_at DESC,id DESC", note_id))


@router.put("/employee-notes/{note_id}")
async def update_employee_note(note_id: int, body: EmployeeNoteIn, admin: dict = Depends(require_admin)):
    pool = await get_pool()
    async with pool.acquire() as c, c.transaction():
        before = await c.fetchrow("SELECT * FROM employee_notes WHERE id=$1 FOR UPDATE", note_id)
        if not before:
            err(404, "Catatan tidak ditemukan")
        await c.execute(
            "INSERT INTO employee_note_revisions(note_id,title,category,note_date,body,changed_by) VALUES($1,$2,$3,$4,$5,$6)",
            note_id, before["title"], before["category"], before["note_date"], before["body"], admin["username"])
        updated = await c.fetchrow(
            "UPDATE employee_notes SET title=$2,category=$3,note_date=$4,body=$5,updated_at=now() WHERE id=$1 RETURNING *",
            note_id, body.title, body.category, body.note_date, body.body)
        await audit(c, admin["username"], "employee_note_updated", "employee_note", note_id,
                    before={"title": before["title"], "category": before["category"]},
                    after={"title": body.title, "category": body.category})
    return row(updated)


async def _save_components(c, eid, comps):
    await c.execute("DELETE FROM employee_components WHERE employee_id=$1", eid)
    await c.executemany("INSERT INTO employee_components(employee_id,name,amount,volume,note) VALUES($1,$2,$3,$4,$5)",
                        [(eid, x.name, x.amount, x.volume, x.note) for x in comps])


FIELDS = ["full_name", "gender", "address", "birth_date", "ktp", "phone", "department_id", "join_date", "payroll_mode", "regular_rate", "overtime_rate"]
EMPLOYEE_AUDIT_SENSITIVE_FIELDS = {"full_name", "gender", "address", "birth_date", "ktp", "phone", "regular_rate", "overtime_rate"}


@router.post("/employees")
async def create_employee(body: EmployeeIn, admin: dict = Depends(require_admin)):
    pool = await get_pool()
    async with pool.acquire() as c, c.transaction():
        vals = [getattr(body, f) for f in FIELDS]
        try:
            e = await c.fetchrow(f"INSERT INTO employees({','.join(FIELDS)}) VALUES({','.join(f'${i+1}' for i in range(len(FIELDS)))}) RETURNING id, code", *vals)
        except asyncpg.ForeignKeyViolationError:
            err(422, "Departemen tidak valid")
        await _save_components(c, e["id"], body.components)
        await audit(c, admin["username"], "employee_created", "employee", e["id"], after={"code": e["code"]})
    return row(e)


@router.put("/employees/{eid}")
async def update_employee(eid: int, body: EmployeeIn, admin: dict = Depends(require_admin)):
    pool = await get_pool()
    async with pool.acquire() as c, c.transaction():
        before = await c.fetchrow(f"SELECT {','.join(FIELDS)} FROM employees WHERE id=$1 FOR UPDATE", eid)
        if not before:
            err(404, "Karyawan tidak ditemukan")
        sets = ",".join(f"{f}=${i+2}" for i, f in enumerate(FIELDS))
        try:
            await c.execute(f"UPDATE employees SET {sets}, updated_at=now() WHERE id=$1", eid, *[getattr(body, f) for f in FIELDS])
        except asyncpg.ForeignKeyViolationError:
            err(422, "Departemen tidak valid")
        await _save_components(c, eid, body.components)
        b = {k: str(v) if v is not None else None for k, v in dict(before).items()}
        a = {k: str(getattr(body, k)) if getattr(body, k) is not None else None for k in FIELDS}
        diff = {k for k in FIELDS if b[k] != a[k]}
        safe_diff = diff - EMPLOYEE_AUDIT_SENSITIVE_FIELDS
        await audit(c, admin["username"], "employee_updated", "employee", eid,
                    before={k: b[k] for k in safe_diff},
                    after={**{k: a[k] for k in safe_diff}, "changed_fields": sorted(diff),
                           "components": len(body.components)})
    return {"ok": True}


class ActiveIn(BaseModel):
    active: bool


@router.post("/employees/{eid}/status")
async def set_employee_status(eid: int, body: ActiveIn, admin: dict = Depends(require_admin)):
    pool = await get_pool()
    async with pool.acquire() as c:
        async with c.transaction():
            employee = await c.fetchrow("SELECT active FROM employees WHERE id=$1 FOR UPDATE", eid)
            if not employee:
                err(404, "Karyawan tidak ditemukan")
            if employee["active"] == body.active:
                return {"ok": True, "changed": False}
            await c.execute("UPDATE employees SET active=$2, updated_at=now() WHERE id=$1", eid, body.active)
            await audit(c, admin["username"], "employee_activated" if body.active else "employee_deactivated",
                        "employee", eid, before={"active": employee["active"]}, after={"active": body.active})
    return {"ok": True, "changed": True}


class NameIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)


@router.get("/departments")
async def list_departments(user: dict = Depends(current_user)):
    pool = await get_pool()
    return rows(await pool.fetch(
        "SELECT d.id, d.name, (SELECT count(*) FROM employees e WHERE e.department_id=d.id) AS employees FROM departments d ORDER BY d.name"))


@router.post("/departments")
async def create_department(body: NameIn, admin: dict = Depends(require_admin)):
    pool = await get_pool()
    try:
        async with pool.acquire() as c, c.transaction():
            r = await c.fetchrow("INSERT INTO departments(name) VALUES($1) RETURNING id, name", body.name.strip())
            await audit(c, admin["username"], "department_created", "department", r["id"], after={"name": r["name"]})
    except asyncpg.UniqueViolationError:
        err(409, "Nama departemen sudah ada")
    return row(r)


@router.put("/departments/{did}")
async def update_department(did: int, body: NameIn, admin: dict = Depends(require_admin)):
    pool = await get_pool()
    try:
        async with pool.acquire() as c, c.transaction():
            old = await c.fetchval("SELECT name FROM departments WHERE id=$1", did)
            if old is None:
                err(404, "Departemen tidak ditemukan")
            await c.execute("UPDATE departments SET name=$2 WHERE id=$1", did, body.name.strip())
            await audit(c, admin["username"], "department_updated", "department", did, before={"name": old}, after={"name": body.name})
    except asyncpg.UniqueViolationError:
        err(409, "Nama departemen sudah ada")
    return {"ok": True}


@router.delete("/departments/{did}")
async def delete_department(did: int, admin: dict = Depends(require_admin)):
    pool = await get_pool()
    async with pool.acquire() as c, c.transaction():
        if await c.fetchval("SELECT count(*) FROM employees WHERE department_id=$1", did):
            err(409, "Departemen masih dipakai karyawan")
        if (await c.execute("DELETE FROM departments WHERE id=$1", did)) == "DELETE 0":
            err(404, "Departemen tidak ditemukan")
        await audit(c, admin["username"], "department_deleted", "department", did)
    return {"ok": True}


class UserIn(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[a-z0-9_.]+$")
    full_name: str = Field(min_length=2, max_length=80)
    role: Literal["admin", "operator"]
    password: str = Field(min_length=12, max_length=128)

    @field_validator("password")
    @classmethod
    def password_byte_length(cls, value):
        if not 12 <= len(value.encode("utf-8")) <= 72:
            raise ValueError("Kata sandi harus berukuran 12-72 byte UTF-8")
        return value


class UserPatch(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=80)
    role: Optional[Literal["admin", "operator"]] = None
    active: Optional[bool] = None
    password: Optional[str] = Field(default=None, min_length=12, max_length=128)

    @field_validator("password")
    @classmethod
    def password_byte_length(cls, value):
        if value is not None and not 12 <= len(value.encode("utf-8")) <= 72:
            raise ValueError("Kata sandi harus berukuran 12-72 byte UTF-8")
        return value


@router.get("/users")
async def list_users(admin: dict = Depends(require_admin)):
    pool = await get_pool()
    return rows(await pool.fetch("SELECT id, username, full_name, role, active, created_at FROM users ORDER BY id"))


@router.post("/users")
async def create_user(body: UserIn, admin: dict = Depends(require_admin)):
    pool = await get_pool()
    try:
        async with pool.acquire() as c, c.transaction():
            r = await c.fetchrow("INSERT INTO users(username,password_hash,full_name,role) VALUES($1,$2,$3,$4) RETURNING id",
                                 body.username, hash_secret(body.password), body.full_name, body.role)
            await audit(c, admin["username"], "user_created", "user", r["id"], after={"username": body.username, "role": body.role})
    except asyncpg.UniqueViolationError:
        err(409, "Username sudah dipakai")
    return {"id": r["id"]}


@router.patch("/users/{uid}")
async def update_user(uid: int, body: UserPatch, admin: dict = Depends(require_admin)):
    pool = await get_pool()
    async with pool.acquire() as c, c.transaction():
        u = await c.fetchrow("SELECT * FROM users WHERE id=$1 FOR UPDATE", uid)
        if not u:
            err(404, "Pengguna tidak ditemukan")
        role = body.role or u["role"]
        active = u["active"] if body.active is None else body.active
        if u["role"] == "admin" and (role != "admin" or not active):
            if await c.fetchval("SELECT count(*) FROM users WHERE role='admin' AND active AND id<>$1", uid) == 0:
                err(409, "Minimal harus ada satu Administrator aktif")
        full_name = body.full_name or u["full_name"]
        changed_fields = []
        if full_name != u["full_name"]:
            changed_fields.append("full_name")
        if role != u["role"]:
            changed_fields.append("role")
        if active != u["active"]:
            changed_fields.append("active")
        if body.password:
            changed_fields.append("password")
        revoke_sessions = role != u["role"] or active != u["active"] or bool(body.password)
        await c.execute("UPDATE users SET full_name=$2, role=$3, active=$4, password_hash=$5, "
                        "session_version=session_version + CASE WHEN $6 THEN 1 ELSE 0 END WHERE id=$1", uid,
                        full_name, role, active,
                        hash_secret(body.password) if body.password else u["password_hash"], revoke_sessions)
        await audit(c, admin["username"], "user_updated", "user", uid,
                    before={"role": u["role"], "active": u["active"], "changed_fields": changed_fields},
                    after={"role": role, "active": active, "changed_fields": changed_fields,
                           "sessions_revoked": revoke_sessions})
    return {"ok": True}


class BreakIn(BaseModel):
    start: str = Field(pattern=r"^\d{2}:\d{2}$")
    end: str = Field(pattern=r"^\d{2}:\d{2}$")

    @field_validator("start", "end")
    @classmethod
    def valid_break_time(cls, value):
        try:
            h, m = map(int, value.split(":"))
            time(h, m)
        except (ValueError, AttributeError):
            raise ValueError("Jam istirahat harus berupa waktu valid dengan format HH:MM")
        return value


class SettingsIn(BaseModel):
    company_name: str = Field(min_length=1, max_length=120)
    company_address: str = Field(default="", max_length=300)
    work_days: list[int] = Field(min_length=1, max_length=7)
    start_time: str = Field(pattern=r"^\d{2}:\d{2}$")
    end_time: str = Field(pattern=r"^\d{2}:\d{2}$")
    breaks: list[BreakIn] = Field(max_length=20)
    late_tolerance_minutes: int = Field(ge=0, le=240)
    first_hour_rule: bool
    rounding_threshold_minutes: int = Field(ge=1, le=60)
    max_regular_minutes: int = Field(ge=60, le=1440)
    early_leave_requires_pin: bool
    early_pin_ttl_minutes: int = Field(ge=1, le=120)
    overtime_enabled: bool
    overtime_break_minutes: int = Field(ge=0, le=240)
    overtime_break_after_minutes: int = Field(ge=0, le=1440)
    kiosk_enabled: bool
    payroll_start_date: date

    @field_validator("start_time", "end_time")
    @classmethod
    def valid_schedule_time(cls, value):
        try:
            h, m = map(int, value.split(":"))
            time(h, m)
        except (ValueError, AttributeError):
            raise ValueError("Jam kerja harus berupa waktu valid dengan format HH:MM")
        return value

    @field_validator("company_name")
    @classmethod
    def nonblank_company_name(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Nama perusahaan wajib diisi")
        return value

    @model_validator(mode="after")
    def validate_schedule_ranges(self):
        if len(set(self.work_days)) != len(self.work_days) or any(day < 1 or day > 7 for day in self.work_days):
            raise ValueError("Hari kerja harus unik dan berada pada rentang 1-7")

        def minute(value):
            hour, mins = map(int, value.split(":"))
            return hour * 60 + mins

        start = minute(self.start_time)
        end = minute(self.end_time)
        if start == end:
            raise ValueError("Jam mulai dan selesai tidak boleh sama")
        if end <= start:
            end += 24 * 60
        for item in self.breaks:
            break_start = minute(item.start)
            break_end = minute(item.end)
            if break_end <= break_start:
                break_end += 24 * 60
            if break_start < start:
                break_start += 24 * 60
                break_end += 24 * 60
            if break_start < start or break_end > end:
                raise ValueError("Jam istirahat harus berada di dalam jadwal kerja")
        return self


HIDDEN = ("overtime_pin_hash", "ot_pin_attempts_by_source", "ot_pin_failures", "ot_pin_locked_until")


@router.get("/settings")
async def read_settings(admin: dict = Depends(require_admin)):
    pool = await get_pool()
    async with pool.acquire() as c:
        cfg = await get_settings(c)
        locked = await c.fetchval("SELECT count(*) FROM payroll_periods") > 0
    return {**{k: v for k, v in cfg.items() if k not in HIDDEN}, "has_overtime_pin": bool(cfg.get("overtime_pin_hash")),
            "payroll_start_locked": locked}


async def _update_settings(c, admin, patch: dict, action: str):
    async with c.transaction():
        cfg = await c.fetchval("SELECT value FROM settings WHERE key='app' FOR UPDATE")
        changed = [k for k, v in patch.items() if cfg.get(k) != v]
        before = {k: (cfg.get(k) if k not in HIDDEN and k != "kiosk_token" else "***") for k in changed}
        cfg.update(patch)
        await c.execute("UPDATE settings SET value=$1 WHERE key='app'", cfg)
        invalidate_settings()
        after = {k: (patch[k] if k not in HIDDEN and k != "kiosk_token" else "***") for k in changed}
        await audit(c, admin["username"], action, "settings", "app", before=before, after=after)


@router.put("/settings")
async def write_settings(body: SettingsIn, admin: dict = Depends(require_admin)):
    pool = await get_pool()
    data = body.model_dump()
    data["payroll_start_date"] = body.payroll_start_date.isoformat()
    async with pool.acquire() as c:
        if await c.fetchval("SELECT count(*) FROM payroll_periods"):
            data.pop("payroll_start_date")
        await _update_settings(c, admin, data, "settings_updated")
    return {"ok": True}


class PinIn(BaseModel):
    pin: str = Field(pattern=r"^\d{6}$")


@router.post("/settings/overtime-pin")
async def set_overtime_pin(body: PinIn, admin: dict = Depends(require_admin)):
    pool = await get_pool()
    async with pool.acquire() as c:
        await _update_settings(c, admin, {"overtime_pin_hash": hash_secret(body.pin)}, "overtime_pin_changed")
    return {"ok": True}


@router.post("/settings/kiosk-rotate")
async def rotate_kiosk(admin: dict = Depends(require_admin)):
    pool = await get_pool()
    token = secrets.token_urlsafe(24)
    async with pool.acquire() as c:
        await _update_settings(c, admin, {"kiosk_token": token}, "kiosk_token_rotated")
    return {"kiosk_token": token}


@router.get("/audit")
async def list_audit(entity: str = "", limit: int = Query(100, le=500), admin: dict = Depends(require_admin)):
    pool = await get_pool()
    records = await pool.fetch(
        "SELECT * FROM audit_logs WHERE ($1='' OR entity=$1) ORDER BY id DESC LIMIT $2", entity, limit)
    result = []
    for record in records:
        item = row(record)
        if item["entity"] == "employee":
            for key in ("before", "after"):
                payload = item.get(key)
                if not isinstance(payload, dict):
                    item[key] = None
                    continue
                safe = {field: payload[field] for field in ("code", "department_id", "join_date", "payroll_mode") if field in payload}
                changed = payload.get("changed_fields")
                if isinstance(changed, list):
                    safe["changed_fields"] = sorted(str(field) for field in changed)
                components = payload.get("components")
                if isinstance(components, int):
                    safe["components"] = components
                elif isinstance(components, (list, tuple)):
                    safe["components"] = len(components)
                item[key] = safe or None
        result.append(item)
    return result


class KasbonIn(BaseModel):
    employee_id: int
    amount: int = Field(gt=0, le=1_000_000_000)
    note: Optional[str] = Field(default=None, max_length=200)


@router.get("/kasbon")
async def kasbon_summary(admin: dict = Depends(require_admin)):
    pool = await get_pool()
    return rows(await pool.fetch(
        "SELECT e.id AS employee_id, e.code, e.full_name, e.active, "
        "coalesce(sum(CASE WHEN c.kind='grant' THEN c.amount END),0) AS total_grant, "
        "coalesce(sum(CASE WHEN c.kind='deduction' THEN c.amount END),0) AS total_deduction, "
        "coalesce(sum(CASE WHEN c.kind='reversal' THEN c.amount END),0) AS total_reversal, "
        "coalesce(sum(CASE WHEN c.kind='deduction' THEN -c.amount ELSE c.amount END),0) AS balance "
        "FROM employees e JOIN cash_advances c ON c.employee_id=e.id GROUP BY e.id ORDER BY e.code"))


@router.get("/kasbon/report.pdf")
async def kasbon_report_pdf(admin: dict = Depends(require_admin)):
    pool = await get_pool()
    async with pool.acquire() as c:
        summary = await c.fetch(
            "SELECT e.id AS employee_id, e.code, e.full_name, "
            "coalesce(sum(c.amount) FILTER (WHERE c.kind='grant'),0) AS total_grant, "
            "coalesce(sum(c.amount) FILTER (WHERE c.kind='deduction'),0) AS total_deduction, "
            "coalesce(sum(c.amount) FILTER (WHERE c.kind='reversal'),0) AS total_reversal, "
            "coalesce(sum(CASE WHEN c.kind='deduction' THEN -c.amount ELSE c.amount END),0) AS balance "
            "FROM employees e JOIN cash_advances c ON c.employee_id=e.id GROUP BY e.id ORDER BY e.code")
        ledger = await c.fetch(
            "SELECT e.id AS employee_id, e.code, e.full_name, c.kind, c.amount, c.tx_date, c.period_id, "
            "c.created_by, p.start_date, p.end_date FROM cash_advances c "
            "JOIN employees e ON e.id=c.employee_id LEFT JOIN payroll_periods p ON p.id=c.period_id "
            "ORDER BY e.code, c.tx_date, c.id")
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    from xml.sax.saxutils import escape

    labels = {"grant": "Pemberian", "deduction": "Potongan payroll", "reversal": "Pembatalan potongan"}
    rupiah_text = lambda value: "Rp " + f"{int(value):,}".replace(",", ".")
    totals = {key: sum(int(r[field]) for r in summary) for key, field in {
        "grant": "total_grant", "deduction": "total_deduction", "reversal": "total_reversal", "balance": "balance"}.items()}
    styles = getSampleStyleSheet()
    title = styles["Title"].clone("kasbon-report-title", textColor=colors.HexColor("#0B1F3A"), fontSize=15,
                                    alignment=0, spaceAfter=3)
    story = [Paragraph("Rekap Kasbon", title),
             Paragraph(f"Dicetak {today_wib():%d/%m/%Y} WIB · {len(summary)} karyawan memiliki transaksi", styles["Normal"]),
             Spacer(1, 4 * mm), Paragraph("Ringkasan saldo", styles["Heading3"])]
    summary_data = [["Karyawan", "Diberikan", "Dipotong", "Pembatalan", "Saldo"]]
    if not summary:
        summary_data.append(["Belum ada transaksi", "", "", "", ""])
    for employee in summary:
        summary_data.append([f"{escape(employee['code'])} — {escape(employee['full_name'])}",
                             rupiah_text(employee["total_grant"]), rupiah_text(employee["total_deduction"]),
                             rupiah_text(employee["total_reversal"]), rupiah_text(employee["balance"])])
    summary_data.append(["TOTAL", rupiah_text(totals["grant"]), rupiah_text(totals["deduction"]),
                         rupiah_text(totals["reversal"]), rupiah_text(totals["balance"])])
    summary_table = Table(summary_data, colWidths=[82 * mm, 38 * mm, 38 * mm, 38 * mm, 38 * mm], repeatRows=1)
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#174EA6")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8), ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D9E2EF")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#F4F7FB")]),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#EAF0FB")),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story += [summary_table, Spacer(1, 5 * mm), Paragraph("Rincian transaksi", styles["Heading3"])]
    detail = [["Tanggal", "ID", "Nama", "Jenis", "Periode tutup buku", "Transaksi", "Saldo setelah", "Oleh"]]
    if not ledger:
        detail.append(["—", "", "", "Belum ada transaksi", "", "", "", ""])
    running = {}
    for tx in ledger:
        delta = -int(tx["amount"]) if tx["kind"] == "deduction" else int(tx["amount"])
        running[tx["employee_id"]] = running.get(tx["employee_id"], 0) + delta
        period = f"{tx['start_date']:%d/%m/%Y}–{tx['end_date']:%d/%m/%Y}" if tx["start_date"] else "—"
        signed = ("−" if delta < 0 else "+") + rupiah_text(abs(delta))
        detail.append([tx["tx_date"].strftime("%d/%m/%Y"), escape(tx["code"]), escape(tx["full_name"]),
                       labels.get(tx["kind"], tx["kind"]), period, signed,
                       rupiah_text(running[tx["employee_id"]]), escape(tx["created_by"])])
    detail_table = Table(detail, colWidths=[22 * mm, 19 * mm, 48 * mm, 34 * mm, 42 * mm, 30 * mm, 31 * mm, 23 * mm], repeatRows=1)
    detail_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#174EA6")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D9E2EF")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F7FB")]),
        ("ALIGN", (5, 1), (6, -1), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    buffer = io.BytesIO()
    SimpleDocTemplate(buffer, pagesize=landscape(A4), leftMargin=10 * mm, rightMargin=10 * mm,
                      topMargin=10 * mm, bottomMargin=10 * mm).build(story + [detail_table])
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/pdf",
                             headers={"Content-Disposition": 'attachment; filename="rekap-kasbon.pdf"'})


@router.get("/kasbon/{eid}")
async def kasbon_ledger(eid: int, admin: dict = Depends(require_admin)):
    pool = await get_pool()
    return rows(await pool.fetch(
        "SELECT c.*, p.start_date, p.end_date FROM cash_advances c LEFT JOIN payroll_periods p ON p.id=c.period_id "
        "WHERE c.employee_id=$1 ORDER BY c.id DESC", eid))


@router.post("/kasbon")
async def kasbon_grant(body: KasbonIn, admin: dict = Depends(require_admin)):
    pool = await get_pool()
    async with pool.acquire() as c, c.transaction():
        if not await c.fetchval("SELECT 1 FROM employees WHERE id=$1", body.employee_id):
            err(404, "Karyawan tidak ditemukan")
        r = await c.fetchrow("INSERT INTO cash_advances(employee_id, kind, amount, tx_date, note, created_by) VALUES($1,'grant',$2,$3,$4,$5) RETURNING id",
                             body.employee_id, body.amount, today_wib(), body.note, admin["username"])
        await audit(c, admin["username"], "kasbon_granted", "cash_advance", r["id"], after={"employee_id": body.employee_id, "amount": body.amount})
    return {"id": r["id"]}
