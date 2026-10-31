"""Pure payroll business rules (no I/O)."""
from datetime import datetime, date, time, timedelta
from decimal import Decimal, ROUND_HALF_EVEN
from zoneinfo import ZoneInfo

WIB = ZoneInfo("Asia/Jakarta")


def _at(d: date, hm: str) -> datetime:
    h, m = map(int, hm.split(":"))
    return datetime.combine(d, time(h, m), tzinfo=WIB)


def mins(a: datetime, b: datetime) -> int:
    return int((b - a).total_seconds() // 60)


def overlap(a1, a2, b1, b2) -> int:
    return max(0, mins(max(a1, b1), min(a2, b2)))


def overlap_total(start, end, windows) -> int:
    clipped = sorted((max(start, a), min(end, b)) for a, b in windows if min(end, b) > max(start, a))
    if not clipped:
        return 0
    total = 0
    current_start, current_end = clipped[0]
    for next_start, next_end in clipped[1:]:
        if next_start <= current_end:
            current_end = max(current_end, next_end)
        else:
            total += mins(current_start, current_end)
            current_start, current_end = next_start, next_end
    return total + mins(current_start, current_end)


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


def recognize_full_hours(eligible_minutes: int, tolerance_minutes: int = 0) -> int:
    """Recognize only whole hours after adding the attendance allowance."""
    recognized = max(0, int(eligible_minutes)) + max(0, int(tolerance_minutes))
    return (recognized // 60) * 60


def _round_rupiah(value: Decimal) -> int:
    """Round exact monetary values to whole Rupiah using the existing tie policy."""
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_EVEN))


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
    breaks = break_windows(work_date, cfg)
    brk = overlap_total(win_start, win_end, breaks)
    eligible = max(0, mins(win_start, win_end) - brk)
    tolerance = int(cfg.get("late_tolerance_minutes", 0))
    rounded = recognize_full_hours(eligible, tolerance)
    paid = rounded
    if forfeited:
        max_possible = mins(win_start, e) - overlap_total(win_start, e, breaks)
        max_possible = recognize_full_hours(max_possible, tolerance)
        paid = min(paid, max_possible)
    cap = cfg.get("max_regular_minutes")
    if cap:
        paid = min(paid, int(cap))
    r.update(break_minutes=brk, eligible_minutes=eligible, rounded_minutes=rounded, paid_minutes=paid)
    return r


def compute_overtime(check_in: datetime, check_out, cfg: dict, regular_end: datetime | None = None) -> dict:
    counted_from = max(check_in, regular_end) if regular_end else check_in
    if check_out is None:
        return {"raw_minutes": 0, "break_minutes": 0, "eligible_minutes": 0, "recognized_minutes": 0,
                "paid_minutes": 0, "incomplete": True}
    raw = max(0, mins(counted_from, check_out))
    brk = int(cfg.get("overtime_break_minutes", 0)) if raw >= int(cfg.get("overtime_break_after_minutes", 0) or 0) else 0
    brk = min(brk, raw)
    eligible = raw - brk
    tolerance = int(cfg.get("late_tolerance_minutes", 0))
    recognized = recognize_full_hours(eligible, tolerance)
    return {"raw_minutes": raw, "break_minutes": brk, "eligible_minutes": eligible,
            "recognized_minutes": recognized, "paid_minutes": recognized, "incomplete": False}


def kasbon_cap(balance: int, net_before: int) -> int:
    return min(max(0, balance), max(0, net_before))


def compute_pay(mode: str, regular_rate: int, overtime_rate: int, paid_minutes: int, ot_minutes: int,
                components: list, other_deduction: int, kasbon_balance: int, kasbon_override=None) -> dict:
    component_total = sum(
        (Decimal(c["amount"]) * Decimal(str(c["volume"])) for c in components),
        start=Decimal("0"),
    )
    # Preserve the existing ties-to-even policy while avoiding binary-float drift.
    comp_total = _round_rupiah(component_total)
    if mode == "hourly":
        regular_amount = _round_rupiah(Decimal(regular_rate) * Decimal(paid_minutes) / Decimal(60))
        ot_amount = _round_rupiah(Decimal(overtime_rate) * Decimal(ot_minutes) / Decimal(60))
    else:
        regular_amount, ot_amount = 0, 0
    gross = regular_amount + ot_amount + comp_total
    if other_deduction < 0 or other_deduction > gross:
        raise ValueError("Potongan lain tidak boleh negatif atau melebihi gaji kotor")
    net_before = gross - other_deduction
    cap = kasbon_cap(kasbon_balance, net_before)
    kasbon = 0 if kasbon_override is None else int(kasbon_override)
    if kasbon < 0 or kasbon > cap:
        raise ValueError(f"Potongan kasbon harus antara 0 dan {cap}")
    return {
        "regular_amount": regular_amount, "overtime_amount": ot_amount, "components_total": comp_total,
        "gross": gross, "other_deduction": other_deduction, "net_before_kasbon": net_before,
        "kasbon_balance": kasbon_balance, "kasbon_cap": cap, "kasbon_deduction": kasbon,
        "kasbon_after": kasbon_balance - kasbon, "net_final": net_before - kasbon,
    }
