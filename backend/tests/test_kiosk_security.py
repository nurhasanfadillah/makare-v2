import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kiosk_security import kiosk_pin_scope, pin_scope_locked, record_pin_attempt  # noqa: E402


def test_pin_lockout_is_scoped_to_kiosk_and_source():
    first_ip = kiosk_pin_scope("kiosk-token", "192.0.2.10")
    second_ip = kiosk_pin_scope("kiosk-token", "192.0.2.11")
    other_kiosk = kiosk_pin_scope("rotated-token", "192.0.2.10")
    attempts = {}

    for n in range(5):
        attempts = record_pin_attempt(attempts, first_ip, 1_000 + n, succeeded=False)

    assert pin_scope_locked(attempts, first_ip, 1_005)
    assert not pin_scope_locked(attempts, second_ip, 1_005)
    assert not pin_scope_locked(attempts, other_kiosk, 1_005)


def test_success_clears_only_that_source_lockout_state():
    first_ip = kiosk_pin_scope("kiosk-token", "192.0.2.10")
    second_ip = kiosk_pin_scope("kiosk-token", "192.0.2.11")
    attempts = {}
    for n in range(5):
        attempts = record_pin_attempt(attempts, first_ip, 2_000 + n, succeeded=False)
        attempts = record_pin_attempt(attempts, second_ip, 2_000 + n, succeeded=False)

    attempts = record_pin_attempt(attempts, first_ip, 2_006, succeeded=True)

    assert not pin_scope_locked(attempts, first_ip, 2_006)
    assert pin_scope_locked(attempts, second_ip, 2_006)


def test_lockout_and_failure_window_expire():
    scope = kiosk_pin_scope("kiosk-token", "192.0.2.10")
    attempts = {}
    for n in range(5):
        attempts = record_pin_attempt(attempts, scope, 3_000 + n, succeeded=False)

    assert pin_scope_locked(attempts, scope, 3_100)
    assert not pin_scope_locked(attempts, scope, 3_905)
    attempts = record_pin_attempt(attempts, scope, 3_905, succeeded=False)
    assert attempts[scope]["failures"] == 1
