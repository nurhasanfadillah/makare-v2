"""Pure helpers for source-scoped kiosk PIN lockout state."""
import hashlib


ATTEMPT_WINDOW_SECONDS = 300
LOCKOUT_SECONDS = 15 * 60
MAX_PIN_FAILURES = 5


def kiosk_pin_scope(token: str, source_ip: str) -> str:
    """Return a non-reversible settings key scoped to one kiosk link and source IP."""
    return hashlib.sha256(f"{token}\0{source_ip}".encode("utf-8")).hexdigest()


def prune_pin_attempts(attempts: dict, now: float) -> dict:
    return {
        key: value for key, value in attempts.items()
        if float(value.get("locked_until", 0)) > now
        or now - float(value.get("window_started", 0)) <= ATTEMPT_WINDOW_SECONDS
    }


def pin_scope_locked(attempts: dict, scope: str, now: float) -> bool:
    current = prune_pin_attempts(attempts, now).get(scope)
    return bool(current and float(current.get("locked_until", 0)) > now)


def record_pin_attempt(attempts: dict, scope: str, now: float, succeeded: bool) -> dict:
    updated = prune_pin_attempts(attempts, now)
    if succeeded:
        updated.pop(scope, None)
        return updated

    current = updated.get(scope, {})
    started = float(current.get("window_started", now))
    failures = int(current.get("failures", 0)) if now - started <= ATTEMPT_WINDOW_SECONDS else 0
    failures += 1
    updated[scope] = {
        "failures": failures,
        "window_started": now if failures == 1 else started,
        "locked_until": now + LOCKOUT_SECONDS if failures >= MAX_PIN_FAILURES else 0,
    }
    return updated
