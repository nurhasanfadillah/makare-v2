"""Pure payroll business rules (no I/O)."""
from datetime import datetime, date, time, timedelta
from zoneinfo import ZoneInfo

WIB = ZoneInfo("Asia/Jakarta")


def _at(d: date, hm: str) -> datetime:
    h, m = map(int, hm.split(":"))
    return datetime.combine(d, time(h, m), tzinfo=WIB)


def mins(a: datetime, b: datetime) -> int:
    return int((b - a).total_seconds() // 60)


def overlap(a1, a2, b1, b2) -> int:
    return max(0, mins(max(a1, b1), min(a2, b2)))


def schedule_bounds(work_date: date, cfg: dict):
    s, e = _at(work_date, cfg["start_time"]), _at(work_date, cfg["end_time"])
    if e <= s:
        e += timedelta(days=1)
    return s, e


def break_windows(work_date: date, cfg: dict):
    s, _ = schedule_bounds(work_date, cfg)
    out = []
    for b in cfg.get("breaks", []):
        bs, be = _at(work_date, b["start"]), _at(work_date, b["end"])
        if bs < s:
            bs, be = bs + timedelta(days=1), be + timedelta(days=1)
        if be <= bs:
            be += timedelta(days=1)
        out.append((bs, be))
    return out


def round_minutes(m: int, threshold: int = 30) -> int:
    h, r = divmod(max(0, m), 60)
    return (h + (1 if r >= threshold else 0)) * 60


def compute_regular(check_in: datetime, check_out, work_date: date, cfg: dict) -> dict:
    s, e = schedule_bounds(work_date, cfg)
    late = max(0, mins(s, check_in))
    r = {
        "late_minutes": late, "is_late": late > 0, "first_hour_forfeited": False,
        "raw_minutes": 0, "break_minutes": 0, "late_adjustment_minutes": 0,
        "eligible_minutes": 0, "rounded_minutes": 0, "paid_minutes": 0,
        "early_leave": False, "incomplete": check_out is None,
    }
    if check_out is None:
        return r
    r["raw_minutes"] = max(0, mins(check_in, check_out))
    r["early_leave"] = check_out < e
    actual_start = max(check_in, s)
    forfeited = False
    if cfg.get("first_hour_rule", True):
        if late <= cfg["late_tolerance_minutes"]:
            win_start = s
        else:
            win_start = max(check_in, s + timedelta(hours=1))
            forfeited = True
    else:
        win_start = actual_start
    win_end = min(check_out, e)
    r["first_hour_forfeited"] = forfeited
    if win_end <= win_start:
        if forfeited:
            r["late_adjustment_minutes"] = -max(0, overlap(actual_start, check_out, actual_start, win_start))
        return r
    r["late_adjustment_minutes"] = mins(win_start, actual_start) if not forfeited else -mins(actual_start, win_start)
    brk = sum(overlap(win_start, win_end, bs, be) for bs, be in break_windows(work_date, cfg))
    eligible = max(0, mins(win_start, win_end) - brk)
    rounded = round_minutes(eligible, cfg["rounding_threshold_minutes"])
    paid = rounded
    if forfeited:
        max_possible = mins(win_start, e) - sum(overlap(win_start, e, bs, be) for bs, be in break_windows(work_date, cfg))
        paid = min(paid, (max(0, max_possible) // 60) * 60)
    cap = cfg.get("max_regular_minutes")
    if cap:
        paid = min(paid, int(cap))
    r.update(break_minutes=brk, eligible_minutes=eligible, rounded_minutes=rounded, paid_minutes=paid)
    return r


def compute_overtime(check_in: datetime, check_out, cfg: dict) -> dict:
    if check_out is None:
        return {"raw_minutes": 0, "break_minutes": 0, "paid_minutes": 0, "incomplete": True}
    raw = max(0, mins(check_in, check_out))
    brk = int(cfg.get("overtime_break_minutes", 0)) if raw >= int(cfg.get("overtime_break_after_minutes", 0) or 0) else 0
    brk = min(brk, raw)
    return {"raw_minutes": raw, "break_minutes": brk, "paid_minutes": raw - brk, "incomplete": False}


def kasbon_cap(balance: int, net_before: int) -> int:
    return min(max(0, balance), max(0, net_before))


def compute_pay(mode: str, regular_rate: int, overtime_rate: int, paid_minutes: int, ot_minutes: int,
                components: list, other_deduction: int, kasbon_balance: int, kasbon_override=None) -> dict:
    comp_total = int(round(sum(c["amount"] * float(c["volume"]) for c in components)))
    if mode == "hourly":
        regular_amount = int(round(regular_rate * paid_minutes / 60))
        ot_amount = int(round(overtime_rate * ot_minutes / 60))
    else:
        regular_amount, ot_amount = 0, 0
    gross = regular_amount + ot_amount + comp_total
    if other_deduction < 0 or other_deduction > gross:
        raise ValueError("Potongan lain tidak boleh negatif atau melebihi gaji kotor")
    net_before = gross - other_deduction
    cap = kasbon_cap(kasbon_balance, net_before)
    kasbon = cap if kasbon_override is None else int(kasbon_override)
    if kasbon < 0 or kasbon > cap:
        raise ValueError(f"Potongan kasbon harus antara 0 dan {cap}")
    return {
        "regular_amount": regular_amount, "overtime_amount": ot_amount, "components_total": comp_total,
        "gross": gross, "other_deduction": other_deduction, "net_before_kasbon": net_before,
        "kasbon_balance": kasbon_balance, "kasbon_cap": cap, "kasbon_deduction": kasbon,
        "kasbon_after": kasbon_balance - kasbon, "net_final": net_before - kasbon,
    }
