import secrets
import bcrypt
from core import today_wib

DDL = """
CREATE TABLE IF NOT EXISTS users(
  id SERIAL PRIMARY KEY,
  username TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  full_name TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('admin','operator')),
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS departments(
  id SERIAL PRIMARY KEY,
  name TEXT UNIQUE NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE SEQUENCE IF NOT EXISTS employee_code_seq START 1;
CREATE TABLE IF NOT EXISTS employees(
  id SERIAL PRIMARY KEY,
  code TEXT UNIQUE NOT NULL DEFAULT ('KRY-' || lpad(nextval('employee_code_seq')::text, 4, '0')),
  full_name TEXT NOT NULL,
  gender TEXT NOT NULL CHECK (gender IN ('L','P')),
  address TEXT,
  birth_date DATE,
  ktp TEXT,
  phone TEXT,
  department_id INT REFERENCES departments(id) ON DELETE SET NULL,
  join_date DATE NOT NULL,
  payroll_mode TEXT NOT NULL CHECK (payroll_mode IN ('hourly','manual')),
  regular_rate BIGINT NOT NULL DEFAULT 0 CHECK (regular_rate >= 0),
  overtime_rate BIGINT NOT NULL DEFAULT 0 CHECK (overtime_rate >= 0),
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS employee_components(
  id SERIAL PRIMARY KEY,
  employee_id INT NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  amount BIGINT NOT NULL CHECK (amount >= 0),
  volume NUMERIC(10,2) NOT NULL DEFAULT 1 CHECK (volume >= 0),
  note TEXT
);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value JSONB NOT NULL);
CREATE TABLE IF NOT EXISTS attendance(
  id SERIAL PRIMARY KEY,
  employee_id INT NOT NULL REFERENCES employees(id),
  work_date DATE NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('hadir','sakit','izin','alfa')),
  check_in TIMESTAMPTZ,
  check_out TIMESTAMPTZ,
  early_leave BOOLEAN NOT NULL DEFAULT FALSE,
  source TEXT NOT NULL,
  note TEXT,
  created_by TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(employee_id, work_date),
  CHECK (check_out IS NULL OR check_in IS NOT NULL),
  CHECK (check_out IS NULL OR check_out >= check_in)
);
CREATE UNIQUE INDEX IF NOT EXISTS attendance_one_open ON attendance(employee_id) WHERE status='hadir' AND check_out IS NULL;
CREATE TABLE IF NOT EXISTS overtime_sessions(
  id SERIAL PRIMARY KEY,
  employee_id INT NOT NULL REFERENCES employees(id),
  work_date DATE NOT NULL,
  check_in TIMESTAMPTZ NOT NULL,
  check_out TIMESTAMPTZ,
  source TEXT NOT NULL,
  created_by TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (check_out IS NULL OR check_out >= check_in)
);
CREATE UNIQUE INDEX IF NOT EXISTS overtime_one_open ON overtime_sessions(employee_id) WHERE check_out IS NULL;
CREATE TABLE IF NOT EXISTS early_leave_pins(
  id SERIAL PRIMARY KEY,
  attendance_id INT NOT NULL REFERENCES attendance(id) ON DELETE CASCADE,
  pin_hash TEXT NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  attempts INT NOT NULL DEFAULT 0,
  used_at TIMESTAMPTZ,
  created_by TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS payroll_periods(
  id SERIAL PRIMARY KEY,
  start_date DATE NOT NULL UNIQUE,
  end_date DATE NOT NULL UNIQUE,
  idempotency_key TEXT UNIQUE NOT NULL,
  totals JSONB NOT NULL,
  settings_snapshot JSONB NOT NULL,
  closed_by TEXT NOT NULL,
  closed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (end_date >= start_date)
);
CREATE TABLE IF NOT EXISTS payroll_snapshots(
  id SERIAL PRIMARY KEY,
  period_id INT NOT NULL REFERENCES payroll_periods(id),
  employee_id INT NOT NULL REFERENCES employees(id),
  data JSONB NOT NULL,
  gross BIGINT NOT NULL,
  net_before_kasbon BIGINT NOT NULL,
  kasbon_deduction BIGINT NOT NULL,
  net_final BIGINT NOT NULL CHECK (net_final >= 0),
  UNIQUE(period_id, employee_id)
);
CREATE TABLE IF NOT EXISTS cash_advances(
  id SERIAL PRIMARY KEY,
  employee_id INT NOT NULL REFERENCES employees(id),
  kind TEXT NOT NULL CHECK (kind IN ('grant','deduction')),
  amount BIGINT NOT NULL CHECK (amount > 0),
  tx_date DATE NOT NULL,
  note TEXT,
  period_id INT REFERENCES payroll_periods(id),
  created_by TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS kasbon_one_deduction ON cash_advances(period_id, employee_id) WHERE kind='deduction';
CREATE TABLE IF NOT EXISTS audit_logs(
  id BIGSERIAL PRIMARY KEY,
  actor TEXT NOT NULL,
  action TEXT NOT NULL,
  entity TEXT NOT NULL,
  entity_id TEXT,
  before JSONB,
  after JSONB,
  result TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


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
        "overtime_pin_hash": hash_secret("135790"),
        "kiosk_enabled": True,
        "kiosk_token": secrets.token_urlsafe(24),
        "payroll_start_date": t.replace(day=1).isoformat(),
    }


SEED_USERS = [("admin", "admin123", "Administrator", "admin"), ("operator", "operator123", "Operator Input", "operator")]


async def init_db(pool):
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("SELECT pg_advisory_xact_lock(424242)")
            await conn.execute(DDL)
            await conn.execute("INSERT INTO settings(key,value) VALUES('app',$1) ON CONFLICT (key) DO NOTHING", default_settings())
            for u, p, n, r in SEED_USERS:
                await conn.execute(
                    "INSERT INTO users(username,password_hash,full_name,role) VALUES($1,$2,$3,$4) ON CONFLICT (username) DO NOTHING",
                    u, hash_secret(p), n, r,
                )
            if not await conn.fetchval("SELECT 1 FROM departments LIMIT 1"):
                await conn.executemany("INSERT INTO departments(name) VALUES($1) ON CONFLICT DO NOTHING",
                                       [(x,) for x in ["Produksi", "Gudang", "Administrasi"]])
