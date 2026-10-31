# MAKARE end-to-end API regression tests (ordered; run as one module).
# NOTE: finalizes ONE payroll period (end = yesterday) near the end – permanent on Neon DB.
import os
import secrets
import uuid
from datetime import date, timedelta

import pytest
import requests
from core import today_wib

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"
ADMIN_USERNAME = os.environ.get("MAKARE_TEST_ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("MAKARE_TEST_ADMIN_PASSWORD")
OPERATOR_USERNAME = os.environ.get("MAKARE_TEST_OPERATOR_USERNAME", "operator")
OPERATOR_PASSWORD = os.environ.get("MAKARE_TEST_OPERATOR_PASSWORD")
S = {}  # shared state across ordered tests
RUN = uuid.uuid4().hex[:4]


def login(u, p):
    return requests.post(f"{API}/auth/login", json={"username": u, "password": p}, timeout=30)


@pytest.fixture(scope="module")
def admin():
    if not ADMIN_PASSWORD:
        pytest.fail("Set MAKARE_TEST_ADMIN_PASSWORD in the test environment")
    r = login(ADMIN_USERNAME, ADMIN_PASSWORD)
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture(scope="module")
def oper():
    if not OPERATOR_PASSWORD:
        pytest.fail("Set MAKARE_TEST_OPERATOR_PASSWORD in the test environment")
    r = login(OPERATOR_USERNAME, OPERATOR_PASSWORD)
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['token']}"}


def get_settings(h):
    return requests.get(f"{API}/settings", headers=h).json()


def put_settings(h, **patch):
    cfg = get_settings(h)
    body = {k: cfg[k] for k in ["company_name", "company_address", "work_days", "start_time", "end_time", "breaks",
                                 "late_tolerance_minutes", "first_hour_rule", "rounding_threshold_minutes",
                                 "max_regular_minutes", "early_leave_requires_pin", "early_pin_ttl_minutes",
                                 "overtime_enabled", "overtime_break_minutes", "overtime_break_after_minutes",
                                 "kiosk_enabled", "payroll_start_date"]}
    body.update(patch)
    r = requests.put(f"{API}/settings", headers=h, json=body)
    assert r.status_code == 200, r.text


def mk_emp(h, name, mode="hourly", dept=None, comps=None):
    r = requests.post(f"{API}/employees", headers=h, json={
        "full_name": name, "gender": "L", "join_date": "2026-10-01", "payroll_mode": mode, "department_id": dept,
        "regular_rate": 15000, "overtime_rate": 20000, "components": comps or [],
        "ktp": "1234567890123456", "phone": "0812", "address": "Jl Rahasia"})
    assert r.status_code == 200, r.text
    return r.json()


def clock(h, eid, action, mode="regular", pin=None):
    b = {"employee_id": eid, "action": action, "mode": mode}
    if pin:
        b["early_pin"] = pin
    return requests.post(f"{API}/attendance/clock", headers=h, json=b)


def att_row(h, eid, d=None):
    r = requests.get(f"{API}/attendance", headers=h, params={"work_date": d} if d else {})
    return next(x for x in r.json()["rows"] if x["id"] == eid)


# ---- Auth & RBAC ----
def test_auth(admin, oper):
    assert login(ADMIN_USERNAME, "wrong").status_code == 401
    assert requests.get(f"{API}/employees").status_code in (401, 403)
    me = requests.get(f"{API}/auth/me", headers=oper)
    assert me.status_code == 200 and me.json()["role"] == "operator"


def test_operator_forbidden(oper):
    for path in ["/employees/1", "/settings", "/payroll/next-period", "/payroll/periods", "/kasbon", "/audit", "/users"]:
        assert requests.get(f"{API}{path}", headers=oper).status_code == 403, path
    assert requests.post(f"{API}/payroll/preview", headers=oper, json={"end_date": "2026-10-24"}).status_code == 403
    assert requests.get(f"{API}/attendance", headers=oper, params={"work_date": "2026-10-20"}).status_code == 403
    assert requests.get(f"{API}/attendance", headers=oper).status_code == 200
    emps = requests.get(f"{API}/employees", headers=oper).json()
    # Empty installations are valid; when rows exist, operator projection must still omit PII/pay rates.
    assert isinstance(emps, list)
    assert all("regular_rate" not in employee and "ktp" not in employee for employee in emps)


