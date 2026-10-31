# Rencana Eksekusi Lanjutan MAKARE

Tanggal: 2026-10-31
Basis: [PRD konsolidasi](../../memory/PRD.md), [Master Plan Tracker](./MASTER-PLAN-TRACKER.md), Spesifikasi Lengkap v1.1, Master Implementation Prompt, MAKARE 2 Master Execution Prompt.

Keputusan pemilik tentang urutan database-first dan audit setelah semua modul: [OWNER-WORKFLOW-DECISIONS.md](./OWNER-WORKFLOW-DECISIONS.md).

## Sasaran

Menyelesaikan seluruh cakupan produk MAKARE dan menghasilkan release candidate dengan bukti yang dapat diaudit. Keberadaan source/test bukan kriteria lulus; setiap item tracker harus diuji dari UI/API sampai database dan aturan bisnis yang relevan. Tidak ada akses tulis ke production. Staging/DB hanya boleh digunakan setelah target dipastikan non-production.

## Urutan kerja yang disepakati

Prioritasnya adalah **lengkapi semua modul produk terlebih dahulu, lalu lakukan audit menyeluruh lintas modul**. Pemeriksaan ringan yang dibutuhkan untuk menyelesaikan satu modul (misalnya build frontend dan unit/model test yang memang sudah ada) tetap boleh dilakukan agar perubahan tidak merusak pekerjaan. Pemeriksaan itu bukan pengganti audit akhir dan tidak membuat status acceptance menjadi lulus.

1. Inventaris setiap acceptance criterion P-01–P-42 terhadap route/UI/schema yang benar-benar ada. Bedakan `belum dibuat`, `parsial`, `implementasi ada`, dan `terverifikasi`; catat keputusan bisnis yang belum ada.
2. Susun dan kerjakan gap dalam urutan dependensi: identitas/akun/settings/karyawan; absensi dan kiosk; kasbon, payroll dan tutup buku; riwayat, laporan/PDF dan dashboard; lalu migration, test harness, dan kebutuhan operasional yang termasuk scope.
3. Tutup setiap modul dengan implementasi vertical slice lengkap dan pemeriksaan ringan yang diperlukan. Jangan menyebutnya terverifikasi lintas sistem.
4. Setelah seluruh gap implementasi tertutup atau pemilik menyetujui penundaan tertulis, bekukan scope dan jalankan audit menyeluruh: route/API/database/role, validasi dan gagal jaringan, perhitungan, snapshot, migrasi, report, security/privacy, UI/responsif/aksesibilitas, concurrency, serta bukti build/test.
5. Kerjakan temuan audit, ulangi acceptance terdampak, lalu susun laporan status final dan release gate.

Gap implementasi pertama yang sudah dikonfirmasi: P-05 memiliki endpoint detail karyawan tetapi belum memiliki halaman detail/change-history; P-42 belum memiliki matriks penerimaan yang memetakan semua aturan ke pemeriksaan. Halaman detail P-05 dan peta coverage P-42 kini ditambahkan; acceptance runtime P-05 serta test yang masih kosong dalam matriks tetap harus diselesaikan. Keputusan P-14/DEC-03–05 yang memengaruhi hasil gaji harus dikunci sebelum menerima modul payroll sebagai lengkap.

## Jalur utama dan batch

### Batch 0 — Amankan sumber dan siapkan baseline eksekusi

**Pekerjaan**
- Jangan menimpa perubahan user yang sudah ada; pertahankan `doc/` dan perubahan Catatan Karyawan.
- Periksa diff, branch/HEAD, versi runtime, lockfile, environment variable names (tanpa membaca atau mencetak nilainya), test runner, dan apakah frontend dependencies tersedia.
- Siapkan database lokal/sintetis sebagai bagian dari penyelesaian modul, bukan baru pada audit akhir. Pastikan target terbukti non-production sebelum koneksi, migration, atau operasi tulis; bila runtime belum tersedia, kerjakan source-safe dan catat persiapan yang kurang.
- Pemilik merotasi kredensial plaintext yang ditemukan di dokumen sumber melalui jalur aman. Jangan memindahkan credential ke repo atau output.

