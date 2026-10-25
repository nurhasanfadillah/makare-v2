# Payroll correction (Koreksi Payroll) API tests on a CLOSED period. Ordered; run as one module.
# Requires: a closed period containing TEST_KorAPI (net_final 40000, kasbon_deduction 200000) - see setup_adjustment_data.py
import os
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
import requests

API = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/") + "/api"
S = {}


def login(u, p):
    r = requests.post(f"{API}/auth/login", json={"username": u, "password": p}, timeout=30)
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture(scope="module")
def admin():
    return login("admin", "admin123")


@pytest.fixture(scope="module")
def oper():
    return login("operator", "operator123")


def key():
    return uuid.uuid4().hex


def detail(h):
    r = requests.get(f"{API}/payroll/periods/{S['pid']}", headers=h, timeout=30)
    assert r.status_code == 200
    d = r.json()
    return d, next(ln for ln in d["lines"] if ln["employee_id"] == S["eid"])


def create(h, kind, amount, reason="TEST_koreksi alasan", k=None):
    return requests.post(f"{API}/payroll/periods/{S['pid']}/adjustments", headers=h, timeout=60,
                         json={"employee_id": S["eid"], "kind": kind, "amount": amount, "reason": reason, "idempotency_key": k or key()})


# Setup: locate closed period + test employee
def test_locate(admin):
    periods = requests.get(f"{API}/payroll/periods", headers=admin).json()
    assert periods
    for p in periods:
        d = requests.get(f"{API}/payroll/periods/{p['id']}", headers=admin).json()
        ln = next((x for x in d["lines"] if x["full_name"] == "TEST_KorAPI"), None)
        if ln:
            S.update(pid=p["id"], eid=ln["employee_id"], net0=ln["net_final"], kas0=ln["kasbon_deduction"])
            break
    assert "pid" in S
    assert S["net0"] == 40000 and S["kas0"] == 200000
    _, ln = detail(admin)
    assert ln["net_effective"] == 40000 and ln["adj_net"] == 0 and ln["kasbon_effective"] == 200000


# RBAC
def test_operator_forbidden(oper):
    body = {"employee_id": S["eid"], "kind": "earning", "amount": 1000}
    assert requests.post(f"{API}/payroll/periods/{S['pid']}/adjustments/preview", headers=oper, json=body).status_code == 403
    assert requests.post(f"{API}/payroll/periods/{S['pid']}/adjustments", headers=oper,
                         json={**body, "reason": "TEST_opr try", "idempotency_key": key()}).status_code == 403
    assert requests.post(f"{API}/payroll/periods/{S['pid']}/adjustments/preview", json=body).status_code in (401, 403)


# Validation
def test_validation(admin):
    assert create(admin, "earning", 1000, reason="abc").status_code == 422
    assert create(admin, "earning", 0).status_code == 422
    assert create(admin, "bonus", 1000).status_code == 422
    r = requests.post(f"{API}/payroll/periods/999999/adjustments/preview", headers=admin, json={"employee_id": S["eid"], "kind": "earning", "amount": 1})
    assert r.status_code == 404
    r = requests.post(f"{API}/payroll/periods/{S['pid']}/adjustments/preview", headers=admin, json={"employee_id": 999999, "kind": "earning", "amount": 1})
    assert r.status_code == 404


def test_zz_whitespace_reason(admin):
    # " ab    " passes pydantic min_length but DB CHECK(length(trim(reason))>=5) -> must be 422, not 500
    r = create(admin, "earning", 1000, reason="  ab      ")
    assert r.status_code == 422, f"{r.status_code} {r.text[:200]}"


# Preview does not persist
def test_preview(admin):
    r = requests.post(f"{API}/payroll/periods/{S['pid']}/adjustments/preview", headers=admin,
                      json={"employee_id": S["eid"], "kind": "earning", "amount": 50000})
    assert r.status_code == 200
    d = r.json()
    assert d["before"]["net_final"] == 40000 and d["after"]["net_final"] == 90000 and d["delta_net"] == 50000
    assert d["original"]["net_final"] == 40000
    assert d["after"]["kasbon_balance"] == d["before"]["kasbon_balance"]
    det, ln = detail(admin)
    assert ln["adj_count"] == 0


# Earning + idempotency
def test_earning_idempotent(admin):
    k = key()
    r1 = create(admin, "earning", 50000, k=k)
    assert r1.status_code == 200, r1.text
    assert r1.json()["duplicate"] is False and r1.json()["after"]["net_final"] == 90000
    r2 = create(admin, "earning", 50000, k=k)
    assert r2.status_code == 200 and r2.json()["duplicate"] is True and r2.json()["id"] == r1.json()["id"]
    det, ln = detail(admin)
    assert ln["adj_count"] == 1 and ln["net_effective"] == 90000 and ln["net_final"] == 40000
    S["earn_id"] = r1.json()["id"]


