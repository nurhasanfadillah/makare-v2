# Inventaris Skema MAKARE

Tanggal: 2026-10-31
Sumber: deklarasi DDL statis di `backend/schema.py`; tidak ada koneksi database yang dilakukan.

## Objek yang dideklarasikan

| Objek | Kolom/aturan penting | Domain |
|---|---|---|
| `users` | username unik, hash password, role admin/operator, active | akun dan RBAC |
| `departments` | nama unik | departemen |
| `employee_code_seq` | sequence employee code | identitas karyawan |
| `employees` | kode unik, status, payroll mode hourly/manual, tarif, join date, FK departemen | master karyawan |
| `employee_components` | employee FK cascade, nama, amount BIGINT nonnegative, volume NUMERIC(10,2), note | komponen gaji master |
| `employee_notes` | employee FK, judul/kategori/tanggal/isi, pembuat dan waktu | catatan karyawan |
| `employee_note_revisions` | snapshot nilai lama dan actor/waktu perubahan | riwayat catatan |
| `settings` | key + JSONB | konfigurasi aplikasi |
| `attendance` | employee/date unik, check constraints, status | absensi reguler |
| `overtime_sessions` | employee/date/waktu, check-out nullable | sesi lembur |
| `early_leave_pins` | FK absensi, hash PIN, TTL, attempt/use metadata | otorisasi pulang awal |
| `payroll_periods` | start/end unik, idempotency key unik, totals/settings JSONB, actor/time, payload hash nullable | periode tutup buku |
| `payroll_snapshots` | unique period/employee, data JSONB, gross/net/kasbon BIGINT | payroll final immutable |
| `cash_advances` | employee FK, grant/deduction/reversal, amount, tx date, period FK nullable | ledger kasbon |
| `payroll_adjustments` | period/employee FK, earning/deduction/reversal, before/after JSONB, idempotency | koreksi pasca tutup buku |
| `audit_logs` | actor/action/entity/before/after/result/time | audit |

Index eksplisit yang terlihat: `employee_notes_history`, `employee_note_revisions_history`, partial unique `attendance_one_open`, partial unique `overtime_one_open`, dan partial unique `kasbon_one_deduction`. PK, unique constraints dan FK lain dibuat lewat DDL tabel.

## Perubahan skema lokal sesi ini

`payroll_periods.finalize_payload_hash TEXT NULL` ditambahkan ke definisi tabel dan lewat `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`. Kolom menyimpan hash request finalisasi untuk menolak pemakaian idempotency key yang sama dengan payload berubah. Baris periode lama tetap `NULL` dan memakai perilaku retry legacy karena request historis tidak tersimpan. Perubahan ini aditif, tetapi belum diuji dengan PostgreSQL dan belum dipindah ke migration versioned.

Bootstrap source juga diubah: instalasi dengan tabel `users` kosong memerlukan konfigurasi env admin tervalidasi; tidak ada akun awal default yang ditanam source. PIN lembur default fresh install adalah `NULL`. Ini tidak mengubah akun/settings yang telah ada pada database mana pun; efek terhadap deployment belum diperiksa.

## Risiko startup DDL

- `init_db()` mengambil advisory lock lalu mengeksekusi seluruh DDL pada startup.
- Ada `ALTER TABLE cash_advances DROP CONSTRAINT IF EXISTS ...` diikuti `ADD CONSTRAINT ...` tanpa pemeriksaan kondisi data; setiap startup mencoba mengganti constraint. Ini memerlukan migrasi versioned dengan validasi data, bukan operasi runtime yang tidak tercatat.
- DDL menggunakan `CREATE TABLE/INDEX IF NOT EXISTS`; hal itu tidak mendeteksi drift pada definisi kolom, constraint, atau index yang sudah ada.
- Tidak terlihat migration ledger, versi aplikasi skema, prosedur downgrade, snapshot/restore sebelum upgrade, atau validasi schema terhadap DB target.
- `employee_notes` dan `employee_note_revisions` berada pada working tree yang belum committed; belum diketahui apakah deployment database memiliki objek tersebut.
- Katalog ini berasal dari source saja. Nama objek, tipe aktual, constraint, data lama, grants, dan drift pada database mana pun belum diverifikasi.

## Rencana Batch 2

1. Pastikan environment lokal PostgreSQL sintetis tersedia tanpa menggunakan `DATABASE_URL` dari `.env` atau shared secret.
2. Implementasikan versioned migration runner/ledger yang sesuai stack asyncpg dan berikan mekanisme lock/transaksi yang konsisten.
3. Susun baseline migration dari schema yang benar-benar disetujui; jangan mengasumsikan tabel Catatan Karyawan sudah deployed.
4. Buat migration aditif untuk hash finalisasi dan constraint kasbon; jalankan dari DB kosong dan fixture schema sebelumnya.
5. Uji constraint/index, data lama dengan hash `NULL`, idempotensi migrasi, dan kegagalan/rollback pada DB sintetis.
6. Setelah sistem migration teruji, rencanakan cutover dari startup DDL ke versioned migrations; jangan menghapus startup schema handling sebelum seluruh environment memiliki versi baseline.

**Status:** inventaris statis selesai; pemeriksaan terakhir juga tidak menemukan `.env` atau `DATABASE_URL` pada workspace/environment ini. Seluruh pemeriksaan live, upgrade, rollback, dan cutover `NOT RUN` sampai target DB lokal/non-production dikonfigurasi dan dibuktikan.