**Keluar batch jika** baseline dan environment test diketahui; secret issue sudah ditangani pemilik atau ditandai tetap terbuka tanpa menghalangi audit statis.

**Tracker:** AUD-01, REL-02.
**Artefak:** BASELINE.md diperbarui dengan command, exit code, runtime/dependency, keterbatasan.

### Batch 1 — Lengkapi modul inti waktu dan payroll (vertical slice + pemeriksaan terarah)

**Urutan**
1. Trace perhitungan payroll manual dan hourly: `rules.py` → `services.py` → preview/finalize route → UI form/preview → snapshot/PDF.
2. Pastikan payroll manual menghitung jumlah semua `amount × volume`; attendance tidak menentukan gaji manual; komponen yang dipakai masuk snapshot.
2a. Halaman admin `/gaji-manual` menampilkan server preview periode berjalan dan snapshot tertutup per pilihan periode; komponen master dapat diedit dari form karyawan, sedangkan snapshot final hanya-baca dan koreksi terlihat sebagai nilai efektif. Verifikasi UI terhadap periode kosong, current, closed, serta karyawan manual tanpa komponen.
2b. Closing preview sekarang menerima daftar komponen efektif per periode; finalisasi menyimpan daftar tersebut dalam snapshot. Jalankan acceptance isolated DB untuk tambah/ubah/hapus komponen, volume, pengaruh ke gross/net, retry, dan snapshot/PDF.
3. Pastikan default potongan kasbon Rp0 jika tidak ada override; validasi server membatasi saldo yang tersedia dan net sebelum kasbon; net akhir tidak negatif.
4. Telusuri attendance WIB, tanggal kerja shift malam, sesi terbuka, batas jadwal, break overlap, lateness tepat batas 30m, pengakuan blok jam pertama, dan pembulatan satu kali.
5. Telusuri finalisasi payroll: rentang, locking, transaksi rollback, hash idempotensi terhadap payload, snapshot immutable, kasbon deduction unik, dan adjustment pasca-tutup. Uji legacy key tanpa hash serta upgrade schema di DB sintetis sebelum staging.
6. Tambahkan/perbaiki test boundary, negative, combination, race/retry berdasarkan spec §§20; jalankan hanya terhadap fixture/DB sintetis yang terisolasi.
7. Perbaiki defect terkonfirmasi dan jalankan ulang test terkait serta regression lintas payroll/attendance.

**Keluar batch jika** setiap perilaku uang/waktu memiliki expected result tertulis, test aktual, exit code dan bukti; business ambiguity yang memengaruhi gaji tetap `NEEDS BUSINESS DECISION` dan jalur terkait belum dinyatakan pass.

**Prioritas tracker:** P-14–P-27, AUD-02–AUD-04, DEC-03–DEC-06.

### Batch 2 — Lengkapi dukungan database dan security boundary yang dibutuhkan modul

**Urutan**
1. Inventaris tabel/index/constraint/FK yang dideklarasikan source dan schema lokal yang aman; bandingkan schema notes/revisions sebelum rollout.
2. Pilih mekanisme migration versioned yang sesuai stack aktual. Buat migration non-destructive dan reversible/ber-rencana-pemulihan; uji DB kosong serta upgrade dari schema sintetis lama. Jangan deploy.
3. Uji Catatan Karyawan: admin list/create/update, revisi before update, audit actor/time, validasi kosong/batas panjang, employee tidak ada, operator/anon terlarang, data tidak muncul di kiosk/laporan publik.
4. Lengkapi implementasi authorization, ownership checks, PII restrictions, validation/error handling, audit metadata, dan replay controls yang dibutuhkan agar setiap modul berjalan aman. Jalankan pemeriksaan terarah untuk perubahan modul.
5. Catat konfigurasi CORS, JWT, bootstrap, proxy/rate-limit, request size, secret handling, log redaction dan dependency untuk audit final Batch 4. Perbaiki blocker keamanan yang mencegah modul dilengkapi; jangan klaim audit lengkap pada batch ini.

