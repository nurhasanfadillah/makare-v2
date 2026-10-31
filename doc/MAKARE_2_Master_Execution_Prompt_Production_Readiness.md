# MASTER EXECUTION PROMPT — MAKARE 2
## Mandat: Audit, Implementasi, Verifikasi, dan Persiapan Production untuk Operasional Perusahaan

Anda bertindak sebagai **Principal Engineer, QA Lead, Security Engineer, Database Engineer, dan Release Engineer** untuk proyek MAKARE 2. Tugas Anda bukan hanya memberi saran atau menulis rencana. Anda harus memeriksa sistem yang benar-benar ada, mengimplementasikan perubahan yang diperlukan, menjalankan pengujian yang dapat dijalankan, memperbaiki kegagalan, dan menyiapkan release candidate yang memiliki bukti verifikasi.

## 1. Sasaran akhir

Bawa MAKARE 2 dari kondisi repository saat ini menuju **release candidate yang layak digunakan perusahaan**, dengan bukti yang dapat diaudit untuk:
- kesesuaian implementasi dengan spesifikasi dan keputusan bisnis yang sudah disepakati;
- frontend, backend, dan database yang terintegrasi;
- validasi dan pengujian otomatis yang relevan;
- keamanan autentikasi, otorisasi, konfigurasi, dan data;
- ketepatan perhitungan absensi, kasbon, dan payroll;
- ketahanan terhadap request berulang dan konkurensi;
- backup, restore, logging, audit trail, dan prosedur rollback;
- panduan operasional dan UAT perusahaan.

**Jangan menyamakan “release candidate siap” dengan “sudah live production”.** Anda boleh menyiapkan artefak deployment dan memverifikasi deployment di staging. Deployment production, perubahan database production, migrasi production, perubahan DNS/secret production, atau tindakan yang berpotensi mengganggu operasional harus menunggu persetujuan eksplisit dari pemilik sistem.

## 2. Sumber kebenaran dan prioritas keputusan

Sebelum mengubah kode, temukan dan baca:
1. spesifikasi lengkap MAKARE yang tersedia pada repository, project files, atau dokumen yang diberikan pemilik;
2. laporan audit dan matriks penerimaan MAKARE 2, jika tersedia;
3. README, source code, test suite, schema/migration, konfigurasi deployment, dan riwayat commit;
4. keputusan bisnis dan UI/UX yang sudah disetujui dalam konteks proyek.

Urutan prioritas:
1. keputusan bisnis/UI/UX eksplisit yang sudah disetujui pemilik;
2. spesifikasi lengkap yang disetujui;
3. aturan yang sedang berjalan di production, hanya untuk memahami dampak dan kompatibilitas—bukan untuk otomatis mengalahkan spesifikasi;
4. implementasi repository saat ini;
5. asumsi engineering umum.

Jangan diam-diam mengubah, menyederhanakan, atau mengganti keputusan yang sudah disepakati. Jika dua sumber kebenaran bertentangan dan tidak dapat diselesaikan dengan bukti, dokumentasikan konflik, hentikan hanya pekerjaan yang bergantung pada keputusan tersebut, lalu ajukan pertanyaan spesifik kepada pemilik. Lanjutkan pekerjaan lain yang aman dan tidak bergantung pada konflik itu.

## 3. Konteks teknis yang sudah diketahui — verifikasi ulang

Informasi awal berikut berasal dari audit read-only sebelumnya dan harus diverifikasi kembali pada commit/lingkungan yang benar-benar Anda akses:
- Repository: `https://github.com/nurhasanfadillah/makare-v2`
- Arsitektur yang terlihat: frontend React/CRA, Tailwind, shadcn/ui; backend FastAPI dan asyncpg; database PostgreSQL di Neon.
- Temuan audit penting: default potongan kasbon pada `backend/rules.py` tampak memakai cap maksimum ketika override `None`, sedangkan spesifikasi menyatakan default/usulan potongan Rp0.
- Test `backend/tests/test_rules.py` tampak mengunci perilaku default kasbon yang berbeda dari spesifikasi.
- Tabel `employee_notes` dan `employee_note_revisions` ditemukan pada database live, tetapi tidak ditemukan dalam DDL `backend/schema.py` yang diperiksa.
- `backend/server.py` memiliki fallback CORS wildcard; `backend/schema.py` memiliki seed kredensial awal yang mudah ditebak; rate limiter di `backend/core.py` berbasis memori proses.
- Metadata Neon sebelumnya menunjukkan production branch tidak protected dan pembatasan koneksi perlu ditinjau.
- Rute frontend yang diperiksa belum menunjukkan rute eksplisit untuk beberapa area seperti Catatan Karyawan/Reports. Verifikasi seluruh repository sebelum menyimpulkan fitur tidak ada.

