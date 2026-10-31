import os
import json
import time
import hashlib
from datetime import datetime, date
from zoneinfo import ZoneInfo
from pathlib import Path
from urllib.parse import urlsplit

import asyncpg
from dotenv import load_dotenv
from fastapi import HTTPException, Request

load_dotenv(os.environ.get("MAKARE_ENV_FILE", Path(__file__).parent / ".env"))

WIB = ZoneInfo("Asia/Jakarta")
_pool = None
_migration_pool = None


def now_wib() -> datetime:
    return datetime.now(WIB)


def today_wib() -> date:
    return now_wib().date()


async def _init_conn(conn):
    await conn.set_type_codec("jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog")
    await conn.execute("SET TIME ZONE 'Asia/Jakarta'")


async def _create_pool(database_url: str, max_size: int):
    # asyncpg receives the connection string without provider-specific query
    # options; TLS policy is passed explicitly and disabled only for local/test.
    url = urlsplit(database_url)._replace(query="").geturl()
    from config import database_ssl_mode
    ssl_mode = database_ssl_mode(os.environ.get("DATABASE_SSL_MODE"), os.environ.get("APP_ENV"))
    return await asyncpg.create_pool(url, ssl=ssl_mode, min_size=1, max_size=max_size, init=_init_conn)


async def get_pool():
    global _pool
    if _pool is None:
        _pool = await _create_pool(os.environ["DATABASE_URL"], max_size=8)
    return _pool


async def get_migration_pool():
    global _migration_pool
    if _migration_pool is None:
        from config import migration_database_url
        runtime_url = os.environ["DATABASE_URL"]
        url = migration_database_url(runtime_url, os.environ.get("DATABASE_MIGRATION_URL"))
        _migration_pool = await _create_pool(url, max_size=1)
    return _migration_pool


async def close_pool():
    global _migration_pool, _pool
    if _migration_pool is not None:
        await _migration_pool.close()
        _migration_pool = None
    if _pool is not None:
        await _pool.close()
        _pool = None


def err(status: int, message: str):
    raise HTTPException(status_code=status, detail=message)


async def audit(conn, actor: str, action: str, entity: str, entity_id=None, before=None, after=None, result="success"):
    await conn.execute(
        "INSERT INTO audit_logs(actor, action, entity, entity_id, before, after, result) VALUES($1,$2,$3,$4,$5,$6,$7)",
        actor, action, entity, None if entity_id is None else str(entity_id), before, after, result,
    )


_settings_cache = {"value": None, "at": 0.0}


async def get_settings(conn) -> dict:
    if _settings_cache["value"] is None or time.monotonic() - _settings_cache["at"] > 15:
        _settings_cache["value"] = await conn.fetchval("SELECT value FROM settings WHERE key='app'")
        _settings_cache["at"] = time.monotonic()
    return dict(_settings_cache["value"])


def invalidate_settings():
    _settings_cache["value"] = None


async def last_closed_end(conn):
    return await conn.fetchval("SELECT max(end_date) FROM payroll_periods")


async def ensure_open_date(conn, d: date):
    end = await last_closed_end(conn)
    if end and d <= end:
        err(409, "Tanggal berada dalam periode yang sudah tutup buku")


_last_rate_limit_cleanup = 0.0


def client_ip(request: Request) -> str:
    # Last hop is appended by the trusted ingress; earlier values are client-controlled.
    return (request.headers.get("x-forwarded-for") or (request.client.host if request.client else "")).split(",")[-1].strip()


async def rate_limit(request: Request, bucket: str, limit: int, window: int, connection=None):
    """Enforce a shared, database-backed fixed-window limit across API instances."""
    global _last_rate_limit_cleanup
    ip = client_ip(request)
    key = hashlib.sha256(f"{bucket}:{ip}".encode("utf-8")).hexdigest()
    own_connection = connection is None
    if own_connection:
        pool = await get_pool()
        connection = await pool.acquire()
    try:
        now = time.monotonic()
        if now - _last_rate_limit_cleanup >= 300:
            await connection.execute("DELETE FROM api_rate_limits WHERE expires_at <= now()")
            _last_rate_limit_cleanup = now
        hits = await connection.fetchval(
            "INSERT INTO api_rate_limits(bucket_hash, window_started_at, hits, expires_at) "
            "VALUES($1, now(), 1, now() + ($2 * interval '1 second')) "
            "ON CONFLICT(bucket_hash) DO UPDATE SET "
            "hits=CASE WHEN api_rate_limits.window_started_at <= now() - ($2 * interval '1 second') "
            "THEN 1 ELSE api_rate_limits.hits + 1 END, "
            "window_started_at=CASE WHEN api_rate_limits.window_started_at <= now() - ($2 * interval '1 second') "
            "THEN now() ELSE api_rate_limits.window_started_at END, "
            "expires_at=now() + ($2 * interval '1 second') RETURNING hits",
            key, window,
        )
    finally:
        if own_connection:
            await pool.release(connection)
    if hits > limit:
        err(429, "Terlalu banyak percobaan. Coba lagi beberapa saat.")


def row(r):
    if r is None:
        return None
    out = {}
    for k, v in dict(r).items():
        if isinstance(v, (datetime, date)):
            v = v.isoformat()
        out[k] = v
    return out


def rows(rs):
    return [row(r) for r in rs]
