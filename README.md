# MAKARE — Manajemen Karyawan Redone

Aplikasi manajemen karyawan berbahasa Indonesia: data karyawan, absensi (manual, sesi, kiosk), lembur, kasbon, penggajian, dan tutup buku atomik.

## Stack
- Frontend: React (CRA) + Tailwind + shadcn/ui (`frontend/`)
- Backend: FastAPI + asyncpg → PostgreSQL/Neon (`backend/`)

## Environment
Backend (`backend/.env`, lihat `backend/.env.example`): `DATABASE_URL`, `JWT_SECRET`, `CORS_ORIGINS`.
Frontend (`frontend/.env`, lihat `frontend/.env.example`): `REACT_APP_BACKEND_URL` (URL backend tanpa `/api`).

## Menjalankan lokal
```bash
cd backend && pip install -r requirements.txt && uvicorn server:app --host 0.0.0.0 --port 8001
cd frontend && yarn install && yarn start
```
Skema database dibuat otomatis saat backend start. Akun awal: `admin` / `admin123`, `operator` / `operator123` — segera ganti setelah login.

## Tes
```bash
cd backend && python -m pytest tests/test_rules.py
```
