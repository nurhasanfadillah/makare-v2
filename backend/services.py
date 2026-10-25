import secrets
from datetime import date, timedelta
from collections import defaultdict

import asyncpg

from core import now_wib, today_wib, err, audit, get_settings, last_closed_end, ensure_open_date
from rules import compute_regular, compute_overtime, compute_pay, schedule_bounds
from schema import hash_secret
from security import verify_secret


async def employee_state(conn, employee_id: int) -> dict:
    today = today_wib()
    reg = await conn.fetchrow(
        "SELECT id, status, check_in, check_out, work_date FROM attendance WHERE employee_id=$1 AND "
        "(work_date=$2 OR (status='hadir' AND check_out IS NULL)) ORDER BY work_date DESC LIMIT 1", employee_id, today)
    ot_open = await conn.fetchval("SELECT id FROM overtime_sessions WHERE employee_id=$1 AND check_out IS NULL", employee_id)
    if reg is None:
        regular = "none"
    elif reg["status"] != "hadir":
        regular = "status_" + reg["status"]
    elif reg["check_out"] is None:
        regular = "open"
    else:
        regular = "done"
    return {"regular": regular, "overtime": "open" if ot_open else "none",
            "regular_check_in": reg["check_in"].isoformat() if reg and reg["check_in"] else None}


async def clock(conn, employee_id: int, mode: str, action: str, actor: str, source: str, early_pin: str | None = None):
    emp = await conn.fetchrow("SELECT id, code, full_name, active, payroll_mode FROM employees WHERE id=$1", employee_id)
    if not emp:
        err(404, "Karyawan tidak ditemukan")
    if not emp["active"]:
        err(409, "Karyawan nonaktif tidak dapat melakukan absensi")
    if source == "kiosk" and emp["payroll_mode"] != "hourly":
        err(403, "Karyawan ini tidak menggunakan absensi kiosk")
    cfg = await get_settings(conn)
    now = now_wib()
    today = now.date()
    await ensure_open_date(conn, today)
    async with conn.transaction():
        await conn.execute("SELECT pg_advisory_xact_lock(1001, $1)", employee_id)
        if mode == "overtime":
            if not cfg.get("overtime_enabled"):
                err(403, "Fitur lembur sedang nonaktif")
            if action == "in":
                if await conn.fetchval("SELECT 1 FROM attendance WHERE employee_id=$1 AND status='hadir' AND check_out IS NULL", employee_id):
                    err(409, "Tutup sesi reguler terlebih dahulu sebelum Masuk lembur")
                try:
                    rec = await conn.fetchrow(
                        "INSERT INTO overtime_sessions(employee_id, work_date, check_in, source, created_by) VALUES($1,$2,$3,$4,$5) RETURNING id, check_in",
                        employee_id, today, now, source, actor)
                except asyncpg.UniqueViolationError:
                    err(409, "Sesi lembur masih terbuka")
            else:
                rec = await conn.fetchrow(
                    "UPDATE overtime_sessions SET check_out=$2 WHERE employee_id=$1 AND check_out IS NULL RETURNING id, check_in, check_out",
                    employee_id, now)
                if not rec:
                    err(409, "Belum ada Masuk lembur yang terbuka")
            entity = "overtime"
        else:
            if action == "in":
                try:
                    rec = await conn.fetchrow(
                        "INSERT INTO attendance(employee_id, work_date, status, check_in, source, created_by) VALUES($1,$2,'hadir',$3,$4,$5) "
                        "ON CONFLICT (employee_id, work_date) DO NOTHING RETURNING id, check_in", employee_id, today, now, source, actor)
                except asyncpg.UniqueViolationError:
                    err(409, "Masih ada sesi Masuk yang belum ditutup")
                if not rec:
                    err(409, "Absensi hari ini sudah tercatat")
            else:
                open_row = await conn.fetchrow(
                    "SELECT id, work_date, check_in FROM attendance WHERE employee_id=$1 AND status='hadir' AND check_out IS NULL FOR UPDATE", employee_id)
                if not open_row:
                    err(409, "Belum ada Masuk yang valid")
                _, sched_end = schedule_bounds(open_row["work_date"], cfg)
                early = now < sched_end
                if early and cfg.get("early_leave_requires_pin", True):
                    if not early_pin:
                        err(428, "Keluar lebih awal membutuhkan PIN dari Administrator")
                    pin = await conn.fetchrow(
                        "SELECT id, pin_hash, attempts FROM early_leave_pins WHERE attendance_id=$1 AND used_at IS NULL AND expires_at > now() "
                        "ORDER BY id DESC LIMIT 1 FOR UPDATE", open_row["id"])
                    if not pin or pin["attempts"] >= 5:
                        err(403, "PIN tidak tersedia atau sudah kedaluwarsa")
                    if not verify_secret(early_pin, pin["pin_hash"]):
                        await conn.execute("UPDATE early_leave_pins SET attempts=attempts+1 WHERE id=$1", pin["id"])
                        await audit(conn, actor, "early_pin_failed", "attendance", open_row["id"], result="failed")
                        return {"error": "PIN salah"}
                    await conn.execute("UPDATE early_leave_pins SET used_at=now() WHERE id=$1", pin["id"])
                rec = await conn.fetchrow(
                    "UPDATE attendance SET check_out=$2, early_leave=$3 WHERE id=$1 AND check_out IS NULL RETURNING id, check_in, check_out",
                    open_row["id"], now, early)
                if not rec:
                    err(409, "Sesi sudah ditutup")
            entity = "attendance"
        await audit(conn, actor, f"{mode}_{action}", entity, rec["id"], after={"employee": emp["code"], "source": source})
    return {"ok": True, "employee": {"id": emp["id"], "code": emp["code"], "full_name": emp["full_name"]},
            "mode": mode, "action": action, "time": now.isoformat()}