Jangan menganggap semua temuan ini masih berlaku tanpa memeriksa commit dan konfigurasi terbaru. Jangan menganggap kredensial bootstrap masih aktif di production hanya karena terdapat di source.

## 4. Aturan keselamatan wajib

### 4.1 Lindungi production
- Semua pekerjaan awal harus read-only terhadap production.
- Jangan menjalankan `DROP`, `TRUNCATE`, reset database, destructive migration, seed ulang, bulk update/delete, atau perubahan data production.
- Jangan mengubah kredensial, secret, CORS, network allowlist, DNS, domain, atau konfigurasi production tanpa persetujuan eksplisit dan rencana rollback.
- Jangan menjalankan test yang menulis atau menghapus data pada production.
- Jangan menampilkan secret, token, password, connection string, data pegawai sensitif, atau data payroll personal di log, laporan, commit, maupun output.
- Gunakan branch kerja khusus dan database/environment non-produksi yang terpisah.
- Sebelum operasi yang mengubah staging, periksa target koneksi dan environment. Jika target tidak dapat dipastikan, berhenti dan jangan mengeksekusi operasi tersebut.
- Jangan melakukan force-push ke branch bersama atau menghapus histori.
- Jangan mengirim prompt ke Lovable atau layanan eksternal lain kecuali diminta secara eksplisit.

### 4.2 Kerjakan, jangan hanya merencanakan
- Setelah audit awal, mulai implementasi pada item yang jelas dan aman tanpa menunggu persetujuan untuk setiap detail teknis kecil.
- Jangan berhenti setelah menulis rencana atau daftar TODO.
- Jalankan test, periksa output nyata, perbaiki kegagalan yang disebabkan perubahan Anda, lalu jalankan ulang test terkait.
- Jangan menyatakan test, fitur, migrasi, backup, restore, deployment, atau security check lulus kecuali benar-benar dilakukan dan hasilnya tersedia.
- Jika akses/tool/dependency menghalangi tindakan, lakukan bagian lain yang aman; catat blocker spesifik, bukti, dampak, dan tindakan yang dibutuhkan.
- Jangan menutupi test gagal dengan menonaktifkan test, menurunkan assertion, menghapus coverage penting, atau mengubah acceptance criteria tanpa persetujuan.

## 5. Alur kerja eksekusi

### Tahap 0 — Orientasi dan baseline
1. Periksa branch aktif, commit SHA, status working tree, struktur repository, instruksi agent, lockfiles, runtime, dependency, environment, test suite, migration, CI, dan deployment config.
2. Identifikasi file spesifikasi dan laporan audit yang tersedia; baca secara penuh jika memungkinkan.
3. Buat branch kerja dengan nama yang jelas, misalnya `agent/makare-production-readiness`, tanpa menimpa perubahan pengguna.
4. Pastikan working tree pengguna tidak memiliki perubahan yang akan tertimpa.
5. Jalankan baseline test/lint/build yang aman di lingkungan lokal/non-production. Catat perintah, hasil, dan error awal tanpa mengklaim lulus jika tidak berjalan.
6. Buat `docs/production-readiness/BASELINE.md` berisi commit, arsitektur aktual, perintah test, hasil baseline, serta keterbatasan akses. Jangan masukkan secret.
7. Susun daftar acceptance criteria dari spesifikasi dan keputusan yang disetujui.

**Output Tahap 0:** baseline faktual dan daftar kerja terprioritas. Lanjutkan ke Tahap 1 tanpa berhenti, kecuali ada blocker yang membuat tindakan berikutnya berbahaya atau memerlukan keputusan bisnis.

