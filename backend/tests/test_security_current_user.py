import asyncio
import os
import sys
from pathlib import Path

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

os.environ.setdefault("JWT_SECRET", "unit-test-signing-key-not-used-for-real-tokens")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import security  # noqa: E402


class FakePool:
    def __init__(self):
        self.user = {"id": 7, "username": "worker", "full_name": "Worker", "role": "admin", "active": True, "session_version": 0}
        self.fetches = 0

    async def fetchrow(self, query, uid):
        assert uid == 7
        self.fetches += 1
        return dict(self.user)


def test_current_user_reads_live_role_on_every_request(monkeypatch):
    pool = FakePool()
    monkeypatch.setattr(security, "get_pool", lambda: _resolved(pool))
    monkeypatch.setattr(security, "decode_token", lambda token: {"sub": "7", "typ": "session"})
    cred = HTTPAuthorizationCredentials(scheme="Bearer", credentials="unit-test-token")

    first = asyncio.run(security.current_user(cred))
    pool.user["role"] = "operator"
    second = asyncio.run(security.current_user(cred))

    assert first["role"] == "admin"
    assert second["role"] == "operator"
    assert pool.fetches == 2


def test_current_user_rejects_account_deactivated_after_token_issue(monkeypatch):
    pool = FakePool()
    pool.user["active"] = False
    monkeypatch.setattr(security, "get_pool", lambda: _resolved(pool))
    monkeypatch.setattr(security, "decode_token", lambda token: {"sub": "7", "typ": "session"})
    cred = HTTPAuthorizationCredentials(scheme="Bearer", credentials="unit-test-token")

    try:
        asyncio.run(security.current_user(cred))
    except HTTPException as exc:
        assert exc.status_code == 401
    else:
        raise AssertionError("Inactive account must be rejected")


def test_current_user_rejects_token_after_session_version_changes(monkeypatch):
    pool = FakePool()
    monkeypatch.setattr(security, "get_pool", lambda: _resolved(pool))
    monkeypatch.setattr(security, "decode_token", lambda token: {"sub": "7", "sv": 0, "typ": "session"})
    cred = HTTPAuthorizationCredentials(scheme="Bearer", credentials="revoked-token")
    pool.user["session_version"] = 1

    try:
        asyncio.run(security.current_user(cred))
    except HTTPException as exc:
        assert exc.status_code == 401
    else:
        raise AssertionError("Revoked session must be rejected")


async def _resolved(value):
    return value