async def create_early_pin(conn, attendance_id: int, actor: str) -> dict:
    cfg = await get_settings(conn)
    a = await conn.fetchrow("SELECT id FROM attendance WHERE id=$1 AND status='hadir' AND check_out IS NULL", attendance_id)
    if not a:
        err(409, "PIN hanya untuk sesi Masuk yang masih terbuka")
    pin = f"{secrets.randbelow(10**6):06d}"
    ttl = int(cfg.get("early_pin_ttl_minutes", 15))
    expires = now_wib() + timedelta(minutes=ttl)
    async with conn.transaction():
        await conn.execute("UPDATE early_leave_pins SET used_at=now() WHERE attendance_id=$1 AND used_at IS NULL", attendance_id)
        await conn.execute("INSERT INTO early_leave_pins(attendance_id, pin_hash, expires_at, created_by) VALUES($1,$2,$3,$4)",
                           attendance_id, hash_secret(pin), expires, actor)
        await audit(conn, actor, "early_pin_created", "attendance", attendance_id)
    return {"pin": pin, "expires_at": expires.isoformat()}


async def next_period(conn) -> dict:
    cfg = await get_settings(conn)
    end = await last_closed_end(conn)
    start = end + timedelta(days=1) if end else date.fromisoformat(cfg["payroll_start_date"])
    return {"start_date": start.isoformat(), "max_end_date": today_wib().isoformat()}