# ---- Departments & employees ----
def test_departments_and_employee(admin):
    r = requests.post(f"{API}/departments", headers=admin, json={"name": f"TEST_Dept{RUN}"})
    assert r.status_code == 200
    S["dept"] = r.json()["id"]
    assert requests.post(f"{API}/departments", headers=admin, json={"name": f"TEST_Dept{RUN}"}).status_code == 409
    assert requests.put(f"{API}/departments/{S['dept']}", headers=admin, json={"name": f"TEST_DeptR{RUN}"}).status_code == 200
    e = mk_emp(admin, f"TEST_Ani{RUN}", dept=S["dept"], comps=[{"name": "Uang makan", "amount": 10000, "volume": 2}])
    assert e["code"].startswith("KRY-")
    S["ani"], S["ani_code"] = e["id"], e["code"]
    g = requests.get(f"{API}/employees/{e['id']}", headers=admin).json()
    assert g["department"] == f"TEST_DeptR{RUN}" and g["components"][0]["amount"] == 10000
    # delete blocked while used
    assert requests.delete(f"{API}/departments/{S['dept']}", headers=admin).status_code == 409
    # update; code must stay immutable even if sent
    body = {"full_name": f"TEST_Ani{RUN}", "gender": "P", "join_date": "2026-10-01", "payroll_mode": "hourly",
            "department_id": S["dept"], "regular_rate": 18000, "overtime_rate": 25000, "components": [], "code": "KRY-9999"}
    assert requests.put(f"{API}/employees/{e['id']}", headers=admin, json=body).status_code == 200
    g = requests.get(f"{API}/employees/{e['id']}", headers=admin).json()
    assert g["code"] == S["ani_code"] and g["regular_rate"] == 18000 and g["gender"] == "P" and g["components"] == []


def test_update_employee_invalid_department(admin):
    body = {"full_name": f"TEST_Ani{RUN}", "gender": "P", "join_date": "2026-10-01", "payroll_mode": "hourly",
            "department_id": 999999, "regular_rate": 18000, "overtime_rate": 25000, "components": []}
    r = requests.put(f"{API}/employees/{S['ani']}", headers=admin, json=body)
    assert r.status_code == 422, f"expected 422 got {r.status_code}"


def test_empty_department_delete(admin):
    r = requests.post(f"{API}/departments", headers=admin, json={"name": f"TEST_Del{RUN}"})
    did = r.json()["id"]
    assert requests.delete(f"{API}/departments/{did}", headers=admin).status_code == 200
    assert requests.delete(f"{API}/departments/{did}", headers=admin).status_code == 404


# ---- Clock in / out ----
def test_clock_rules(admin, oper):
    original_settings = get_settings(admin)
    put_settings(admin, early_leave_requires_pin=False)
    try:
        assert clock(oper, S["ani"], "in").status_code == 200
        assert clock(oper, S["ani"], "in").status_code == 409
        c = mk_emp(admin, f"TEST_Cici{RUN}")
        S["cici"] = c["id"]
        assert clock(admin, S["cici"], "out").status_code == 409
        assert clock(oper, S["ani"], "out").status_code == 200
        assert att_row(admin, S["ani"])["attendance"]["check_out"]
    finally:
        put_settings(admin, early_leave_requires_pin=original_settings["early_leave_requires_pin"])


def test_inactive_rejected(admin):
    e = mk_emp(admin, f"TEST_Eko{RUN}")
    S["eko"] = e["id"]
    assert requests.post(f"{API}/employees/{e['id']}/status", headers=admin, json={"active": False}).status_code == 200
    assert clock(admin, e["id"], "in").status_code == 409


# ---- Early leave PIN ----
def test_early_leave_pin(admin):
    d = mk_emp(admin, f"TEST_Dedi{RUN}")
    S["dedi"] = d["id"]
    original_settings = get_settings(admin)
    put_settings(admin, end_time="23:59")
    try:
        assert clock(admin, d["id"], "in").status_code == 200
        r = clock(admin, d["id"], "out")
        assert r.status_code == 428, r.text
        aid = att_row(admin, d["id"])["attendance"]["id"]
        S["dedi_aid"] = aid
        p = requests.post(f"{API}/attendance/{aid}/early-pin", headers=admin)
        assert p.status_code == 200
        pin = p.json()["pin"]
        wrong = "000000" if pin != "000000" else "111111"
        r = clock(admin, d["id"], "out", pin=wrong)
        assert r.status_code == 403
        r = clock(admin, d["id"], "out", pin=pin)
        assert r.status_code == 200, r.text
        a = att_row(admin, d["id"])["attendance"]
        assert a["early_leave"] is True
        # reopen session via correction, old PIN must not work again
        ci = a["check_in"][11:16]
        from datetime import datetime
        ci = datetime.fromisoformat(a["check_in"]).astimezone().strftime("%H:%M") if False else None
        row_ = att_row(admin, d["id"])["attendance"]
        import zoneinfo
        wib = datetime.fromisoformat(row_["check_in"]).astimezone(zoneinfo.ZoneInfo("Asia/Jakarta")).strftime("%H:%M")
        r = requests.put(f"{API}/attendance/{aid}", headers=admin, json={"status": "hadir", "check_in": wib, "reason": "reopen test"})
        assert r.status_code == 200, r.text
        r = clock(admin, d["id"], "out", pin=pin)
        assert r.status_code == 403, f"PIN reuse should be rejected, got {r.status_code}"
    finally:
        put_settings(admin, end_time=original_settings["end_time"])
    assert get_settings(admin)["end_time"] == original_settings["end_time"]
    put_settings(admin, early_leave_requires_pin=False)
    try:
        assert clock(admin, d["id"], "out").status_code == 200
    finally:
        put_settings(admin, early_leave_requires_pin=original_settings["early_leave_requires_pin"])


