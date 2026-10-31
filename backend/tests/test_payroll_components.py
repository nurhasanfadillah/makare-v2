import asyncio
import os
import sys
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("JWT_SECRET", "test-only-secret-for-payroll-component-tests")
from routes_payroll import AdjustIn, PeriodComponentIn, _finalize_payload_hash, _ov  # noqa: E402
from rules import compute_pay  # noqa: E402
import services  # noqa: E402


def test_period_component_override_is_trimmed_and_serialized_for_payroll():
    adjustment = AdjustIn(components=[{
        "name": "  Insentif  ", "amount": 2000, "volume": "1.50", "note": "  Target tercapai  "
    }])

    override = _ov({"42": adjustment})["42"]["components"][0]
    pay = compute_pay("manual", 0, 0, 0, 0, [override], 0, 0)

    assert override == {"name": "Insentif", "amount": 2000, "volume": 1.5, "note": "Target tercapai"}
    assert pay["components_total"] == 3000
    assert pay["gross"] == 3000


def test_component_totals_use_exact_decimal_products_before_existing_half_even_rounding():
    # Binary float accumulation previously produced 30.500000000000004 and rounded to 31.
    components = [{"name": "Satuan", "amount": 305, "volume": "0.01"} for _ in range(10)]
    pay = compute_pay("manual", 0, 0, 0, 0, components, 0, 0)

    assert pay["components_total"] == 30
    half_even = compute_pay("manual", 0, 0, 0, 0,
                             [{"name": "Ties", "amount": 1, "volume": "2.5"}], 0, 0)
    assert half_even["components_total"] == 2


def test_hourly_rate_proration_keeps_exact_half_even_rounding():
    pay = compute_pay("hourly", 3, 9, 10, 10, [], 0, 0)

    assert pay["regular_amount"] == 0  # Rp0.50 rounds to the nearest even Rupiah.
    assert pay["overtime_amount"] == 2  # Rp1.50 rounds to the nearest even Rupiah.


@pytest.mark.parametrize("volume", ["1.001", "100000000"])
def test_period_component_override_rejects_volume_outside_schema_precision(volume):
    with pytest.raises(ValidationError):
        PeriodComponentIn(name="Bonus", amount=1000, volume=volume)


@pytest.mark.parametrize("name", ["", "   "])
def test_period_component_override_rejects_blank_name(name):
    with pytest.raises(ValidationError):
        PeriodComponentIn(name=name, amount=1000, volume=1)


def test_period_component_override_rejects_negative_amount():
    with pytest.raises(ValidationError):
        PeriodComponentIn(name="Bonus", amount=-1, volume=1)


def test_build_payroll_uses_period_components_in_effective_line(monkeypatch):
    async def settings(_conn):
        return {"start_time": "08:00", "end_time": "17:00", "breaks": [], "overtime_break_minutes": 0,
                "overtime_break_after_minutes": 0, "regular_rate": 0, "late_tolerance_minutes": 0,
                "first_hour_rule": False, "rounding_threshold_minutes": 30, "max_regular_minutes": 480}

    class Connection:
        async def fetch(self, query, *_args):
            if "FROM employees e LEFT JOIN departments" in query:
                return [{"id": 42, "code": "KRY-0042", "full_name": "Uji Manual", "department": None,
                         "payroll_mode": "manual", "regular_rate": 0, "overtime_rate": 0}]
            if "FROM employee_components" in query:
                return [{"employee_id": 42, "name": "Master", "amount": 1000, "volume": 1, "note": None}]
            return []

    monkeypatch.setattr(services, "get_settings", settings)
    components = [{"name": "Insentif periode", "amount": 2000, "volume": 1.5, "note": None}]
    result = asyncio.run(services.build_payroll(Connection(), date(2026, 1, 1), date(2026, 1, 31),
                                                {"42": {"components": components}}))

    line = result["lines"][0]
    assert line["components"] == components
    assert line["gross"] == 3000
    assert result["totals"]["gross"] == 3000


def test_finalize_payload_hash_is_stable_for_equivalent_normalized_payloads():
    a = AdjustIn(other_deduction=0, components=[{"name": " Bonus ", "amount": 2500, "volume": "1.50"}])
    b = AdjustIn(components=[{"name": "Bonus", "amount": 2500, "volume": 1.5}], other_deduction=0)
    date_end = date(2026, 1, 31)

    assert _finalize_payload_hash(date_end, {"42": a}) == _finalize_payload_hash(date_end, {"42": b})
    assert _finalize_payload_hash(date_end, {"42": a}) != _finalize_payload_hash(date(2026, 2, 1), {"42": b})


class _Transaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False


class _ExistingFinalizeConnection:
    def __init__(self, payload_hash):
        self.payload_hash = payload_hash

    def transaction(self):
        return _Transaction()

    async def execute(self, *_args):
        return "SELECT 1"

    async def fetchrow(self, *_args):
        return {"id": 7, "finalize_payload_hash": self.payload_hash}


def test_finalize_retry_with_same_payload_returns_existing_period():
    result = asyncio.run(services.finalize_closing(
        _ExistingFinalizeConnection("same-hash"), date(2026, 1, 31), "key-12345678", {}, "admin", "same-hash"))

    assert result == {"period_id": 7, "duplicate": True}


def test_finalize_reused_key_with_different_payload_returns_conflict():
    with pytest.raises(HTTPException) as error:
        asyncio.run(services.finalize_closing(
            _ExistingFinalizeConnection("original-hash"), date(2026, 1, 31), "key-12345678", {}, "admin", "changed-hash"))

    assert error.value.status_code == 409
