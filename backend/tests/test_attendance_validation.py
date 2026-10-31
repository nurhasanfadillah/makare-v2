import asyncio
import os
from datetime import date, datetime

import pytest
from pydantic import ValidationError

os.environ.setdefault("JWT_SECRET", "test-only-secret-for-validation-tests")

from routes_admin import BreakIn, SettingsIn  # noqa: E402
from routes_attendance import CorrectionIn, ManualIn, _is_early_leave  # noqa: E402
from rules import WIB  # noqa: E402
import services  # noqa: E402
from fastapi import HTTPException  # noqa: E402


@pytest.mark.parametrize("model", [ManualIn, CorrectionIn])
@pytest.mark.parametrize("clock_time", ["00:00", "08:30", "23:59"])
def test_manual_and_correction_accept_valid_clock_times(model, clock_time):
    payload = {"employee_id": 1, "status": "hadir", "check_in": clock_time}
    if model is CorrectionIn:
        payload["reason"] = "Koreksi data"

    assert model(**payload).check_in == clock_time


@pytest.mark.parametrize("model,field", [
    (ManualIn, "check_in"), (ManualIn, "check_out"),
    (CorrectionIn, "check_in"), (CorrectionIn, "check_out"),
])
@pytest.mark.parametrize("clock_time", ["24:00", "99:99", "12:60"])
def test_manual_and_correction_reject_out_of_range_clock_times(model, field, clock_time):
    payload = {"employee_id": 1, "status": "hadir", field: clock_time}
    if model is CorrectionIn:
        payload["reason"] = "Koreksi data"

    with pytest.raises(ValidationError):
        model(**payload)


@pytest.mark.parametrize("reason", ["   ", "  x  "])
def test_correction_requires_non_whitespace_reason(reason):
    with pytest.raises(ValidationError):
        CorrectionIn(employee_id=1, status="izin", reason=reason)


def test_correction_trims_a_valid_reason():
    correction = CorrectionIn(employee_id=1, status="izin", reason="  Koreksi data  ")

    assert correction.reason == "Koreksi data"


@pytest.mark.parametrize("clock_time", ["24:00", "99:99", "12:60"])
def test_break_settings_reject_invalid_clock_values(clock_time):
    with pytest.raises(ValidationError):
        BreakIn(start=clock_time, end="13:00")


SETTINGS = {
    "company_name": "MAKARE Test",
    "work_days": [1, 2, 3, 4, 5, 6],
    "start_time": "08:00",
    "end_time": "17:00",
    "breaks": [{"start": "12:00", "end": "13:00"}],
    "late_tolerance_minutes": 30,
    "first_hour_rule": True,
    "rounding_threshold_minutes": 30,
    "max_regular_minutes": 480,
    "early_leave_requires_pin": True,
    "early_pin_ttl_minutes": 15,
    "overtime_enabled": True,
    "overtime_break_minutes": 0,
    "overtime_break_after_minutes": 240,
    "kiosk_enabled": True,
    "payroll_start_date": "2026-01-01",
}


@pytest.mark.parametrize("field", ["start_time", "end_time"])
@pytest.mark.parametrize("clock_time", ["24:00", "99:99", "12:60"])
def test_settings_reject_invalid_schedule_times(field, clock_time):
    with pytest.raises(ValidationError):
        SettingsIn(**{**SETTINGS, field: clock_time})


@pytest.mark.parametrize("override", [
    {"work_days": []}, {"work_days": [1, 1]}, {"work_days": [8]},
    {"start_time": "08:00", "end_time": "08:00"},
    {"breaks": [{"start": "17:00", "end": "18:00"}]},
    {"breaks": [{"start": "12:00", "end": "12:00"}]},
    {"company_name": "   "},
])
def test_settings_reject_invalid_cross_field_schedule(override):
    with pytest.raises(ValidationError):
        SettingsIn(**{**SETTINGS, **override})


def test_settings_accept_overnight_shift_break_inside_shift():
    schedule = SettingsIn(**{
        **SETTINGS,
        "start_time": "22:00",
        "end_time": "06:00",
        "breaks": [{"start": "00:00", "end": "01:00"}],
    })

    assert schedule.start_time == "22:00"


@pytest.mark.parametrize("check_out,expected", [
    (datetime(2026, 1, 5, 16, 59, tzinfo=WIB), True),
    (datetime(2026, 1, 5, 17, 0, tzinfo=WIB), False),
    (datetime(2026, 1, 5, 17, 1, tzinfo=WIB), False),
    (None, False),
])
def test_manual_and_corrected_attendance_share_early_leave_boundary(check_out, expected):
    cfg = {"start_time": "08:00", "end_time": "17:00"}

    assert _is_early_leave(date(2026, 1, 5), check_out, cfg) is expected


def test_early_leave_boundary_works_for_overnight_shift():
    cfg = {"start_time": "22:00", "end_time": "06:00"}

    assert _is_early_leave(date(2026, 1, 5), datetime(2026, 1, 6, 5, 59, tzinfo=WIB), cfg)
    assert not _is_early_leave(date(2026, 1, 5), datetime(2026, 1, 6, 6, 0, tzinfo=WIB), cfg)


class _Transaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False


class _InactiveEmployeeConnection:
    def __init__(self):
        self.events = []

    def transaction(self):
        return _Transaction()

    async def execute(self, query, *_args):
        self.events.append("advisory_lock" if "pg_advisory_xact_lock" in query else "write")

    async def fetchrow(self, query, *_args):
        self.events.append("employee_for_update" if "FOR UPDATE" in query else "employee_read")
        return {"id": 7, "code": "KRY-0007", "full_name": "Inactive", "active": False, "payroll_mode": "hourly"}


def test_clock_checks_active_state_after_locking_employee_inside_transaction(monkeypatch):
    async def settings(_conn):
        return {"start_time": "08:00", "end_time": "17:00", "breaks": [], "late_tolerance_minutes": 0}

    async def ensure_open(_conn, _date):
        return None

    monkeypatch.setattr(services, "get_settings", settings)
    monkeypatch.setattr(services, "today_wib", lambda: date(2026, 1, 5))
    monkeypatch.setattr(services, "now_wib", lambda: datetime(2026, 1, 5, 9, 0, tzinfo=WIB))
    monkeypatch.setattr(services, "ensure_open_date", ensure_open)
    conn = _InactiveEmployeeConnection()

    with pytest.raises(HTTPException) as exc:
        asyncio.run(services.clock(conn, 7, "regular", "in", "operator", "panel"))

    assert exc.value.status_code == 409
    assert conn.events == ["advisory_lock", "employee_for_update"]
