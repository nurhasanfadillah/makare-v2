"""Create an explicitly named live-test employee and close a two-day period.

Load MAKARE_TEST_ADMIN_USERNAME / MAKARE_TEST_ADMIN_PASSWORD from the ignored
local environment before running. All rows are removable test fixtures.
"""
import os
from datetime import date, timedelta
import uuid

import requests

API = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
admin = requests.post(
    f"{API}/auth/login",
    json={
        "username": os.environ["MAKARE_TEST_ADMIN_USERNAME"],
        "password": os.environ["MAKARE_TEST_ADMIN_PASSWORD"],
    },
    timeout=30,
)
assert admin.status_code == 200, admin.status_code
headers = {"Authorization": f"Bearer {admin.json()['token']}"}

settings = requests.get(f"{API}/settings", headers=headers, timeout=30).json()
next_period = requests.get(f"{API}/payroll/next-period", headers=headers, timeout=30).json()
start = date.fromisoformat(next_period["start_date"])
end = date.today() - timedelta(days=1)
workdays = set(settings["work_days"])
attendance_days = [
    current.isoformat()
    for offset in range((end - start).days + 1)
    if (current := start + timedelta(days=offset)).isoweekday() in workdays
][:2]
assert len(attendance_days) == 2, "Need two past working days in the next open period"

employee = requests.post(
    f"{API}/employees",
    headers=headers,
    json={
        "full_name": "TEST_KorAPI",
        "gender": "L",
        "join_date": start.isoformat(),
        "payroll_mode": "hourly",
        "department_id": None,
        "regular_rate": 15000,
        "overtime_rate": 20000,
        "components": [],
    },
    timeout=30,
)
assert employee.status_code == 200, employee.status_code
employee = employee.json()

for work_date in attendance_days:
    result = requests.post(
        f"{API}/attendance/manual",
        headers=headers,
        json={
            "employee_id": employee["id"],
            "status": "hadir",
            "work_date": work_date,
            "check_in": "08:00",
            "check_out": "17:00",
            "reason": "TEST acceptance payroll correction fixture",
        },
        timeout=30,
    )
    assert result.status_code == 200, result.status_code

advance = requests.post(
    f"{API}/kasbon",
    headers=headers,
    json={"employee_id": employee["id"], "amount": 200000, "note": "TEST payroll correction fixture"},
    timeout=30,
)
assert advance.status_code == 200, advance.status_code

adjustments = {str(employee["id"]): {"kasbon_deduction": 200000}}
preview = requests.post(
    f"{API}/payroll/preview",
    headers=headers,
    json={"end_date": end.isoformat(), "adjustments": adjustments},
    timeout=60,
)
assert preview.status_code == 200, preview.status_code
line = next(row for row in preview.json()["lines"] if row["employee_id"] == employee["id"])
assert line["gross"] == 240000 and line["kasbon_deduction"] == 200000 and line["net_final"] == 40000

finalize = requests.post(
    f"{API}/payroll/finalize",
    headers=headers,
    json={
        "end_date": end.isoformat(),
        "idempotency_key": f"test-adjustment-fixture-{uuid.uuid4().hex}",
        "adjustments": adjustments,
    },
    timeout=60,
)
assert finalize.status_code == 200, finalize.status_code
print("Payroll adjustment acceptance fixture created; run test_payroll_adjustments.py, then clean test rows.")
