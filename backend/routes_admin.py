import secrets
from datetime import date
from typing import Literal, Optional

import asyncpg
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field, field_validator

from core import get_pool, err, audit, rows, row, today_wib, get_settings, invalidate_settings
from schema import hash_secret
from security import current_user, require_admin, forget_user

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
                "SELECT coalesce(sum(CASE WHEN kind='grant' THEN amount ELSE -amount END),0) FROM cash_advances")
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
        "SELECT coalesce(sum(CASE WHEN kind='grant' THEN amount ELSE -amount END),0) FROM cash_advances WHERE employee_id=$1", eid)
    return out


async def _save_components(c, eid, comps):
    await c.execute("DELETE FROM employee_components WHERE employee_id=$1", eid)
    await c.executemany("INSERT INTO employee_components(employee_id,name,amount,volume,note) VALUES($1,$2,$3,$4,$5)",
                        [(eid, x.name, x.amount, x.volume, x.note) for x in comps])


FIELDS = ["full_name", "gender", "address", "birth_date", "ktp", "phone", "department_id", "join_date", "payroll_mode", "regular_rate", "overtime_rate"]


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
        await audit(c, admin["username"], "employee_created", "employee", e["id"], after={"code": e["code"], "name": body.full_name})
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
        await audit(c, admin["username"], "employee_updated", "employee", eid,
                    before={k: b[k] for k in diff}, after={**{k: a[k] for k in diff}, "components": len(body.components)})
    return {"ok": True}


class ActiveIn(BaseModel):
    active: bool


@router.post("/employees/{eid}/status")
async def set_employee_status(eid: int, body: ActiveIn, admin: dict = Depends(require_admin)):
    pool = await get_pool()
    async with pool.acquire() as c:
        r = await c.fetchrow("UPDATE employees SET active=$2, updated_at=now() WHERE id=$1 RETURNING code", eid, body.active)
        if not r:
            err(404, "Karyawan tidak ditemukan")
        await audit(c, admin["username"], "employee_activated" if body.active else "employee_deactivated", "employee", eid)
    return {"ok": True}


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
        async with pool.acquire() as c:
            r = await c.fetchrow("INSERT INTO departments(name) VALUES($1) RETURNING id, name", body.name.strip())
            await audit(c, admin["username"], "department_created", "department", r["id"], after={"name": r["name"]})
    except asyncpg.UniqueViolationError:
        err(409, "Nama departemen sudah ada")
    return row(r)


@router.put("/departments/{did}")
async def update_department(did: int, body: NameIn, admin: dict = Depends(require_admin)):
    pool = await get_pool()
    try:
        async with pool.acquire() as c:
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
    async with pool.acquire() as c:
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
    password: str = Field(min_length=8, max_length=128)


class UserPatch(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=80)
    role: Optional[Literal["admin", "operator"]] = None
    active: Optional[bool] = None
    password: Optional[str] = Field(default=None, min_length=8, max_length=128)


@router.get("/users")
async def list_users(admin: dict = Depends(require_admin)):
    pool = await get_pool()
    return rows(await pool.fetch("SELECT id, username, full_name, role, active, created_at FROM users ORDER BY id"))


@router.post("/users")
async def create_user(body: UserIn, admin: dict = Depends(require_admin)):
    pool = await get_pool()
    try:
        async with pool.acquire() as c:
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
        await c.execute("UPDATE users SET full_name=$2, role=$3, active=$4, password_hash=$5 WHERE id=$1", uid,
                        body.full_name or u["full_name"], role, active,
                        hash_secret(body.password) if body.password else u["password_hash"])
        forget_user(uid)
        await audit(c, admin["username"], "user_updated", "user", uid, before={"role": u["role"], "active": u["active"]},
                    after={"role": role, "active": active, "password_reset": bool(body.password)})
    return {"ok": True}


class BreakIn(BaseModel):
    start: str = Field(pattern=r"^\d{2}:\d{2}$")
    end: str = Field(pattern=r"^\d{2}:\d{2}$")


class SettingsIn(BaseModel):
    company_name: str = Field(min_length=1, max_length=120)
    company_address: str = Field(default="", max_length=300)
    work_days: list[int]
    start_time: str = Field(pattern=r"^\d{2}:\d{2}$")
    end_time: str = Field(pattern=r"^\d{2}:\d{2}$")
    breaks: list[BreakIn]
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


HIDDEN = ("overtime_pin_hash",)


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
    return rows(await pool.fetch(
        "SELECT * FROM audit_logs WHERE ($1='' OR entity=$1) ORDER BY id DESC LIMIT $2", entity, limit))


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
        "coalesce(sum(CASE WHEN c.kind='grant' THEN c.amount ELSE -c.amount END),0) AS balance "
        "FROM employees e JOIN cash_advances c ON c.employee_id=e.id GROUP BY e.id ORDER BY e.code"))


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