def test_parallel_same_key(admin):
    k = key()
    with ThreadPoolExecutor(3) as ex:
        res = list(ex.map(lambda _: create(admin, "earning", 1000, k=k), range(3)))
    codes = [r.status_code for r in res]
    assert codes.count(200) == 3, codes
    assert sum(1 for r in res if r.json()["duplicate"] is False) == 1
    det, ln = detail(admin)
    assert ln["adj_count"] == 2 and ln["net_effective"] == 91000


# Deduction
def test_deduction(admin):
    assert create(admin, "deduction", 91001).status_code == 422
    r = create(admin, "deduction", 11000)
    assert r.status_code == 200
    assert r.json()["before"]["net_final"] == 91000 and r.json()["after"]["net_final"] == 80000
    det, ln = detail(admin)
    assert ln["net_effective"] == 80000 and ln["adj_deduction"] == 11000


# Kasbon reversal
def test_kasbon_reversal(admin):
    def bal():
        return next(x for x in requests.get(f"{API}/kasbon", headers=admin).json() if x["employee_id"] == S["eid"])
    b0 = bal()
    assert b0["balance"] == 0
    assert create(admin, "kasbon_reversal", 200001).status_code == 422
    r = create(admin, "kasbon_reversal", 50000, reason="TEST_salah potong kasbon")
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["before"]["kasbon_balance"] == 0 and d["after"]["kasbon_balance"] == 50000
    assert d["after"]["kasbon_deduction"] == 150000 and d["after"]["net_final"] == 130000
    b1 = bal()
    assert b1["balance"] == 50000 and b1["total_reversal"] == 50000
    led = requests.get(f"{API}/kasbon/{S['eid']}", headers=admin).json()
    rev = [x for x in led if x["kind"] == "reversal"]
    assert len(rev) == 1 and rev[0]["amount"] == 50000 and rev[0]["period_id"] == S["pid"]
    ded = [x for x in led if x["kind"] == "deduction"]
    assert len(ded) == 1 and ded[0]["amount"] == 200000  # original deduction untouched, not duplicated
    assert create(admin, "kasbon_reversal", 150001).status_code == 422
    det, ln = detail(admin)
    assert ln["kasbon_effective"] == 150000 and ln["kasbon_deduction"] == 200000 and ln["net_effective"] == 130000


def test_parallel_deductions_capped(admin):
    # effective net 130000; 3 parallel deductions of 60000 -> at most 2 may succeed
    with ThreadPoolExecutor(3) as ex:
        res = list(ex.map(lambda _: create(admin, "deduction", 60000), range(3)))
    codes = sorted(r.status_code for r in res)
    assert codes == [200, 200, 422], codes
    det, ln = detail(admin)
    assert ln["net_effective"] == 10000 and ln["net_effective"] >= 0


# Snapshot unchanged + adjustment list + period list + audit
def test_snapshot_and_listing(admin):
    det, ln = detail(admin)
    assert ln["net_final"] == S["net0"] and ln["kasbon_deduction"] == S["kas0"]
    mine = [a for a in det["adjustments"] if a["employee_id"] == S["eid"]]
    assert len(mine) == ln["adj_count"] == 6
    for a in mine:
        assert "idempotency_key" not in a and a["created_by"] == "admin" and len(a["reason"]) >= 5
        assert "net_final" in a["before"] and "net_final" in a["after"]
    assert any(a["kind"] == "kasbon_reversal" and a["cash_advance_id"] for a in mine)
    p = next(x for x in requests.get(f"{API}/payroll/periods", headers=admin).json() if x["id"] == S["pid"])
    assert p["adjustment_count"] >= 6 and p["adjustment_net"] == det["adjustment_net"]
    logs = requests.get(f"{API}/audit", headers=admin, params={"entity": "payroll_period", "limit": 50}).json()
    adj = [x for x in logs if x["action"] == "payroll_adjusted" and x["entity_id"] == str(S["pid"])]
    assert len(adj) >= 6
    assert any(x["after"].get("reason") == "TEST_salah potong kasbon" for x in adj)


# PDFs include corrections
def test_pdfs(admin):
    r = requests.get(f"{API}/payroll/periods/{S['pid']}/recap.pdf", headers=admin, timeout=60)
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/pdf") and r.content[:4] == b"%PDF"
    r = requests.get(f"{API}/payroll/periods/{S['pid']}/slip/{S['eid']}.pdf", headers=admin, timeout=60)
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/pdf") and r.content[:4] == b"%PDF"
    open("/tmp/slip_adj.pdf", "wb").write(r.content)