### Tahap 1 — Audit cakupan dan kesenjangan
Audit backend, frontend, database, API, autentikasi/otorisasi, validasi input, audit log, test, konfigurasi deployment, backup/restore, observability, dan dokumentasi.
- Cocokkan setiap fitur dan aturan bisnis dengan implementasi serta test.
- Telusuri setiap route/API sampai ke komponen frontend dan database yang relevan.
- Cari TODO/FIXME, endpoint tanpa proteksi, error handling yang bocor, data race, transaksi parsial, schema drift, dan konfigurasi insecure.
- Verifikasi apakah CI benar-benar ada dan berjalan.
- Bedakan: fakta terverifikasi, dugaan, belum diuji, dan rekomendasi.
- Jangan menyimpulkan fitur tidak ada hanya dari satu file.

Simpan hasil pada `docs/production-readiness/GAP-ANALYSIS.md`, termasuk ID temuan, prioritas, bukti file/baris atau command output, dampak, tindakan, dan acceptance test.

### Tahap 2 — Tutup kesenjangan P0: integritas aturan bisnis
Tangani lebih dahulu kesalahan yang dapat memengaruhi uang, kehadiran, atau konsistensi data.

#### Kasbon/payroll
- Cocokkan rumus dengan spesifikasi yang disetujui.
- Default/usulan potongan kasbon adalah **Rp0** jika tidak ada override eksplisit.
- Batas potongan tetap tidak boleh melebihi saldo kasbon atau net sebelum kasbon; net final tidak boleh negatif.
- Ubah implementasi dan unit test secara bersamaan. Jangan mempertahankan test yang mengunci perilaku bertentangan dengan spesifikasi.
- Verifikasi alur end-to-end: nilai awal UI, preview API, perubahan operator, validasi server, persistensi adjustment/finalisasi, snapshot, dan riwayat.
- Pastikan retry tidak membuat potongan ganda.
- Jangan mengedit snapshot payroll final secara langsung; koreksi harus menggunakan mekanisme adjustment sesuai spesifikasi.

#### Aturan attendance/payroll lain
Verifikasi setiap aturan dalam spesifikasi, termasuk:
- timezone WIB;
- tanggal kerja untuk shift lintas tengah malam mengikuti check-in;
- toleransi keterlambatan 30 menit;
- aturan pengurangan jam pertama setelah melewati toleransi;
- ambang pembulatan 30 menit;
- sesi absensi tidak lengkap;
- overlap istirahat dan hitung lembur;
- operator hanya menginput attendance hari ini;
- admin mengoreksi attendance historis dengan alasan;
- kiosk/token dan batasan akses;
- PIN pulang awal terikat pada transaksi dan tidak dapat digunakan ulang di luar cakupannya;
- server menolak lembur jika fitur nonaktif;
- snapshot payroll immutable, adjustment terlacak;
- finalisasi atomik dan idempotent;
- status Hadir/Sakit/Izin/Alfa dan aturan Alfa tanpa pemotongan gaji sesuai keputusan bisnis.

Jangan mengubah aturan bisnis lain hanya agar test mudah lulus. Buat test batas (boundary), test negatif, dan test kombinasi untuk setiap rumus kritis.

### Tahap 3 — Database dan migrasi
1. Inventarisasikan tabel, index, constraint, foreign key, trigger, extension, dan migration yang ada.
2. Bandingkan schema source dengan schema non-production yang nyata.
3. Rekonsiliasi `employee_notes` dan `employee_note_revisions` jika discrepancy masih ada.
4. Tetapkan mekanisme migration versioned yang dapat direproduksi. Hindari ketergantungan pada schema manual yang tidak terdokumentasi.
5. Migration harus idempotent jika pola proyek mengharuskannya, dapat diaudit, dan mempunyai langkah rollback atau rencana pemulihan yang jelas.
6. Uji dari database kosong dan dari salinan schema non-production yang mendekati kondisi saat ini.
7. Jangan drop/recreate tabel untuk menyamakan schema. Pertahankan data dan histori.
8. Verifikasi constraint penting: unique attendance per pegawai/tanggal, hanya satu sesi terbuka, satu snapshot per periode/pegawai, dan pencegahan potongan kasbon ganda jika sesuai desain.
9. Tambahkan test migration dan schema contract.

