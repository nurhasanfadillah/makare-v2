# MAKARE — Manajemen Karyawan Redone

Aplikasi manajemen karyawan berbahasa Indonesia: data karyawan, absensi (manual, sesi, kiosk), lembur, kasbon, penggajian, dan tutup buku atomik.

## Stack
- Frontend: React (CRA) + Tailwind + shadcn/ui (`frontend/`)
- Backend: FastAPI + asyncpg → PostgreSQL/Neon (`backend/`)

## Environment
Backend (`backend/.env`, lihat `backend/.env.example`): `DATABASE_URL`, `DATABASE_MIGRATION_URL` (opsional), `DATABASE_SSL_MODE`, `JWT_SECRET`, `CORS_ORIGINS`, `INITIAL_ADMIN_USERNAME`, dan `INITIAL_ADMIN_PASSWORD`. Atas arahan pemilik, implementasi saat ini memakai `DATABASE_URL` Neon yang tersedia untuk request runtime dan migrations; `DATABASE_MIGRATION_URL` bisa ditambahkan kemudian untuk direct endpoint di branch/database yang sama. Neon merekomendasikan endpoint direct untuk migrasi dan pooled untuk request runtime. SSL wajib untuk Neon/deployment; SSL disable hanya untuk environment local/development/test. `CORS_ORIGINS` harus berisi origin frontend secara eksplisit, dipisahkan koma; wildcard tidak diterima. Untuk dev lokal gunakan origin frontend lokal. Untuk deployment, masukkan hanya domain frontend deployment.
Frontend (`frontend/.env`, lihat `frontend/.env.example`): `REACT_APP_BACKEND_URL` (URL backend tanpa `/api`).

## Menjalankan lokal
```bash
cd backend && pip install -r requirements.txt && uvicorn server:app --host 0.0.0.0 --port 8001
cd frontend && yarn install && yarn start
```
Skema database dibuat otomatis saat backend start. Pada database baru tanpa user, set `INITIAL_ADMIN_USERNAME` dan `INITIAL_ADMIN_PASSWORD` sebelum backend dijalankan; password bootstrap harus unik dan minimal 12 karakter. Setelah admin pertama dibuat, variabel bootstrap tidak mengubah akun yang ada. Admin dapat membuat akun operator dari halaman pengaturan.

## Tes
```bash
cd backend && python -m pytest tests/test_rules.py
```