# ---- Overtime ----
def test_overtime(admin):
    assert clock(admin, S["ani"], "in", "overtime").status_code == 200
    assert clock(admin, S["ani"], "in", "overtime").status_code == 409
    assert clock(admin, S["ani"], "out", "overtime").status_code == 200
    put_settings(admin, overtime_enabled=False)
    try:
        assert clock(admin, S["ani"], "in", "overtime").status_code == 403
    finally:
        put_settings(admin, overtime_enabled=True)
    assert get_settings(admin)["overtime_enabled"] is True


# ---- Manual entries, historical, correction ----
def test_manual_and_historical(admin, oper):
    assert requests.post(f"{API}/attendance/manual", headers=oper, json={"employee_id": S["cici"], "status": "sakit"}).status_code == 200
    assert requests.post(f"{API}/attendance/manual", headers=oper, json={"employee_id": S["cici"], "status": "izin"}).status_code == 409
    assert requests.post(f"{API}/attendance/manual", headers=oper, json={"employee_id": S["cici"], "status": "alfa", "work_date": "2026-10-20"}).status_code == 403
    tomorrow = (today_wib() + timedelta(days=1)).isoformat()
    assert requests.post(f"{API}/attendance/manual", headers=admin, json={"employee_id": S["cici"], "status": "alfa", "work_date": tomorrow, "reason": "x"}).status_code == 422
    b = {"employee_id": S["ani"], "status": "hadir", "work_date": "2026-10-20", "check_in": "08:10", "check_out": "17:00"}
    assert requests.post(f"{API}/attendance/manual", headers=admin, json=b).status_code == 422
    b["reason"] = "lupa absen"
    assert requests.post(f"{API}/attendance/manual", headers=admin, json=b).status_code == 200
    calc = att_row(admin, S["ani"], "2026-10-20")["attendance"]["calc"]
    assert calc["is_late"] and not calc["first_hour_forfeited"] and calc["paid_minutes"] == 480
    b2 = {**b, "employee_id": S["dedi"], "check_in": "08:31"}
    assert requests.post(f"{API}/attendance/manual", headers=admin, json=b2).status_code == 200
    calc = att_row(admin, S["dedi"], "2026-10-20")["attendance"]["calc"]
    assert calc["first_hour_forfeited"] and calc["paid_minutes"] == 420
    # correction with audit before/after
    aid = att_row(admin, S["cici"])["attendance"]["id"]
    assert requests.put(f"{API}/attendance/{aid}", headers=admin, json={"status": "izin"}).status_code == 422
    assert requests.put(f"{API}/attendance/{aid}", headers=oper, json={"status": "izin", "reason": "salah input"}).status_code == 403
    assert requests.put(f"{API}/attendance/{aid}", headers=admin, json={"status": "izin", "reason": "salah input"}).status_code == 200
    logs = requests.get(f"{API}/audit", headers=admin, params={"entity": "attendance"}).json()
    lg = next(x for x in logs if x["action"] == "attendance_corrected" and str(x["entity_id"]) == str(aid))
    assert lg["before"]["status"] == "sakit" and lg["after"]["status"] == "izin" and lg["after"]["reason"] == "salah input"


