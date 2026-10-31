import os
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

os.environ.setdefault("JWT_SECRET", "unit-test-signing-key-not-used-for-real-tokens")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from routes_reports import _active_at_shift_start  # noqa: E402

WIB = ZoneInfo("Asia/Jakarta")
CFG = {"start_time": "08:00", "end_time": "17:00", "breaks": []}


def event(action, day, hour, minute=0):
    return {"action": action, "created_at": datetime(2026, 10, day, hour, minute, tzinfo=WIB)}


def test_inactive_employee_is_not_inferred_absent_after_deactivation():
    events = [event("employee_deactivated", 1, 17)]

    assert _active_at_shift_start(events, date(2026, 10, 2), CFG) is False


def test_deactivation_after_shift_start_does_not_erase_that_workday():
    events = [event("employee_deactivated", 2, 16)]

    assert _active_at_shift_start(events, date(2026, 10, 2), CFG) is True


def test_reactivation_restores_inference_for_later_workdays():
    events = [event("employee_deactivated", 1, 17), event("employee_activated", 3, 7)]

    assert _active_at_shift_start(events, date(2026, 10, 2), CFG) is False
    assert _active_at_shift_start(events, date(2026, 10, 3), CFG) is True


def test_transition_at_shift_start_applies_to_that_workday():
    events = [event("employee_deactivated", 2, 8)]

    assert _active_at_shift_start(events, date(2026, 10, 2), CFG) is False
