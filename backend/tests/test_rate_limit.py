import asyncio
import time

from fastapi import HTTPException, Request
import pytest

import core


class FakeConnection:
    def __init__(self):
        self.counts = {}
        self.keys = []

    async def execute(self, _sql):
        return "DELETE 0"

    async def fetchval(self, sql, bucket_hash, _window):
        assert "ON CONFLICT(bucket_hash) DO UPDATE" in sql
        self.keys.append(bucket_hash)
        self.counts[bucket_hash] = self.counts.get(bucket_hash, 0) + 1
        return self.counts[bucket_hash]


class FakePool:
    def __init__(self, connection):
        self.connection = connection
        self.acquired = 0
        self.released = 0

    async def acquire(self):
        self.acquired += 1
        return self.connection

    async def release(self, _connection):
        self.released += 1


def request(forwarded="203.0.113.7, 10.0.0.1"):
    return Request({
        "type": "http", "http_version": "1.1", "method": "GET", "scheme": "https",
        "path": "/", "raw_path": b"/", "query_string": b"", "headers": [
            (b"x-forwarded-for", forwarded.encode("ascii")),
        ], "client": ("127.0.0.1", 1234), "server": ("example.test", 443),
    })


def test_rate_limit_is_shared_and_hashes_bucket_identity(monkeypatch):
    connection = FakeConnection()
    pool = FakePool(connection)
    monkeypatch.setattr(core, "get_pool", lambda: _async_value(pool))
    monkeypatch.setattr(core, "_last_rate_limit_cleanup", time.monotonic())

    async def scenario():
        await core.rate_limit(request(), "login:admin", 2, 300)
        await core.rate_limit(request(), "login:admin", 2, 300)
        with pytest.raises(HTTPException) as error:
            await core.rate_limit(request(), "login:admin", 2, 300)
        return error.value.status_code
    status = asyncio.run(scenario())

    assert status == 429
    assert connection.keys[0] == connection.keys[1] == connection.keys[2]
    assert len(connection.keys[0]) == 64
    assert "admin" not in connection.keys[0]
    assert pool.acquired == pool.released == 3


def test_rate_limit_reuses_an_existing_connection(monkeypatch):
    connection = FakeConnection()
    async def unexpected_pool():
        raise AssertionError("should reuse route connection")
    monkeypatch.setattr(core, "get_pool", unexpected_pool)
    monkeypatch.setattr(core, "_last_rate_limit_cleanup", time.monotonic())

    asyncio.run(core.rate_limit(request(), "kiosk", 5, 300, connection=connection))
    assert len(connection.keys) == 1


async def _async_value(value):
    return value