**Keluar batch jika** schema upgrade/rollback terbukti di non-prod, Catatan lulus alur API/UI/role, critical security findings ditutup atau tercatat dengan owner/mitigasi.

**Prioritas tracker:** P-01–P-04, P-17/P-19/P-28/P-37/P-38, AUD-05–AUD-12, DEC-01/02.

### Batch 3 — Lengkapi permukaan produk dan laporan

**Urutan**
- Pastikan detail karyawan dan riwayat perubahan tersedia, termasuk kebijakan akses PII.
- Inventaris setiap laporan di P-29–P-36; implementasikan item yang hilang: daftar pegawai PDF, rekap kehadiran PDF, attendance report, payroll report, kasbon report. Pastikan final period memakai snapshot + koreksi, dan filter/total konsisten.
- Rekonsiliasi dashboard role-specific, settings/audit effective policy, closing history, menu/routes, dan state empty/loading/error.
- Audit format Rupiah, tanggal DD/MM/YYYY, WIB, date picker, mobile card Absensi, responsive desktop/tablet, fokus keyboard, label/kontras.
- Putuskan konflik sudut gradien 110° vs 135° dengan pemilik sebelum mengubah token visual.

**Keluar batch jika** seluruh halaman/modul yang dijanjikan punya jalur navigasi, data nyata, validasi/error state dan acceptance; PDF/laporan direkonsiliasi ke source of truth.

**Prioritas tracker:** P-05, P-29–P-41, AUD-15, DEC-10.

### Batch 4 — Audit menyeluruh setelah modul lengkap, test harness, CI, dan observability

**Pekerjaan**
- Bekukan inventaris implementasi P-01–P-42 dan keputusan produk; pastikan gap fitur sudah ditutup atau disetujui tertulis untuk ditunda.
- Jalankan audit akhir lintas modul: API/UI/database/role, PII/logging, perhitungan dan snapshot, migrasi, error/loading state, reports/PDF, concurrency/idempotency, mobile/a11y, dan rute kiosk.
- Buat daftar temuan dengan bukti dan prioritas; perbaiki temuan, lalu ulangi acceptance terdampak.
- Buat CI backend/frontend berdasarkan toolchain yang terkunci: lint/static checks yang tersedia, unit/integration, schema/migration test, dependency check, frontend build.
- CI hanya memakai secret contoh dan database sintetis terisolasi; tidak punya jalur ke production.
- Tambah API/auth matrix, concurrency/idempotency, frontend critical-flow, smoke/E2E test yang disyaratkan MAKARE 2.
- Tambah structured log/request ID, health/readiness yang aman, petunjuk diagnosis; periksa log tidak memuat secret/PII.

**Keluar batch jika** workflow PR berjalan dan evidence tiap job disimpan; semua test yang gagal memiliki perbaikan atau status blocker jelas.

**Prioritas tracker:** P-42, AUD-13/AUD-14/AUD-16.

### Batch 5 — Operasi pemulihan dan dokumentasi

**Pekerjaan**
- Susun backup policy, retention/access; lakukan restore drill sungguhan pada DB non-production dan catat waktu, keberhasilan, serta batasannya.
- Susun deployment, rollback app/schema, rotasi secret, incident response/escalation, onboarding admin/operator dan SOP harian.
- Uji prosedur rollback dan restore tanpa menyentuh production.

**Keluar batch jika** backup benar-benar dapat dipulihkan di lingkungan isolasi dan runbook sesuai deployment yang benar-benar digunakan.

**Prioritas tracker:** REL-01–REL-04.

### Batch 6 — Staging, UAT, dan release gate

