# Setup for payroll adjustment tests: TEST_ employees + historical attendance + kasbon (run once before closing)
import json
import os
import requests

API = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/") + "/api"
tok = requests.post(f"{API}/auth/login", json={"username": "admin", "password": "admin123"}).json()["token"]
H = {"Authorization": f"Bearer {tok}"}
out = {}
for name in ["TEST_KorAPI", "TEST_KorUI"]:
    r = requests.post(f"{API}/employees", headers=H, json={
        "full_name": name, "gender": "L", "join_date": "2026-10-01", "payroll_mode": "hourly", "department_id": None,
        "regular_rate": 15000, "overtime_rate": 20000, "components": [],
        "ktp": "1234567890123456", "phone": "0812", "address": "Jl Test"})
    assert r.status_code == 200, r.text
    e = r.json()
    for d in ["2026-10-20", "2026-10-21"]:
        a = requests.post(f"{API}/attendance/manual", headers=H, json={
            "employee_id": e["id"], "status": "hadir", "work_date": d, "check_in": "08:00", "check_out": "17:00",
            "reason": "TEST historis koreksi"})
        assert a.status_code == 200, a.text
    k = requests.post(f"{API}/kasbon", headers=H, json={"employee_id": e["id"], "amount": 200000, "note": "TEST kasbon"})
    assert k.status_code == 200, k.text
    out[name] = {"id": e["id"], "code": e["code"]}
print(json.dumps(out))
pv = requests.post(f"{API}/payroll/preview", headers=H, json={"end_date": "2026-10-24"}).json()
for ln in pv["lines"]:
    print(ln["code"], ln["full_name"], ln["gross"], ln["kasbon_deduction"], ln["net_final"])