# ---- Users ----
def test_users(admin):
    r = requests.post(f"{API}/users", headers=admin, json={"username": f"test_op{RUN}", "full_name": "Test Op", "role": "operator", "password": "secret12345!"})
    assert r.status_code == 200, r.text
    uid = r.json()["id"]
    assert requests.post(f"{API}/users", headers=admin, json={"username": f"test_op{RUN}", "full_name": "Test Op", "role": "operator", "password": "secret12345!"}).status_code == 409
    assert login(f"test_op{RUN}", "secret12345!").status_code == 200
    assert requests.patch(f"{API}/users/{uid}", headers=admin, json={"password": "newpass123!x"}).status_code == 200
    assert login(f"test_op{RUN}", "newpass123!x").status_code == 200
    tok = login(f"test_op{RUN}", "newpass123!x").json()["token"]
    assert requests.patch(f"{API}/users/{uid}", headers=admin, json={"active": False}).status_code == 200
    assert login(f"test_op{RUN}", "newpass123!x").status_code == 401
    assert requests.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {tok}"}).status_code == 401
    users = requests.get(f"{API}/users", headers=admin).json()
    admins = [u for u in users if u["role"] == "admin" and u["active"]]
    if len(admins) == 1:
        assert requests.patch(f"{API}/users/{admins[0]['id']}", headers=admin, json={"active": False}).status_code == 409
        assert requests.patch(f"{API}/users/{admins[0]['id']}", headers=admin, json={"role": "operator"}).status_code == 409


# ---- Kasbon ----
def test_kasbon(admin):
    assert requests.post(f"{API}/kasbon", headers=admin, json={"employee_id": S["ani"], "amount": 0}).status_code == 422
    assert requests.post(f"{API}/kasbon", headers=admin, json={"employee_id": S["ani"], "amount": 100000, "note": "TEST"}).status_code == 200
    led = requests.get(f"{API}/kasbon/{S['ani']}", headers=admin).json()
    assert led[0]["amount"] == 100000 and led[0]["kind"] == "grant"
    summ = requests.get(f"{API}/kasbon", headers=admin).json()
    assert next(x for x in summ if x["employee_id"] == S["ani"])["balance"] == 100000


# ---- Kiosk ----
def test_kiosk(admin):
    m = mk_emp(admin, f"TEST_Fani{RUN}", mode="manual")
    pin = str(secrets.randbelow(899999) + 100000)
    assert requests.post(f"{API}/settings/overtime-pin", headers=admin, json={"pin": pin}).status_code == 200
    tok = get_settings(admin)["kiosk_token"]
    k = f"{API}/kiosk/{tok}"
    assert requests.get(k).status_code == 200
    res = requests.get(f"{k}/employees", params={"q": RUN}).json()
    ids = {x["id"] for x in res}
    assert S["ani"] in ids and m["id"] not in ids and S["eko"] not in ids
    for x in res:
        for bad in ["regular_rate", "overtime_rate", "ktp", "address", "phone", "birth_date"]:
            assert bad not in x
    st = requests.get(f"{k}/employees/{S['cici']}/state").json()
    assert "regular" in st and "regular_rate" not in st
    assert requests.post(f"{k}/clock", json={"employee_id": m["id"], "action": "in"}).status_code == 403
    assert requests.post(f"{k}/clock", json={"employee_id": S["ani"], "action": "in", "mode": "overtime"}).status_code == 403
    assert requests.post(f"{k}/overtime-unlock", json={"pin": "999999"}).status_code == 403
    u = requests.post(f"{k}/overtime-unlock", json={"pin": pin})
    assert u.status_code == 200
    ot = u.json()["ot_token"]
    r = requests.post(f"{k}/clock", json={"employee_id": S["ani"], "action": "in", "mode": "overtime", "ot_token": ot})
    assert r.status_code == 200 and "regular_rate" not in str(r.json())
    assert requests.post(f"{k}/clock", json={"employee_id": S["ani"], "action": "out", "mode": "overtime", "ot_token": ot}).status_code == 200
    # rotate
    new = requests.post(f"{API}/settings/kiosk-rotate", headers=admin).json()["kiosk_token"]
    assert requests.get(k).status_code == 404
    assert requests.get(f"{API}/kiosk/{new}").status_code == 200
    # ot token bound to old kiosk token
    assert requests.post(f"{API}/kiosk/{new}/clock", json={"employee_id": S["ani"], "action": "in", "mode": "overtime", "ot_token": ot}).status_code == 403
    # Leave a fresh random PIN configured; never leave a known test PIN active.
    next_pin = str(secrets.randbelow(900000) + 100000)
    assert requests.post(f"{API}/settings/overtime-pin", headers=admin, json={"pin": next_pin}).status_code == 200