### Tahap 4 — Keamanan aplikasi
Lakukan audit dan implementasi perbaikan yang didukung bukti:
- autentikasi dan session/token lifecycle;
- password hashing dan kebijakan password;
- role-based access control pada backend untuk setiap endpoint sensitif;
- validasi input server-side dan batas ukuran request;
- CORS production dengan origin eksplisit, bukan fallback wildcard berkredensial;
- secret dari environment/secret manager, tanpa default secret production;
- kredensial bootstrap yang aman, tidak permanen, dan proses rotasi yang jelas;
- rate limiting yang sesuai dengan arsitektur deployment dan trusted proxy;
- perlindungan terhadap IDOR, privilege escalation, replay/idempotency abuse, SQL injection, XSS, CSRF bila relevan, dan kebocoran error;
- dependency vulnerability review dengan tooling yang tersedia;
- audit log untuk aksi sensitif;
- log redaction dan pengelolaan data personal.

Jangan melakukan penetration test destruktif atau menyerang sistem pihak ketiga. Uji keamanan hanya pada sistem yang diizinkan dan lingkungan yang ditentukan. Untuk temuan konfigurasi live, dokumentasikan risiko dan usulan perubahan; jangan mengubah production otomatis.

### Tahap 5 — Pengujian dan CI
Tambahkan atau perbaiki test sesuai stack aktual:
- unit tests untuk rumus;
- integration tests untuk API/database;
- authorization matrix tests untuk anonymous/operator/admin;
- migration/schema tests;
- idempotency dan concurrency tests untuk attendance dan payroll;
- regression tests untuk setiap bug yang diperbaiki;
- frontend tests untuk validasi, loading/error/empty state, serta alur kritis;
- smoke tests dan end-to-end tests untuk alur login, attendance, kasbon, closing payroll, adjustment, dan audit history.

Buat atau perbaiki CI agar pull request menjalankan dependency checks yang tersedia, lint, test, dan build. Jangan memasukkan secret dalam workflow. Jangan membuat CI menyentuh production. Gunakan test database yang terisolasi dan data sintetis.

Jalankan semua test yang relevan. Untuk setiap perintah, catat exit code dan ringkasan hasil. Jika ada test yang tidak bisa dijalankan, tulis alasannya dengan tepat; jangan menandainya sebagai pass.

### Tahap 6 — UI/UX dan alur operasional
Pertahankan desain dan aturan yang sudah disepakati. Jangan melakukan redesign tanpa kebutuhan yang dibuktikan.
- Pertahankan light mode, palet Midnight Navy `#0B1F3A`, Royal Blue `#174EA6`, Gradient Blue `#4F7DF3`, Cool Canvas `#F4F7FB`, serta tipografi Plus Jakarta Sans dan IBM Plex Mono, jika memang masih menjadi keputusan proyek aktif.
- Pertahankan pengalaman kiosk full-screen dan alur Masuk/Keluar sesuai spesifikasi.
- Pertahankan batasan operator dan akses admin.
- Periksa responsive/mobile, navigasi, label, konfirmasi tindakan sensitif, validasi form, loading/error/empty states, format tanggal/jam WIB, dan aksesibilitas dasar.
- Verifikasi fitur Catatan Karyawan, histori revisi, Reports, employee detail/change history, date picker, serta menu dan route terkait berdasarkan spesifikasi. Implementasikan yang memang menjadi cakupan rilis; jangan membuat klaim fitur selesai tanpa bukti.
- Pastikan error backend disajikan ke pengguna secara aman dan dapat dipahami.

### Tahap 7 — Operabilitas dan pemulihan
Siapkan dan uji di lingkungan non-production:
- structured logs dengan request/correlation ID;
- health/readiness checks yang tidak membocorkan informasi;
- metrik atau minimal indikator operasional yang sesuai stack;
- petunjuk diagnosis error umum;
- backup policy, retention, dan akses backup;
- restore drill yang benar-benar dijalankan pada database non-production;
- deployment/runbook;
- rollback aplikasi dan database;
- panduan rotasi secret;
- panduan respons insiden dan eskalasi;
- panduan onboarding admin/operator dan prosedur harian perusahaan.

Backup yang hanya dikonfigurasi tanpa uji restore tidak boleh disebut terverifikasi. Dokumentasikan hasil restore drill, waktu yang diperlukan, dan keterbatasannya.

### Tahap 8 — Staging dan UAT
Deploy ke staging hanya jika akses dan target staging telah dipastikan. Gunakan data sintetis atau data yang secara eksplisit diizinkan.
Lakukan smoke test setelah deployment, termasuk:
- login/logout dan role;
- attendance masuk/keluar;
- kasus shift lintas tengah malam;
- kasbon dan preview payroll;
- finalisasi dan snapshot;
- adjustment dan audit history;
- kiosk;
- pengaturan;
- Catatan Karyawan dan Reports sesuai cakupan;
- error handling, refresh, dan mobile layout;
- backup/restore serta rollback yang relevan.

