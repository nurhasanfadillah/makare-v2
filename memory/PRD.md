# MAKARE — Manajemen Karyawan Redone (PRD)

## Original problem statement
MASTER IMPLEMENTATION PROMPT — MAKARE (Manajemen Karyawan Redone): aplikasi manajemen karyawan berbahasa Indonesia untuk data karyawan, absensi, jam kerja, lembur, kasbon, penggajian, catatan karyawan, laporan, dan tutup buku. UI final: Midnight Navy #0B1F3A, Royal Blue #174EA6, Gradient Blue #4F7DF3, Cool Canvas #F4F7FB, Surface #FFFFFF, gradasi 110deg #174EA6→#4F7DF3, mode terang, korporat premium seperti aplikasi perbankan. Peran: Administrator, Operator Input (absensi hari ini), Kiosk publik (token). Aturan bisnis: ID otomatis tak berubah, aktif/nonaktif, mode payroll Harian Berbasis Jam & Manual, status Hadir/Sakit/Izin/Alfa (Alfa tidak memotong gaji), jadwal global, waktu server WIB, shift lintas tengah malam ikut tanggal Masuk, durasi dalam menit, PIN keluar lebih awal berumur pendek terikat transaksi, kiosk tanpa antrean offline, lembur sesi terpisah ditolak server jika nonaktif, snapshot payroll final immutable, koreksi via penyesuaian, potongan kasbon = min(saldo, max(0, bersih sebelum kasbon)), tutup buku atomik & idempoten. Aturan keterlambatan (toleransi 30m, jam pertama gugur bila > toleransi), pembulatan 30 menit, kiosk layar penuh dengan tombol Masuk/Keluar bergantian, PIN lembur sekali per tab. (Lihat pesan pengguna lengkap untuk detail modul A–M, keamanan, dan arsitektur target Next.js/Neon/Drizzle — platform menggunakan React + FastAPI.)

User choices: Database = Neon PostgreSQL milik user (DATABASE_URL). Login = username+password (admin/admin123, operator/operator123). Cakupan rilis pertama = Inti dulu.

## Architecture
- Frontend: React (CRA, JS) + Tailwind + shadcn/ui + lucide; fonts Plus Jakarta Sans + IBM Plex Mono. Tokens in src/index.css.
- Backend: FastAPI + asyncpg → Neon Postgres. Files: core.py (pool, WIB, audit, rate-limit, settings cache), schema.py (DDL + idempotent seed), security.py (bcrypt + JWT HS256, roles), rules.py (pure payroll rules, unit-tested in tests/test_rules.py), services.py (clock, payroll build, atomic finalize), routes_admin.py, routes_attendance.py (attendance + kiosk), routes_payroll.py (preview/finalize/PDF via reportlab).
- Integrity: unique(employee, work_date), partial unique open-session indexes, advisory locks, idempotency_key unique, unique snapshot per (period, employee), unique kasbon deduction per (period, employee), closed dates locked.

## Personas
Administrator (full access), Operator Input (dashboard + today's attendance only), Kiosk publik (token link, no admin).

## Implemented (2026-10-25)
- Auth username/password, role enforcement server-side, login rate limit, audit log.
- Dashboard (real DB data), Data Karyawan (CRUD, filter, auto ID KRY-0001, deactivate, rates, manual components), Departemen CRUD, Akun CRUD.
- Absensi: Masuk/Keluar session (server time), Sakit/Izin/Alfa, admin historical input & correction with reason + before/after audit, early-leave PIN (6 digit, single-use, TTL, 5 attempts), overtime sessions (server rejects when disabled).
- Pengaturan: company, payroll start date, schedule, breaks, tolerance, first-hour rule, rounding, max regular, early-leave policy, overtime, kiosk enable/rotate, overtime PIN.
- Kasbon minimal: grant, ledger, balance; deductions only via tutup buku.
- Tutup Buku wizard (period → preview + adjust kasbon/potongan lain → confirm), atomic idempotent finalize, snapshots, Riwayat, Rekap Gaji PDF, Slip Gaji PDF.
- Kiosk: fullscreen, WIB server clock, search (active hourly only), Reguler/Lembur (PIN once per tab, persistent lockout after 5 wrong), alternating Masuk/Keluar, confirm, result, auto reset.
- Tested by testing agent iteration_1 (backend 93%, frontend 85%); all reported HIGH issues fixed afterwards (FK 500, XFF rate-limit bypass, edit form race, kiosk timer). Test data removed.

## Open product decisions (before production payroll)
- Arrival before schedule start: currently not counted (window starts at schedule start).
- Work days setting is stored but not yet used to flag non-work-day attendance.
- Overtime paid pro-rata per minute (no rounding); overtime break deducted when session ≥ threshold.
- Sessions without Keluar at closing are paid 0 (warning shown).
- Late within tolerance credits full first hour (late adjustment positive).

## Backlog
- P0: Mode Koreksi payroll (penyesuaian setelah tutup buku), Catatan Karyawan.
- P1: Laporan (Daftar Karyawan PDF, Rekap Kehadiran PDF, Laporan Kehadiran/Penggajian/Kasbon), detail karyawan & riwayat perubahan.
- P2: Performance (Neon region far from app ~200ms/roundtrip), backup/restore procedure doc, CI (GitHub Actions), shadcn date pickers, mobile card layout for Absensi.

## Next tasks
Mode Koreksi payroll + Catatan Karyawan, then reports.