**Prasyarat**
- Batch P0 lulus; schema migration, security review, critical tests/build, backup/restore dan runbook memiliki bukti.
- Target staging dikonfirmasi non-production dan data sintetis/diizinkan.

**Pekerjaan**
- Jalankan smoke test login/role, attendance (termasuk overnight), kasbon, payroll manual/hourly, closing/snapshot, adjustment, kiosk, settings, notes, reports, mobile/error states, backup/restore dan rollback.
- Isi UAT checklist expected vs actual, status, bukti; hanya pemilik bisnis yang menyetujui UAT.
- Terbitkan security review dan release report yang mencantumkan commit, migration, hasil perintah, known issues, keputusan bisnis dan risiko residual.

**Keluar batch jika** release status hanya salah satu `READY FOR UAT`, `READY FOR PRODUCTION APPROVAL`, atau `BLOCKED` sesuai bukti; tidak pernah mengklaim production live tanpa deployment dan verifikasi nyata serta persetujuan.

**Prioritas tracker:** REL-05–REL-08.

## Keputusan/dependensi yang dapat menghentikan sub-batch

- DEC-01 multi-tenant: harus diputuskan sebelum perubahan schema ownership/multi-tenant.
- DEC-02 batas operator: sebelum finalizing policy dan authorization tests.
- DEC-03–DEC-06 aturan tarif, toleransi, jam pertama, istirahat dan rounding: sebelum menerima kalkulasi payroll sebagai benar.
- DEC-07 model approval/slip koreksi: sebelum perubahan approval semantics.
- DEC-08 sesi terbuka/nomor ID/transaksi batal: sebelum implementasi kebijakan terkait.
- DEC-09 cabang, pajak, currency, integrasi, retensi: pemilik harus memilih scope atau menunda tertulis.
- DEC-10 sudut gradien: sebelum perubahan token visual.

Pekerjaan yang tidak bergantung pada keputusan boleh berjalan paralel secara logis, tetapi tidak melakukan perubahan bersamaan pada file/schema yang berkonflik.

## Gate perubahan dan status

- Satu batch per perubahan logis; update tracker setelah command acceptance benar-benar dijalankan.
- Setiap command mencatat exit code dan ringkasan. `py_compile`/diff check bukan test acceptance.
- Jangan jalankan test yang menulis/menghapus data sampai target lokal/non-production dipastikan.
- Jangan menandai `DONE — VERIFIED` hanya karena implementasi atau test file tersedia.
- Jangan mengubah acceptance untuk membuat test pass tanpa persetujuan pemilik.
- Semua item plan wajib diselesaikan atau ditunda/dihapus dengan keputusan tertulis pemilik.
- Urutan aktif per 2026-10-31: default kasbon Rp0, rentang jam valid, alasan koreksi non-whitespace, deduplikasi overlap istirahat, clamp lembur ke akhir jadwal reguler, override komponen per-periode, dan payload-bound finalize idempotency sudah diperbaiki lokal. Suite rules/model terisolasi terakhir lulus 59 test di `backend/.venv`. Formula pengakuan jam memakai `floor((eligible + tolerance)/60)` untuk regular dan lembur; sumber setting toleransi dan interaksi jam pertama/istirahat masih perlu dikunci. API/DB regression hanya pada target non-production yang terkonfirmasi. Catatan Karyawan menunggu migration serta uji terisolasi.

## Bukan bagian dari rencana otomatis

- Tidak ada rewrite ke Next.js/TypeScript/Drizzle/Better Auth tanpa keputusan eksplisit; implementasi saat ini React/FastAPI.
- Tidak ada koneksi/mutasi database production, deploy production, perubahan secret/live CORS/DNS, atau pengiriman data ke pihak luar tanpa persetujuan dan target yang tervalidasi.
- Tidak ada klaim lulus untuk test, build, security, restore, UAT atau deployment sebelum hasil nyata tercatat.