Buat `docs/production-readiness/UAT-CHECKLIST.md` dengan langkah, expected result, actual result, status, bukti, dan kolom persetujuan pengguna bisnis. Jangan menandatangani UAT atas nama perusahaan.

### Tahap 9 — Release readiness dan handoff
Buat dokumen:
- `docs/production-readiness/RELEASE-REPORT.md`
- `docs/production-readiness/DEPLOYMENT-RUNBOOK.md`
- `docs/production-readiness/ROLLBACK-RUNBOOK.md`
- `docs/production-readiness/BACKUP-RESTORE.md`
- `docs/production-readiness/SECURITY-REVIEW.md`
- `docs/production-readiness/UAT-CHECKLIST.md`
- `docs/production-readiness/GAP-ANALYSIS.md`
- `docs/production-readiness/BASELINE.md`

Laporan release harus menyertakan:
- commit SHA dan perubahan penting;
- fitur yang selesai dengan tautan/bukti;
- test command, hasil aktual, dan test yang belum berjalan;
- build dan staging URL hanya jika benar-benar tersedia;
- status migration;
- status security review;
- status backup/restore;
- status UAT;
- known issues dan risiko sisa;
- instruksi deployment dan rollback;
- keputusan yang masih perlu dibuat pemilik;
- keputusan release: `READY FOR UAT`, `READY FOR PRODUCTION APPROVAL`, atau `BLOCKED`, beserta alasan.

**Dilarang memberi status `PRODUCTION READY`** jika ada bug P0 terbuka, test kritis gagal/belum dijalankan, migration belum tervalidasi, tidak ada prosedur backup/restore yang diuji, isu keamanan kritis terbuka, atau UAT pemilik bisnis belum disetujui. Anda boleh menyatakan `READY FOR PRODUCTION APPROVAL` setelah seluruh bukti teknis wajib lulus, tetapi jangan menyatakan production sudah live kecuali deployment benar-benar dilakukan dan diverifikasi dengan persetujuan.

## 6. Matriks penerimaan minimum

Buat satu baris per aturan spesifikasi, dengan kolom:
`ID | Aturan | Lokasi implementasi | Test terkait | Kriteria lulus | Hasil aktual | Bukti | Status | Catatan`.

Status yang diizinkan:
- `PASS` — dijalankan dan bukti memenuhi kriteria;
- `FAIL` — dijalankan dan tidak memenuhi kriteria;
- `NOT RUN` — belum dijalankan;
- `BLOCKED` — tidak dapat dijalankan, dengan blocker jelas;
- `NEEDS BUSINESS DECISION` — spesifikasi/keputusan bertentangan.

Jangan gunakan `PASS` hanya karena kode terlihat benar atau test sudah ditulis. Test harus dijalankan.

## 7. Cara bekerja dan pelaporan
- Kerjakan dalam batch kecil yang logis; pastikan setiap batch memiliki test.
- Setelah setiap batch, periksa diff, cari perubahan tak sengaja, dan jalankan test relevan.
- Pertahankan perubahan pengguna yang sudah ada.
- Gunakan migration dan commit yang jelas; jangan commit secret atau data produksi.
- Jika dapat membuat commit, buat commit bertahap dengan pesan deskriptif. Jangan push atau merge ke branch protected/shared tanpa izin.
- Jangan berhenti untuk meminta izin atas keputusan implementasi teknis yang jelas dan reversible dalam branch kerja.
- Minta persetujuan hanya untuk keputusan bisnis yang ambigu, perubahan desain yang material, tindakan produksi, biaya/layanan baru, atau perubahan destruktif.
- Beri laporan kemajuan berbasis hasil, bukan narasi aktivitas. Cantumkan perubahan file, test yang benar-benar dijalankan, hasil, blocker, dan langkah berikutnya.
- Jika konteks sesi hampir habis, simpan status dan langkah berikutnya ke `docs/production-readiness/EXECUTION-STATE.md` agar agent berikutnya dapat melanjutkan.

## 8. Instruksi mulai sekarang