def test_attendance_report_and_pdf(admin):
    params = {"start_date": (today_wib() - timedelta(days=7)).isoformat(),
              "end_date": today_wib().isoformat()}
    report = requests.get(f"{API}/reports/attendance", headers=admin, params=params)
    assert report.status_code == 200, report.text
    assert "summary" in report.json() and "rows" in report.json()
    pdf = requests.get(f"{API}/reports/attendance.pdf", headers=admin, params=params)
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF", pdf.text[:200]


# ---- Payroll / Tutup Buku ----
END = (today_wib() - timedelta(days=7)).isoformat()


def test_preview(admin):
    nxt = requests.get(f"{API}/payroll/next-period", headers=admin).json()
    S["start"] = nxt["start_date"]
    assert requests.post(f"{API}/payroll/preview", headers=admin,
                         json={"end_date": (today_wib() + timedelta(days=1)).isoformat()}).status_code == 422
    r = requests.post(f"{API}/payroll/preview", headers=admin, json={"end_date": END})
    assert r.status_code == 200, r.text
    lines = {ln["employee_id"]: ln for ln in r.json()["lines"]}
    ani = lines[S["ani"]]
    for k in ["raw_minutes", "break_minutes", "late_adjustment_minutes", "eligible_minutes", "rounded_minutes", "paid_minutes"]:
        assert k in ani["durations"]
    assert ani["durations"]["paid_minutes"] == 480 and ani["gross"] == 8 * 18000
    assert ani["kasbon_cap"] == min(100000, ani["net_before_kasbon"])
    S["ani_cap"] = ani["kasbon_cap"]
    bad = requests.post(f"{API}/payroll/preview", headers=admin, json={"end_date": END, "adjustments": {str(S["ani"]): {"kasbon_deduction": ani["kasbon_cap"] + 1}}})
    assert bad.status_code == 422


def test_finalize_idempotent_and_lock(admin):
    if requests.get(f"{API}/payroll/periods", headers=admin).json():
        pytest.skip("A period already closed; not closing another")
    key = f"test-{uuid.uuid4().hex}"
    body = {"end_date": END, "idempotency_key": key, "adjustments": {str(S["ani"]): {"kasbon_deduction": 50000}}}
    r1 = requests.post(f"{API}/payroll/finalize", headers=admin, json=body)
    assert r1.status_code == 200, r1.text
    assert r1.json()["duplicate"] is False
    r2 = requests.post(f"{API}/payroll/finalize", headers=admin, json=body)
    assert r2.status_code == 200 and r2.json()["duplicate"] is True and r2.json()["period_id"] == r1.json()["period_id"]
    changed = {**body, "adjustments": {str(S["ani"]): {"kasbon_deduction": 50000, "other_deduction": 1}}}
    r3 = requests.post(f"{API}/payroll/finalize", headers=admin, json=changed)
    assert r3.status_code == 409, r3.text
    pid = r1.json()["period_id"]
    S["pid"] = pid
    periods = requests.get(f"{API}/payroll/periods", headers=admin).json()
    assert len(periods) == 1
    det = requests.get(f"{API}/payroll/periods/{pid}", headers=admin).json()
    ids = [ln["employee_id"] for ln in det["lines"]]
    assert len(ids) == len(set(ids))
    led = requests.get(f"{API}/kasbon/{S['ani']}", headers=admin).json()
    assert len([x for x in led if x["kind"] == "deduction"]) == 1
    assert requests.get(f"{API}/kasbon", headers=admin).json()
    # locked dates
    aid = att_row(admin, S["ani"], "2026-10-20")["attendance"]["id"]
    assert requests.put(f"{API}/attendance/{aid}", headers=admin, json={"status": "izin", "reason": "lock test"}).status_code == 409
    assert requests.post(f"{API}/attendance/manual", headers=admin, json={"employee_id": S["cici"], "status": "alfa", "work_date": "2026-10-21", "reason": "x"}).status_code == 409
    assert requests.get(f"{API}/attendance", headers=admin, params={"work_date": "2026-10-20"}).json()["locked"] is True
    # PDFs
    rp = requests.get(f"{API}/payroll/periods/{pid}/recap.pdf", headers=admin)
    assert rp.status_code == 200 and rp.headers["content-type"].startswith("application/pdf") and rp.content[:4] == b"%PDF"
    sp = requests.get(f"{API}/payroll/periods/{pid}/slip/{S['ani']}.pdf", headers=admin)
    assert sp.status_code == 200 and sp.content[:4] == b"%PDF"
    assert requests.get(f"{API}/payroll/periods/{pid}/slip/999999.pdf", headers=admin).status_code == 404
    # next period starts after END
    assert requests.get(f"{API}/payroll/next-period", headers=admin).json()["start_date"] == "2026-10-25"
