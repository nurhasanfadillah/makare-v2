import os
import json
import time
from collections import defaultdict, deque
from datetime import datetime, date
from zoneinfo import ZoneInfo
from pathlib import Path

import asyncpg
from dotenv import load_dotenv
from fastapi import HTTPException, Request

load_dotenv(Path(__file__).parent / ".env")

WIB = ZoneInfo("Asia/Jakarta")
_pool = None


def now_wib() -> datetime:
    return datetime.now(WIB)


def today_wib() -> date:
    return now_wib().date()


async def _init_conn(conn):
    await conn.set_type_codec("jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog")
    await conn.execute("SET TIME ZONE 'Asia/Jakarta'")


async def get_pool():
    global _pool
    if _pool is None:
        url = os.environ["DATABASE_URL"].split("?")[0]
        _pool = await asyncpg.create_pool(url, ssl="require", min_size=1, max_size=8, init=_init_conn)
    return _pool


async def close_pool():
    if _pool is not None:
        await _pool.close()


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


_hits = defaultdict(deque)


def rate_limit(request: Request, bucket: str, limit: int, window: int):
    # Last hop is appended by the trusted ingress; earlier values are client-controlled.
    ip = (request.headers.get("x-forwarded-for") or (request.client.host if request.client else "")).split(",")[-1].strip()
    key = f"{bucket}:{ip}"
    q = _hits[key]
    t = time.monotonic()
    while q and t - q[0] > window:
        q.popleft()
    if len(q) >= limit:
        err(429, "Terlalu banyak percobaan. Coba lagi beberapa saat.")
    q.append(t)


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