Mulai Tahap 0 sekarang. Periksa repository dan dokumen sumber yang tersedia, verifikasi commit serta lingkungan aktif, lalu jalankan baseline aman. Setelah itu lanjutkan tahap implementasi berurutan tanpa berhenti pada rencana saja.

Jangan mengajukan pertanyaan umum seperti “apa yang harus saya kerjakan?” terlebih dahulu. Ajukan pertanyaan hanya jika ada konflik keputusan bisnis yang nyata, target environment tidak aman/tidak dapat dipastikan, atau tindakan berisiko memerlukan persetujuan pemilik.

Pada akhir setiap sesi, laporkan secara ringkas:
1. apa yang telah benar-benar berubah;
2. test/perintah yang benar-benar dijalankan dan hasilnya;
3. apa yang belum dilakukan dan mengapa;
4. blocker atau keputusan yang diperlukan;
5. langkah berikutnya yang sudah jelas.

**Target:** menghasilkan release candidate yang teruji dan terdokumentasi, serta siap menjalani persetujuan production perusahaan—tanpa mengorbankan data production, aturan bisnis yang disepakati, atau kejujuran status implementasi.


## 9. Klausul wajib: Selesaikan seluruh plan awal, bukan hanya temuan audit

**Klausul ini mengikat seluruh tahapan di atas.** Audit production-readiness adalah satu workstream, bukan pengganti plan produk awal. Jangan menandai proyek selesai hanya karena temuan audit sudah diperbaiki, build berhasil, atau beberapa test lolos.

### 9.1 Rekonstruksi plan dan backlog lengkap
Sebelum memilih urutan implementasi, temukan dan rekonstruksi seluruh sumber rencana MAKARE 2:
- spesifikasi lengkap/PRD dan ERD;
- backlog, milestone, checklist, task list, dan keputusan yang pernah disetujui;
- dokumen dalam repository, project knowledge, file proyek, issue/PR jika dapat diakses;
- keputusan UI/UX, alur pengguna, aturan bisnis, laporan, dan fitur yang dijanjikan;
- pekerjaan yang sudah dimulai pada commit/branch saat ini.

Jangan mengasumsikan semua plan tersedia di README. Cari sumber yang relevan dan catat sumber yang tidak dapat diakses. Jangan mengarang item backlog atau menyatakan dokumen sudah dibaca jika belum berhasil membacanya.

### 9.2 Buat master backlog dengan status berbasis bukti
Buat `docs/production-readiness/MASTER-PLAN-TRACKER.md` yang mencantumkan **setiap item plan awal** secara terpisah dengan kolom minimum:

`ID | Sumber plan dan referensi | Modul/fitur | Acceptance criteria | Status awal | Bukti saat ini | Gap tersisa | Prioritas | Dependensi | Tindakan berikutnya | Test penerimaan | Status akhir | Bukti akhir`

Gunakan status awal:
- `DONE — VERIFIED`: implementasi ada dan acceptance criteria telah dibuktikan lewat test atau pemeriksaan yang sesuai;
- `PARTIAL`: sebagian alur/criteria selesai, sebagian belum;
- `NOT STARTED`: belum ada implementasi yang dapat dibuktikan;
- `REGRESSION`: sebelumnya ada tetapi sekarang rusak atau tidak lagi sesuai;
- `NEEDS BUSINESS DECISION`: sumber keputusan saling bertentangan;
- `NOT VERIFIED`: belum ada bukti cukup untuk menentukan status.

Keberadaan file, komponen UI, endpoint, atau tabel **tidak cukup** untuk menyatakan sebuah fitur `DONE — VERIFIED`. Verifikasi alur dari UI/API hingga database dan aturan bisnisnya jika relevan.

Jika spesifikasi memuat fitur seperti Catatan Karyawan, Reports, detail karyawan/histori perubahan, date picker, attendance/kiosk, kasbon, closing payroll, adjustment, audit, settings, atau modul lain, masukkan masing-masing sesuai sumber aslinya. Daftar ini contoh area untuk diperiksa, bukan izin untuk mengarang acceptance criteria atau menghilangkan modul yang tidak disebut di sini.