async def build_payroll(conn, start: date, end: date, overrides: dict | None = None) -> dict:
    overrides = overrides or {}
    cfg = await get_settings(conn)
    emps = await conn.fetch(
        "SELECT e.*, d.name AS department FROM employees e LEFT JOIN departments d ON d.id=e.department_id "
        "WHERE e.active OR e.id IN (SELECT employee_id FROM attendance WHERE work_date BETWEEN $1 AND $2) "
        "OR e.id IN (SELECT employee_id FROM overtime_sessions WHERE work_date BETWEEN $1 AND $2) ORDER BY e.code", start, end)
    comps, atts, ots = defaultdict(list), defaultdict(list), defaultdict(list)
    for c in await conn.fetch("SELECT * FROM employee_components ORDER BY id"):
        comps[c["employee_id"]].append({"name": c["name"], "amount": c["amount"], "volume": float(c["volume"]), "note": c["note"]})
    for a in await conn.fetch("SELECT * FROM attendance WHERE work_date BETWEEN $1 AND $2 ORDER BY work_date", start, end):
        atts[a["employee_id"]].append(a)
    for o in await conn.fetch("SELECT * FROM overtime_sessions WHERE work_date BETWEEN $1 AND $2 ORDER BY check_in", start, end):
        ots[o["employee_id"]].append(o)
    balances = {r["employee_id"]: r["bal"] for r in await conn.fetch(
        "SELECT employee_id, sum(CASE WHEN kind='grant' THEN amount ELSE -amount END) AS bal FROM cash_advances GROUP BY employee_id")}
    keys = ["raw_minutes", "break_minutes", "late_adjustment_minutes", "eligible_minutes", "rounded_minutes", "paid_minutes"]
    out, totals = [], defaultdict(int)
    for e in emps:
        eid = e["id"]
        sessions, sums = [], dict.fromkeys(keys, 0)
        counts = {"hadir": 0, "sakit": 0, "izin": 0, "alfa": 0, "late": 0, "forfeited": 0, "incomplete": 0}
        for a in atts[eid]:
            counts[a["status"]] += 1
            s = {"date": a["work_date"].isoformat(), "status": a["status"],
                 "check_in": a["check_in"].isoformat() if a["check_in"] else None,
                 "check_out": a["check_out"].isoformat() if a["check_out"] else None}
            if a["status"] == "hadir" and a["check_in"]:
                c = compute_regular(a["check_in"], a["check_out"], a["work_date"], cfg)
                s.update(c)
                for k in keys:
                    sums[k] += c[k]
                counts["late"] += int(c["is_late"])
                counts["forfeited"] += int(c["first_hour_forfeited"])
                counts["incomplete"] += int(c["incomplete"])
            sessions.append(s)
        ot_sessions, ot_min = [], 0
        for o in ots[eid]:
            c = compute_overtime(o["check_in"], o["check_out"], cfg)
            ot_min += c["paid_minutes"]
            ot_sessions.append({"date": o["work_date"].isoformat(), "check_in": o["check_in"].isoformat(),
                                "check_out": o["check_out"].isoformat() if o["check_out"] else None, **c})
        ov = overrides.get(str(eid), {})
        try:
            pay = compute_pay(e["payroll_mode"], e["regular_rate"], e["overtime_rate"], sums["paid_minutes"], ot_min,
                              comps[eid], int(ov.get("other_deduction") or 0), int(balances.get(eid, 0) or 0), ov.get("kasbon_deduction"))
        except ValueError as ex:
            err(422, f"{e['code']} {e['full_name']}: {ex}")
        line = {"employee_id": eid, "code": e["code"], "full_name": e["full_name"], "department": e["department"],
                "payroll_mode": e["payroll_mode"], "regular_rate": e["regular_rate"], "overtime_rate": e["overtime_rate"],
                "components": comps[eid], "counts": counts, "durations": sums, "overtime_minutes": ot_min,
                "sessions": sessions, "overtime_sessions": ot_sessions, **pay}
        for k in ["gross", "net_before_kasbon", "kasbon_deduction", "net_final", "other_deduction"]:
            totals[k] += pay[k]
        out.append(line)
    totals["employees"] = len(out)
    return {"start_date": start.isoformat(), "end_date": end.isoformat(), "lines": out, "totals": dict(totals)}


async def finalize_closing(conn, end: date, idem_key: str, overrides: dict, actor: str) -> dict:
    async with conn.transaction():
        await conn.execute("SELECT pg_advisory_xact_lock(2002)")
        existing = await conn.fetchrow("SELECT id FROM payroll_periods WHERE idempotency_key=$1", idem_key)
        if existing:
            return {"period_id": existing["id"], "duplicate": True}
        nxt = await next_period(conn)
        start = date.fromisoformat(nxt["start_date"])
        if end < start or end > today_wib():
            err(422, "Tanggal akhir tidak valid")
        data = await build_payroll(conn, start, end, overrides)
        cfg = await get_settings(conn)
        cfg_snap = {k: v for k, v in cfg.items() if k not in ("kiosk_token", "overtime_pin_hash")}
        pid = await conn.fetchval(
            "INSERT INTO payroll_periods(start_date, end_date, idempotency_key, totals, settings_snapshot, closed_by) "
            "VALUES($1,$2,$3,$4,$5,$6) RETURNING id", start, end, idem_key, data["totals"], cfg_snap, actor)
        await conn.executemany(
            "INSERT INTO payroll_snapshots(period_id, employee_id, data, gross, net_before_kasbon, kasbon_deduction, net_final) "
            "VALUES($1,$2,$3,$4,$5,$6,$7)",
            [(pid, ln["employee_id"], ln, ln["gross"], ln["net_before_kasbon"], ln["kasbon_deduction"], ln["net_final"]) for ln in data["lines"]])
        await conn.executemany(
            "INSERT INTO cash_advances(employee_id, kind, amount, tx_date, note, period_id, created_by) VALUES($1,'deduction',$2,$3,$4,$5,$6)",
            [(ln["employee_id"], ln["kasbon_deduction"], end, f"Potongan payroll {start}–{end}", pid, actor)
             for ln in data["lines"] if ln["kasbon_deduction"] > 0])
        await audit(conn, actor, "closing_finalized", "payroll_period", pid, after={"start": str(start), "end": str(end), **data["totals"]})
    return {"period_id": pid, "duplicate": False}
