import secrets
import os
import re
import hashlib
from pathlib import Path
import bcrypt
from core import today_wib

def hash_secret(s: str) -> str:
    return bcrypt.hashpw(s.encode(), bcrypt.gensalt()).decode()


def default_settings():
    t = today_wib()
    return {
        "company_name": "Redone",
        "company_address": "",
        "work_days": [1, 2, 3, 4, 5, 6],
        "start_time": "08:00",
        "end_time": "17:00",
        "breaks": [{"start": "12:00", "end": "13:00"}],
        "late_tolerance_minutes": 30,
        "first_hour_rule": True,
        "rounding_threshold_minutes": 30,
        "max_regular_minutes": 480,
        "early_leave_requires_pin": True,
        "early_pin_ttl_minutes": 15,
        "overtime_enabled": True,
        "overtime_break_minutes": 0,
        "overtime_break_after_minutes": 240,
        "overtime_pin_hash": None,
        "kiosk_enabled": True,
        "kiosk_token": secrets.token_urlsafe(24),
        "payroll_start_date": t.replace(day=1).isoformat(),
    }


def initial_admin_from_env(env=None):
    source = os.environ if env is None else env
    username = (source.get("INITIAL_ADMIN_USERNAME") or "").strip().lower()
    password = source.get("INITIAL_ADMIN_PASSWORD") or ""
    full_name = (source.get("INITIAL_ADMIN_FULL_NAME") or "Administrator").strip()
    if not username and not password:
        return None
    if not re.fullmatch(r"[a-z0-9_.]{3,32}", username):
        raise RuntimeError("INITIAL_ADMIN_USERNAME must be 3-32 lowercase letters, digits, dots, or underscores")
    if len(password) < 12 or len(password.encode("utf-8")) > 72:
        raise RuntimeError("INITIAL_ADMIN_PASSWORD must be 12-72 UTF-8 bytes")
    if not 2 <= len(full_name) <= 80:
        raise RuntimeError("INITIAL_ADMIN_FULL_NAME must be 2-80 characters")
    return username, password, full_name


async def init_db(pool):
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("SELECT pg_advisory_xact_lock(424242)")
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations(
                  version TEXT PRIMARY KEY,
                  checksum TEXT NOT NULL,
                  applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
            """)
            migration_dir = Path(__file__).parent / "migrations"
            migrations = sorted(migration_dir.glob("*.sql"))
            if not migrations:
                raise RuntimeError("No database migrations found; refusing to start without a schema")
            registered = await conn.fetch("SELECT version FROM schema_migrations")
            known_versions = {migration.name for migration in migrations}
            unknown_versions = {record["version"] for record in registered} - known_versions
            if unknown_versions:
                raise RuntimeError(
                    "Database contains migrations missing from this release: "
                    + ", ".join(sorted(unknown_versions))
                )
            for migration in migrations:
                sql = migration.read_text(encoding="utf-8")
                checksum = hashlib.sha256(sql.encode("utf-8")).hexdigest()
                version = migration.name
                applied = await conn.fetchrow(
                    "SELECT checksum FROM schema_migrations WHERE version=$1", version
                )
                if applied:
                    if applied["checksum"] != checksum:
                        raise RuntimeError(f"Applied migration checksum changed: {version}")
                    continue
                await conn.execute(sql)
                await conn.execute(
                    "INSERT INTO schema_migrations(version,checksum) VALUES($1,$2)",
                    version, checksum,
                )
            await conn.execute("INSERT INTO settings(key,value) VALUES('app',$1) ON CONFLICT (key) DO NOTHING", default_settings())
            if not await conn.fetchval("SELECT 1 FROM users LIMIT 1"):
                initial_admin = initial_admin_from_env()
                if not initial_admin:
                    raise RuntimeError("Set INITIAL_ADMIN_USERNAME and INITIAL_ADMIN_PASSWORD before initializing an empty users table")
                u, p, n = initial_admin
                await conn.execute(
                    "INSERT INTO users(username,password_hash,full_name,role) VALUES($1,$2,$3,'admin') ON CONFLICT (username) DO NOTHING",
                    u, hash_secret(p), n,
                )
            if not await conn.fetchval("SELECT 1 FROM departments LIMIT 1"):
                await conn.executemany("INSERT INTO departments(name) VALUES($1) ON CONFLICT DO NOTHING",
                                       [(x,) for x in ["Produksi", "Gudang", "Administrasi"]])