### 9.3 Backlog awal bukan satu-satunya daftar kerja
Gabungkan backlog menjadi tiga kelompok yang tetap terlacak terpisah:
1. **Plan awal — pekerjaan produk:** semua fitur, UI/UX, alur pengguna, aturan bisnis, dan deliverable yang disetujui.
2. **Koreksi audit — kualitas dan keamanan:** defect, schema drift, authorization, integritas data, observability, CI, dan risiko operasional.
3. **Kesiapan rilis — operasional perusahaan:** staging, UAT, backup/restore, deployment/rollback, runbook, onboarding, dan approval.

Satu item boleh terkait lebih dari satu kelompok, tetapi jangan sampai item plan awal hilang karena sudah disebut sebagai temuan audit, atau sebaliknya. Setiap item harus mempunyai ID dan status tersendiri.

### 9.4 Eksekusi semua item yang disepakati
Setelah master tracker dibuat:
- lanjutkan implementasi semua item `PARTIAL`, `NOT STARTED`, dan `REGRESSION` yang termasuk cakupan plan yang disetujui;
- selesaikan acceptance criteria tiap item, bukan hanya tampilan atau happy path;
- tambahkan atau perbaiki test untuk setiap perilaku penting;
- perbarui tracker setelah benar-benar mengubah dan menguji kode;
- jalankan regression test lintas modul setelah perubahan yang berpotensi memengaruhi modul lain;
- kerjakan item independen secara paralel hanya jika aman dan tidak menimbulkan konflik file/schema;
- jangan menandai item selesai hanya karena agent telah menulis kodenya.

Jika ada item yang tidak dapat diselesaikan karena akses, dependency, keputusan bisnis, biaya, atau kebutuhan kredensial, beri status `BLOCKED` dengan alasan spesifik dan tetap pertahankan item tersebut dalam backlog. Jangan diam-diam menghapus atau menurunkan prioritasnya.

### 9.5 Aturan prioritas
Gunakan urutan:
1. risiko kehilangan/korupsi data, keamanan kritis, dan perhitungan uang yang salah;
2. aturan bisnis inti dan alur yang menghalangi operasional;
3. fitur wajib pada plan awal yang belum selesai;
4. integrasi antar-modul dan regression;
5. kesiapan deployment, backup/restore, observability, dokumentasi, dan UAT;
6. peningkatan non-kritis yang memang tercakup dalam plan.

Prioritas ini mengatur urutan pengerjaan, **bukan menghapus kewajiban menyelesaikan cakupan plan awal**.

### 9.6 Definition of Done proyek
Proyek belum dianggap selesai sampai:
- seluruh item wajib dalam plan awal terdaftar dalam tracker;
- setiap item wajib berstatus `DONE — VERIFIED`, atau memiliki keputusan tertulis pemilik yang menyetujui penundaan/penghapusan;
- acceptance criteria produk dan aturan bisnis memiliki bukti;
- tidak ada defect P0/P1 yang belum diselesaikan atau secara eksplisit diterima pemilik dengan risiko terdokumentasi;
- integration/regression tests dan build yang relevan dijalankan dan hasilnya dicatat;
- migration/schema, security review, backup/restore, deployment/rollback runbook, dan UAT memenuhi gate yang ditetapkan;
- keputusan UI/UX yang disepakati dipertahankan atau perubahan disetujui;
- laporan akhir memisahkan item selesai, item tertunda, item tidak diuji, risiko tersisa, dan keputusan pemilik;
- pemilik bisnis menyetujui UAT serta memberi persetujuan eksplisit sebelum production release.

Jangan mengklaim “semua plan selesai” bila tracker masih memiliki item wajib berstatus `PARTIAL`, `NOT STARTED`, `REGRESSION`, `NOT VERIFIED`, atau `BLOCKED`.

### 9.7 Instruksi eksekusi yang diperbarui
Saat memulai, **jangan langsung hanya memperbaiki bug kasbon**. Pertama rekonstruksi plan awal dan buat master tracker, lalu jalankan implementasi berdasarkan prioritas risiko sambil tetap memastikan seluruh plan tercakup. Setelah itu lanjutkan audit dan release-readiness. Jangan berhenti setelah tracker dibuat: gunakan tracker sebagai backlog aktif dan terus kerjakan item yang aman hingga mencapai gate release. Pada setiap laporan kemajuan, tampilkan jumlah item `DONE — VERIFIED`, `PARTIAL`, `NOT STARTED`, `REGRESSION`, `BLOCKED`, dan `NEEDS BUSINESS DECISION` agar progres proyek dapat diukur.
