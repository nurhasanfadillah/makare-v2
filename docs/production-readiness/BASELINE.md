# Baseline MAKARE

Tanggal pemeriksaan: 2026-10-31 (Asia/Jakarta)

## Git dan struktur

- Branch: `main`, tracking `origin/main`.
- Working tree awal: satu untracked directory `doc/` (berisi spesifikasi/prompt; dipertahankan).
- Stack yang tampak dari source: React 19 / CRA + CRACO, FastAPI 0.110 + asyncpg/PostgreSQL.
- Struktur: backend modular per route; frontend halaman React; skema saat ini disiapkan melalui `backend/schema.py` ketika aplikasi mulai.
- CI, migration ter-version, deployment manifest, dan prosedur restore tidak ditemukan dalam inventaris file yang terlihat.

## Baseline command

- Pemeriksaan status dan inventaris file dilakukan.
- Test, lint, build, koneksi database, staging, dan dependency audit tidak dijalankan pada baseline ini. Target DB non-production tidak dapat dikonfirmasi dari konfigurasi yang dibaca; data lokal/environment sengaja tidak diekspos.
- Tidak ada klaim kelulusan runtime atau test.

## Verifikasi lanjutan

- Pada sesi berikutnya, `backend/tests/test_rules.py` dan `backend/tests/test_attendance_validation.py` dijalankan di `backend/.venv` (pytest 9.1.1, pytest-xdist 3.8.0, tzdata 2026.5 dan dependency backend terpilih sesuai pin): **49 passed, exit code 0**. `backend/pytest.ini` tidak diubah.
- Tes API/database, build frontend, staging, dependency audit, security runtime, backup/restore dan UAT tetap belum dijalankan. Target database belum dikonfirmasi non-production.

## Sumber rencana

- `memory/PRD.md`: status produk, backlog, keputusan terbuka, dan next tasks.
- `doc/MAKARE_Spesifikasi_Lengkap_v1.1.md`: spesifikasi fitur, acceptance criteria, aturan bisnis, tahapan.
- `doc/MAKARE_2_Master_Execution_Prompt_Production_Readiness.md`: audit, keselamatan, tahapan release, dan kewajiban tracker.
- `doc/MAKARE_MASTER IMPLEMENTATION PROMPT FOR BUILD.md`: mandat implementasi dan UI/UX.
