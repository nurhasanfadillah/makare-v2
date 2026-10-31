import sys
from pathlib import Path
from datetime import date, datetime, timedelta
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rules import compute_regular, compute_overtime, kasbon_cap, compute_pay, WIB  # noqa: E402

CFG = {"start_time": "08:00", "end_time": "17:00", "breaks": [{"start": "12:00", "end": "13:00"}],
       "late_tolerance_minutes": 30, "first_hour_rule": True, "rounding_threshold_minutes": 30, "max_regular_minutes": 480}
D = date(2026, 1, 5)


def t(h, m, d=D):
    return datetime(d.year, d.month, d.day, h, m, tzinfo=WIB)


def test_late_within_tolerance_keeps_first_hour():
    r = compute_regular(t(8, 10), t(17, 0), D, CFG)
    assert r["is_late"] and not r["first_hour_forfeited"]
    assert r["paid_minutes"] == 480


@pytest.mark.parametrize("minute,forfeited,paid", [(30, False, 480), (31, True, 420)])
def test_lateness_tolerance_is_inclusive_at_exact_boundary(minute, forfeited, paid):
    result = compute_regular(t(8, minute), t(17, 0), D, CFG)

    assert result["late_minutes"] == minute
    assert result["first_hour_forfeited"] is forfeited
    assert result["paid_minutes"] == paid


@pytest.mark.parametrize("m", [31, 35])
def test_late_beyond_tolerance_forfeits_first_hour(m):
    r = compute_regular(t(8, m), t(17, 0), D, CFG)
    assert r["first_hour_forfeited"]
    assert r["paid_minutes"] == 420


def test_first_hour_forfeiture_caps_recognized_hours():
    r = compute_regular(t(8, 45), t(16, 30), D, CFG)
    assert r["eligible_minutes"] == 390 and r["rounded_minutes"] == 420 and r["paid_minutes"] == 420
    r2 = compute_regular(t(8, 45), t(17, 0), D, CFG)
    assert r2["paid_minutes"] == 420


@pytest.mark.parametrize("eligible,tolerance,expected", [(460, 30, 480), (440, 30, 420), (410, 20, 420)])
def test_regular_recognition_adds_tolerance_then_floors(eligible, tolerance, expected):
    from rules import recognize_full_hours
    assert recognize_full_hours(eligible, tolerance) == expected


@pytest.mark.parametrize("check_in,expected", [(t(8, 20), 480), (t(8, 40), 420)])
def test_regular_payroll_uses_recognition_tolerance(check_in, expected):
    cfg = {**CFG, "first_hour_rule": False}
    assert compute_regular(check_in, t(17, 0), D, cfg)["paid_minutes"] == expected


def test_regular_capped_at_schedule_end_not_overtime():
    r = compute_regular(t(7, 30), t(19, 0), D, CFG)
    assert r["paid_minutes"] == 480 and r["break_minutes"] == 60


def test_break_overlap_only():
    r = compute_regular(t(8, 0), t(12, 30), D, CFG)
    assert r["break_minutes"] == 30 and r["eligible_minutes"] == 240 and r["early_leave"]


def test_overlapping_break_windows_are_deducted_once():
    cfg = {**CFG, "breaks": [{"start": "12:00", "end": "13:00"}, {"start": "12:30", "end": "13:30"}]}
    r = compute_regular(t(8, 0), t(17, 0), D, cfg)

    assert r["break_minutes"] == 90
    assert r["eligible_minutes"] == 450


def test_never_negative():
    r = compute_regular(t(16, 0), t(16, 10), D, CFG)
    assert r["eligible_minutes"] >= 0 and r["paid_minutes"] == 0


def test_cross_midnight_follows_check_in_date():
    cfg = {**CFG, "start_time": "22:00", "end_time": "06:00", "breaks": [{"start": "02:00", "end": "03:00"}]}
    r = compute_regular(t(22, 0), t(6, 0, date(2026, 1, 6)), D, cfg)
    assert r["break_minutes"] == 60 and r["paid_minutes"] == 420


def test_overtime_break():
    r = compute_overtime(t(17, 0), t(22, 0), {"overtime_break_minutes": 30, "overtime_break_after_minutes": 240,
                                                "late_tolerance_minutes": 0})
    assert r["paid_minutes"] == 240


@pytest.mark.parametrize("duration,tolerance,expected", [(150, 20, 120), (160, 20, 180)])
def test_overtime_recognition_adds_regular_tolerance_then_floors(duration, tolerance, expected):
    r = compute_overtime(t(17, 0), t(17, 0) + timedelta(minutes=duration),
                         {"overtime_break_minutes": 0, "overtime_break_after_minutes": 240,
                          "late_tolerance_minutes": tolerance})
    assert r["eligible_minutes"] == duration
    assert r["paid_minutes"] == expected


def test_overtime_started_before_regular_end_counts_from_regular_end():
    r = compute_overtime(
        t(16, 30), t(19, 30), {"overtime_break_minutes": 0, "overtime_break_after_minutes": 240,
                               "late_tolerance_minutes": 0},
        regular_end=t(17, 0),
    )
    assert r["raw_minutes"] == 150 and r["paid_minutes"] == 120


def test_overtime_ending_before_regular_end_has_no_payable_time():
    r = compute_overtime(
        t(16, 30), t(16, 55), {"overtime_break_minutes": 0, "overtime_break_after_minutes": 240,
                               "late_tolerance_minutes": 0},
        regular_end=t(17, 0),
    )
    assert r["raw_minutes"] == 0 and r["paid_minutes"] == 0


def test_kasbon_cap_and_non_negative():
    assert kasbon_cap(500_000, 300_000) == 300_000
    assert kasbon_cap(100_000, 300_000) == 100_000
    assert kasbon_cap(100_000, -5) == 0
    p = compute_pay("hourly", 10_000, 15_000, 480, 60, [], 0, 1_000_000)
    assert p["gross"] == 95_000 and p["kasbon_deduction"] == 0 and p["net_final"] == 95_000
    p_override = compute_pay("hourly", 10_000, 15_000, 480, 60, [], 0, 1_000_000, kasbon_override=95_000)
    assert p_override["kasbon_deduction"] == 95_000 and p_override["net_final"] == 0
    with pytest.raises(ValueError):
        compute_pay("hourly", 10_000, 0, 60, 0, [], 0, 50_000, kasbon_override=20_000)


def test_manual_mode():
    p = compute_pay("manual", 0, 0, 999, 999, [{"amount": 100_000, "volume": 2}, {"amount": 50_000, "volume": 1.5}], 0, 0)
    assert p["gross"] == 275_000
