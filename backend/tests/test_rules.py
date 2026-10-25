import sys
from pathlib import Path
from datetime import date, datetime
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rules import compute_regular, compute_overtime, round_minutes, kasbon_cap, compute_pay, WIB  # noqa: E402

CFG = {"start_time": "08:00", "end_time": "17:00", "breaks": [{"start": "12:00", "end": "13:00"}],
       "late_tolerance_minutes": 30, "first_hour_rule": True, "rounding_threshold_minutes": 30, "max_regular_minutes": 480}
D = date(2026, 1, 5)


def t(h, m, d=D):
    return datetime(d.year, d.month, d.day, h, m, tzinfo=WIB)


def test_late_within_tolerance_keeps_first_hour():
    r = compute_regular(t(8, 10), t(17, 0), D, CFG)
    assert r["is_late"] and not r["first_hour_forfeited"]
    assert r["paid_minutes"] == 480


@pytest.mark.parametrize("m", [31, 35])
def test_late_beyond_tolerance_forfeits_first_hour(m):
    r = compute_regular(t(8, m), t(17, 0), D, CFG)
    assert r["first_hour_forfeited"]
    assert r["paid_minutes"] == 420


@pytest.mark.parametrize("m,exp", [(7 * 60 + 28, 420), (7 * 60 + 30, 480), (7 * 60 + 32, 480), (29, 0), (30, 60)])
def test_rounding(m, exp):
    assert round_minutes(m) == exp


def test_rounding_does_not_restore_forfeited_hour():
    r = compute_regular(t(8, 45), t(16, 30), D, CFG)
    assert r["eligible_minutes"] == 390 and r["rounded_minutes"] == 420 and r["paid_minutes"] == 420
    r2 = compute_regular(t(8, 45), t(17, 0), D, CFG)
    assert r2["paid_minutes"] == 420


def test_regular_capped_at_schedule_end_not_overtime():
    r = compute_regular(t(7, 30), t(19, 0), D, CFG)
    assert r["paid_minutes"] == 480 and r["break_minutes"] == 60


def test_break_overlap_only():
    r = compute_regular(t(8, 0), t(12, 30), D, CFG)
    assert r["break_minutes"] == 30 and r["eligible_minutes"] == 240 and r["early_leave"]


def test_never_negative():
    r = compute_regular(t(16, 0), t(16, 10), D, CFG)
    assert r["eligible_minutes"] >= 0 and r["paid_minutes"] == 0


def test_cross_midnight_follows_check_in_date():
    cfg = {**CFG, "start_time": "22:00", "end_time": "06:00", "breaks": [{"start": "02:00", "end": "03:00"}]}
    r = compute_regular(t(22, 0), t(6, 0, date(2026, 1, 6)), D, cfg)
    assert r["break_minutes"] == 60 and r["paid_minutes"] == 420


def test_overtime_break():
    r = compute_overtime(t(17, 0), t(22, 0), {"overtime_break_minutes": 30, "overtime_break_after_minutes": 240})
    assert r["paid_minutes"] == 270


def test_kasbon_cap_and_non_negative():
    assert kasbon_cap(500_000, 300_000) == 300_000
    assert kasbon_cap(100_000, 300_000) == 100_000
    assert kasbon_cap(100_000, -5) == 0
    p = compute_pay("hourly", 10_000, 15_000, 480, 60, [], 0, 1_000_000)
    assert p["gross"] == 95_000 and p["kasbon_deduction"] == 95_000 and p["net_final"] == 0
    with pytest.raises(ValueError):
        compute_pay("hourly", 10_000, 0, 60, 0, [], 0, 50_000, kasbon_override=20_000)


def test_manual_mode():
    p = compute_pay("manual", 0, 0, 999, 999, [{"amount": 100_000, "volume": 2}, {"amount": 50_000, "volume": 1.5}], 0, 0)
    assert p["gross"] == 275_000
