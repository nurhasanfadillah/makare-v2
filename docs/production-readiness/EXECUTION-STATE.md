# Execution state — 2026-10-31

## Keputusan urutan eksekusi

- Pemilik setuju: inventaris kelengkapan, susun rencana dan selesaikan gap implementasi semua modul, lalu lakukan audit menyeluruh sebagai fase khusus. Build/unit check secukupnya tetap dilakukan per modul untuk mencegah regresi; itu bukan audit final.
- Inventaris awal P-01–P-42: mayoritas source tersedia tetapi acceptance lintas sistem belum terbukti; P-05 detail karyawan belum punya UI, dan P-42 belum punya matriks pemetaan acceptance. P-14/DEC-03–05 tetap mengandung keputusan aturan gaji yang harus dikunci sebelum payroll bisa dinyatakan lengkap.

## P-05 — implementasi detail karyawan

- Ditambahkan route admin `/karyawan/:id`, tombol Detail di direktori, profil personal/pekerjaan/payroll, komponen manual, saldo kasbon, dialog edit, tautan Catatan, dan timeline perubahan.
- Ditambahkan `GET /employees/{eid}/history` yang mewajibkan admin, memastikan karyawan ada, dan hanya mengembalikan actor/action/time/result/nama field yang berubah; payload before/after tidak dikirim agar data sensitif historis tidak muncul di profil.
- Build frontend berhasil (`Compiled successfully`); `python -m py_compile routes_admin.py` exit 0; `git diff --check` bersih.
- Browser admin berhasil membuka `/karyawan/9` dan menampilkan profil, payroll, saldo kasbon, dan aksi Catatan/Ubah Data. Riwayat meminta endpoint baru tetapi server di port 8001 menjawab 404 karena proses API yang berjalan belum memuat perubahan source. P-05 tetap PARTIAL sampai server lokal terkonfigurasi memuat route baru dan role/404/history privacy diverifikasi.

## P-37 — redaksi data historis di pembacaan audit

- Browser admin menunjukkan audit log legacy memuat nilai personal pada event employee sebelum aturan penulisan audit diperketat. Endpoint `/audit` kini memproyeksikan event employee lewat allowlist aman (`code`, `department_id`, `join_date`, `payroll_mode`, `components` sebagai jumlah, dan `changed_fields`) sehingga nilai legacy tidak dikirim ke UI; actor/action/time/result tetap utuh.
- Fix source belum diverifikasi lewat API runtime karena proses backend yang berjalan belum memuat route history P-05. P-37/AUD-11 tetap PARTIAL sampai endpoint audit dibuka ulang dan nilai lama terbukti tidak hadir di response.

## User steering

Lanjutkan proyek berdasarkan PRD konsolidasi, tracker dan execution plan. Prioritaskan aturan uang/attendance; lindungi production dan perubahan user.

## Status kerja

- Baca Spesifikasi MAKARE v1.1, Master Implementation Prompt, MAKARE 2 Master Execution Prompt, dan PRD lama.
- Selaraskan `memory/PRD.md` dan buat tracker 76 item serta execution plan batch.
- Kode Catatan Karyawan berada di working tree; frontend build lulus, tetapi schema migration versioned dan CRUD/revision acceptance belum dilakukan.
- Audit payroll manual sebelumnya menemukan override khusus-periode belum ada; kini Closing menerima komponen efektif yang tervalidasi dan snapshot menyimpan daftar tersebut. Halaman `/gaji-manual` menampilkan current preview serta closed snapshots.
- Halaman admin khusus Gaji Manual menampilkan preview periode berjalan, snapshot periode tutup buku per pilihan periode, dan membuka form komponen master karyawan. Snapshot closed read-only serta menampilkan koreksi bersih efektif. Closing preview menerima daftar komponen per-periode tervalidasi; effective component list disimpan dalam snapshot final. P-22 masih PARTIAL; frontend build lulus tetapi API/DB acceptance belum dibuktikan; skema memakai amount integer Rupiah dan volume maksimum 2 desimal; kalkulasi total tetap memakai `round()` Python ties-to-even.
- P-26 lokal diperbaiki: finalisasi menyimpan SHA-256 payload ternormalisasi (tanggal akhir + penyesuaian); key sama dan payload sama tetap retry idempoten, key sama dan payload berubah menghasilkan HTTP 409. Kolom nullable ditambahkan secara aditif pada startup DDL; periode lama tanpa hash tetap memakai perilaku legacy. Belum diuji API/DB, concurrency, atau jalur migration versioned.
- Audit attendance/settings menemukan jam pola `HH:MM` yang tidak valid sebelumnya dapat lolos ke `datetime.time`, alasan koreksi hanya spasi, dan break yang tumpang tindih dihitung ganda. Validasi jam/alasan serta penggabungan overlap diperbaiki lokal.
- Probe aturan jam pertama dengan rumus recognition lama: jadwal 08:00–17:00 + istirahat 12:00–13:00, check-in 09:30 menghasilkan eligible 390, rounded 420, tetapi paid 360 menit. Nilai perlu dihitung ulang menurut formula pemilik sesudah sumber toleransi dan urutan jam pertama/istirahat ditetapkan.
- Static trace: endpoint manual/correction dapat membuat atau membuka sesi reguler tanpa memeriksa sesi lembur terbuka, walau `clock()` melarang memulai lembur selama sesi reguler terbuka. Perlu selesaikan kebijakan DEC-08 dan concurrency design.
- Klarifikasi pemilik: menit toleransi pengakuan ditambahkan ke durasi eligible, lalu dibulatkan turun ke jam penuh (`floor((eligible + tolerance)/60)`); setting yang dipakai adalah `late_tolerance_minutes` untuk regular dan lembur. Formula diimplementasikan di `rules.py`; 73 unit/model tests lulus. Acceptance endpoint/database dan interaksi jam pertama masih pending.
- Audit kasbon: default lama memotong cap maksimum. Perbaikan lokal di `backend/rules.py` kini menetapkan default Rp0; test expectation di `backend/tests/test_rules.py` diperbarui untuk default zero dan explicit override.

## Verifikasi sesi

- Dua direct assertions pure Python sesudah fix lulus (default zero dan explicit override).
- `python -m py_compile rules.py tests/test_rules.py` berhasil.
- Suite terisolasi terakhir dijalankan dari `backend` menggunakan ignored `backend/.venv`: `python -m pytest tests/test_config.py tests/test_kiosk_security.py tests/test_security_current_user.py tests/test_schema_bootstrap.py tests/test_payroll_components.py tests/test_rules.py tests/test_attendance_validation.py -q` ? **88 passed, exit code 0 after CORS and PIN lockout changes**. Test payroll memvalidasi payload komponen periode, presisi schema, nilai gross, hash payload stabil, retry sama, dan konflik key dengan payload berbeda.
- `python -m py_compile` untuk modul backend yang berubah berhasil; `git diff --check` bersih; frontend production build berhasil. Laporan yang dibaca saja sudah diuji pada browser dengan sesi admin yang tersedia.
- Konfigurasi `backend/pytest.ini` tetap dipatuhi (`-n 2 --dist loadscope`); tujuh file unit/model murni dipilih. Tes API/database tidak dijalankan. FastAPI mengeluarkan deprecation warnings `asyncio.iscoroutinefunction` (dependency warning, test tetap lulus).
- `git diff --check` bersih; `py_compile` untuk modul backend yang baru/berubah berhasil.
- Backend lokal terkoneksi ke PostgreSQL yang dikonfigurasi; startup schema selesai. Health endpoint dan CORS preflight berhasil untuk origin lokal, dan origin asing ditolak. Tidak ada reset data bisnis.
- Frontend dependencies terpasang dari `yarn.lock`; CRA production build berhasil setelah menambahkan ekspor direktori karyawan. Dev server lokal tersedia pada `http://localhost:3000`; backend pada `http://127.0.0.1:8001`. Sesi Administrator pada browser bersama dipakai untuk verifikasi baca-saja; tidak ada akun atau kredensial baru dibuat.

## Langkah berikutnya

1. Minta/gunakan kredensial admin existing agar login browser dan laporan PDF dapat diverifikasi pada data yang ada; jangan menampilkan kredensial di output atau dokumen.
2. Lanjutkan P-34/P-35/P-36, lalu selesaikan gap fitur laporan/PDF tersisa dengan sumber snapshot/ledger final.
3. Buat fixture API yang dapat dibersihkan atau transaction rollback untuk payroll/attendance; jangan menghapus/reset data bisnis sebelum aplikasi siap dan pemilik menyetujui reset akhir.
4. Bangun migrasi versioned dan rekonsiliasi schema; sesudah fitur produk lengkap, jalankan acceptance matrix, validasi, dan review keamanan sesuai `EXECUTION-PLAN.md`.

## Bukti terbaru ? koneksi lokal dan laporan

- PostgreSQL target merespons melalui startup backend; tabel bisnis existing dipertahankan dan tidak di-reset. Startup schema menjalankan DDL aplikasi yang sudah ada.
- `GET /api/` mengembalikan status `ok`; `OPTIONS` dari origin frontend lokal mendapat HTTP 200 dan allow-origin yang tepat; origin asing mendapat HTTP 400 tanpa allow-origin.
- Yarn Classic 1.22.22 menginstal dependencies dengan `--frozen-lockfile`; production build berhasil. Warning peer dependency/deprecation tetap muncul dari toolchain, tetapi tidak menggagalkan build.
- P-29: endpoint admin-only dan aksi Direktori PDF ditambahkan. Query hanya memuat kode, nama, departemen, mode payroll, tanggal masuk, dan status. Dengan sesi admin browser, endpoint menghasilkan `200 application/pdf`; pagination belum diuji.
- Backend dan frontend aktif kembali pada `127.0.0.1:8001` dan `localhost:3000`; startup schema sukses dan tidak ada reset data.


- P-32/P-33: authenticated browser menampilkan periode Oktober pada data existing (2 Hadir, 1 Sakit, 4 tanpa catatan, 0 Alfa manual); endpoint PDF menghasilkan `200 application/pdf`. Satu sesi reguler berdurasi lebih dari 24 jam terdeteksi dan kini diberi penanda `Periksa durasi`, tanpa mengubah data maupun gaji. Fixture edge-case dan pagination PDF masih pending.

- P-35/P-36: rekap Kasbon PDF baru menghasilkan `200 application/pdf`; dua transaksi ledger pada karyawan existing merekonsiliasi dengan total pemberian/potongan/pembatalan/saldo API. Periode payroll tertutup saat ini berjumlah 0, sehingga rekap snapshot P-34 dan baris status final P-36 belum dapat divalidasi end-to-end.

## Progress P-37 — audit log

- Peninjauan statis menemukan beberapa mutasi admin dan penulisan audit belum berada dalam satu transaksi: perubahan status karyawan, CRUD departemen, dan pembuatan user. Jika insert audit gagal, mutasi bisa tetap tersimpan tanpa jejak. Handler tersebut kini memakai transaksi yang sama untuk data dan audit.
- Audit create/update karyawan tidak lagi menulis nama atau nilai gender, alamat, tanggal lahir, KTP, telepon, dan tarif. Update tetap mencatat `changed_fields` serta nilai sebelum/sesudah hanya untuk field non-sensitif.
- Verifikasi yang dilakukan: inspeksi diff/source dan perubahan tracker. Tes API/database serta verifikasi hak append-only di database belum dijalankan; tidak ada data bisnis yang diubah.
- Batasan tersisa: cakupan event untuk semua tindakan sensitif belum dibuktikan lengkap, dan perlindungan append-only pada level database/runtime role belum dikonfirmasi. Status P-37 tetap PARTIAL.

## Progress P-38 — siklus tautan kiosk

- Validasi token/status kiosk sebelumnya memakai cache pengaturan lokal 15 detik. Endpoint kiosk kini membaca baris pengaturan aktual dari DB untuk setiap pemeriksaan, sehingga perubahan token atau status aktif berlaku pada request berikutnya juga di instance lain.
- UI rotasi kini langsung memakai token dari respons rotasi untuk memperbarui tautan yang terlihat; audit tetap menyimpan penanda tersamarkan, bukan token.
- Verifikasi terbatas pada inspeksi source dan diff; belum ada acceptance API/browser atau uji beberapa instance. URL produksi masih harus dibandingkan dengan deployment frontend yang sesungguhnya. P-38 tetap PARTIAL.

## Progress P-39 — state halaman Pengaturan

- Halaman Pengaturan kini menampilkan state memuat awal, kegagalan memuat dengan tombol coba lagi, dan banner ketika refresh gagal tetapi data sebelumnya masih tersedia.
- Penyimpanan pengaturan menampilkan state `Menyimpan…` dan menonaktifkan formulir umum selama request. Rotasi token dan simpan PIN punya state pending masing-masing agar tidak terjadi submit ganda dan tidak ada toast sukses sebelum respons berhasil.
- Perubahan baru mencakup halaman Pengaturan; halaman lain belum diaudit menyeluruh. Frontend build/interaksi browser belum diverifikasi pada slice ini; tidak ada data bisnis yang diubah.

## Lanjutan P-39 — state Data Karyawan

- Daftar karyawan kini mengakhiri loading saat request gagal dan menampilkan error dengan tombol coba lagi; hasil request lama dibersihkan supaya error tidak tampak sebagai daftar kosong. Kegagalan memuat departemen juga terlihat terpisah.
- Dialog edit karyawan tetap terbuka jika detail gagal diambil, menampilkan alasan kegagalan dan aksi coba lagi. Cleanup effect mengabaikan respons lama saat dialog/karyawan berubah, mengikuti pola fetch React yang mendokumentasikan ignore flag pada cleanup.
- Frontend production build berhasil: `npx --yes yarn@1.22.22 build` (exit code 0, compiled successfully). `git diff --check` bersih. Belum ada uji interaksi browser; cakupan P-39 untuk halaman lain tetap pending.

## Lanjutan P-39 — layar payroll dan kasbon

- Riwayat tutup buku serta detail snapshot kini membedakan loading dari error dan menyediakan retry; error detail periode tidak lagi berputar tanpa akhir.
- Halaman Tutup Buku kini menampilkan error/retry saat periode berikutnya gagal diambil. Rekap kasbon dan dialog ledger juga punya state gagal/retry, termasuk state kosong terpisah untuk ledger yang berhasil dimuat tanpa transaksi.
- Build pertama menangkap duplikasi import `Button` pada detail periode; import ganda dihapus. Build ulang berhasil: `npx --yes yarn@1.22.22 build` (exit code 0, compiled successfully). `git diff --check` bersih. Belum ada uji browser; P-39 tetap PARTIAL.

## Lanjutan P-39 — dashboard, absensi, dan laporan

- Dashboard kini memiliki retry saat ringkasan gagal dimuat. Absensi membedakan loading, error awal dengan retry, dan kegagalan refresh di atas data terbaru sebelumnya.
- Gaji Manual menampilkan retry ketika preview periode berjalan atau snapshot periode tutup gagal diambil. Laporan Absensi tidak lagi menyamakan request gagal dengan belum memilih filter; filter karyawan yang gagal juga terlihat.
- Build frontend terakhir berhasil: `npx --yes yarn@1.22.22 build` (exit code 0, compiled successfully); `git diff --check` bersih. Acceptance interaksi browser dan audit semua halaman masih pending; P-39 tetap PARTIAL.

## Lanjutan P-39 — catatan karyawan dan form kasbon

- Catatan Karyawan sebelumnya mengubah kegagalan fetch menjadi array kosong. Sekarang halaman membedakan loading, error dengan retry, dan hasil kosong setelah request sukses.
- Dialog pemberian kasbon sekarang memuat karyawan aktif dengan status pending/error yang terlihat, retry saat fetch gagal, serta menonaktifkan penyimpanan ketika daftar belum tersedia/kosong. Respons async yang datang setelah dialog ditutup diabaikan.
- Tombol simpan catatan memperlihatkan state `Menyimpan…` dan tidak bisa dibatalkan selama submit berlangsung.
- Frontend production build berhasil: `npx --yes yarn@1.22.22 build` (exit code 0, compiled successfully). Uji browser dan audit P-39 untuk seluruh aksi/peran masih pending.

## Lanjutan P-39 — tab Departemen dan Akun

- Tab Departemen dan Akun kini menampilkan loading, error dengan retry, dan keadaan kosong setelah fetch sukses. Mutasi disable saat request berjalan dan tombol simpan menunjukkan state pending.
- Build terakhir berhasil: `npx --yes yarn@1.22.22 build` (exit code 0, compiled successfully); `git diff --check` bersih. Browser acceptance belum dilakukan karena sesi browser sebelumnya tidak tersedia pada giliran ini. P-39 tetap PARTIAL.

## Progress P-40 — aksesibilitas dasar dan gerak

- Bahasa dokumen dan metadata halaman utama disesuaikan ke Bahasa Indonesia/Makare.
- App shell mendapat tautan lewati ke konten utama dan target fokus yang jelas; tombol pembuka menu seluler mengumumkan status expanded serta kontrol terkait.
- Tombol buka rincian gaji dan unduh slip di detail periode memakai label yang menyebut nama karyawan; kontrol rincian juga mengumumkan expanded state.
- Preferensi `prefers-reduced-motion` sekarang mengurangi animasi, transisi, dan smooth scrolling.
- Fokus yang terlihat sudah tersedia lewat aturan global `:focus-visible`; P-40/AUD-15 masih PARTIAL.
- Login sekarang memakai label eksplisit untuk username/kata sandi, ikon dekoratif disembunyikan dari pohon aksesibilitas, dan status submit tetap punya nama yang bisa diumumkan.
- Browser lokal: halaman login punya satu landmark `main`; Tab pertama fokus pada Username. Pada lebar 320, 375, 768, dan 1280 px, tidak ada horizontal overflow.
- Sesi Administrator tersedia untuk audit lanjutan. Semua 10 rute admin dinavigasi via menu pada lebar 375 px; masing-masing merender heading utama dan landmark `main`, tanpa overflow horizontal. Tab Pengaturan juga diperiksa; kontrol yang awalnya tanpa nama kini memiliki nama eksplisit, dan pemeriksaan ulang tidak menemukan input/tombol/tab tanpa nama.
- Menu mobile kini diumumkan sebagai dialog modal, mengirim fokus ke Dashboard saat dibuka, mengurung Tab/Shift+Tab, menutup dengan Escape, dan mengembalikan fokus ke tombol pemicu. Browser mengonfirmasi empat perilaku tersebut. Tautan lewati memfokuskan main, reduced motion menghasilkan animasi `0.01ms`.
- P-40/AUD-15 masih PARTIAL: pemeriksaan kontras, touch target terukur, perangkat pembaca layar, dan detail overflow tabel/halaman kiosk belum selesai.


## Progress P-11 ? eksklusivitas sesi lintas jalur

- Jalur input manual admin/operator dan koreksi admin sebelumnya hanya mengandalkan unique index per tabel, sehingga sesi reguler dapat dibuka ketika sesi lembur masih terbuka.
- Kedua jalur kini mengambil advisory transaction lock karyawan yang sama dengan `services.clock` (`1001, employee_id`), memeriksa lembur terbuka sebelum membuat/membuka sesi reguler, dan koreksi mengunci sesi setelah advisory lock untuk menjaga urutan lock konsisten.
- Pemeriksaan terbatas: `python -m py_compile backend/schema.py backend/routes_attendance.py` berhasil; `git diff --check` bersih. Belum ada concurrency/API test, dan tidak ada data absensi yang diubah. P-11 tetap PARTIAL sampai race test dijalankan pada DB sintetis.

## Progress AUD-06 ? migrasi ber-versi

- DDL startup dipindahkan ke `backend/migrations/001_initial_schema.sql`; runner `init_db` membuat ledger `schema_migrations`, menerapkan file SQL berurutan di transaksi startup dengan advisory lock, mencatat SHA-256, dan menghentikan startup jika checksum migration yang sudah dipakai berubah atau berkas migration tidak tersedia.
- `backend/migrations/README.md` menetapkan file immutable dan kebijakan forward-only dengan restore/forward fix sebagai pemulihan. Migration belum dijalankan pada target yang belum dibuktikan non-production; empty/legacy upgrade, recovery, dan schema contract masih pending.
- Context7 asyncpg docs mengonfirmasi pola `async with connection.transaction()` meng-commit/rollback otomatis untuk DDL/data migration.
- Syntax check untuk `schema.py` lulus; `git diff --check` bersih. Tidak ada test suite atau database yang dijalankan pada slice ini.


## Progress P-01/P-02 ? pencabutan sesi dan pengelolaan peran

- Sebelum perubahan, JWT hanya bergantung pada expiry; logout hanya menghapus token browser. Migration `002_user_session_revocation.sql` menambah `users.session_version`. JWT baru membawa versi; setiap request mencocokkan versi itu dengan database. Logout menaikkan versi dan mencatat audit, sedangkan perubahan role/status/reset password juga menaikkan versi dalam transaksi mutasi user. Token lama ditolak saat request berikutnya.
- UI kini dapat mengganti role akun yang sudah dibuat. Jika role/password/status akun sendiri diubah, admin diarahkan kembali ke login karena server sudah mencabut seluruh sesi akun itu. Logout biasa memberi pesan jika koneksi gagal dan server belum mengonfirmasi revoke.
- Validasi password akun kini membatasi panjang 8-72 byte UTF-8, konsisten dengan batas bcrypt; sumber test current-user ditambah untuk versi sesi yang sudah dicabut. Test tidak dijalankan pada slice ini.
- Acceptance runtime belum dijalankan karena target database yang dikonfigurasi adalah host Neon cloud dan status non-production belum dibuktikan. P-01/P-02 tetap PARTIAL sampai migrasi dan API/session matrix tervalidasi di isolasi.

- Lanjutan akun: admin kini dapat mengubah nama dan role akun existing. Audit menyimpan role/status before-after serta nama field berubah, tanpa menyalin nama/password. Password API tervalidasi dalam rentang 8-72 byte UTF-8 untuk mencegah kegagalan bcrypt yang sebelumnya dapat muncul sebagai 500. Build produksi frontend berhasil (`npx --yes yarn@1.22.22 build`, exit 0); `python -m py_compile backend/security.py backend/routes_admin.py backend/schema.py` dan `git diff --check` berhasil. Regression test sumber untuk session-version revoke ditambahkan tetapi belum dijalankan; runtime DB tidak disentuh.


## Progress P-07 ? validasi lintas field pengaturan jadwal

- `SettingsIn` sebelumnya memastikan sintaks/rentang tiap jam, tetapi membolehkan duplikasi/hari di luar 1-7, nama perusahaan whitespace, jam mulai sama dengan selesai, dan istirahat di luar shift.
- Validasi lintas-field kini memastikan workdays unik ISO 1-7, shift tidak nol (overnight diperbolehkan), istirahat valid berada penuh di dalam shift termasuk lintas tengah malam, nama perusahaan nonblank, dan maksimum 20 interval istirahat. Regression cases ditambahkan untuk invalid configurations serta valid overnight break.
- Pydantic v2.14.1 docs di Context7 menegaskan `model_validator(mode="after")` memvalidasi instance tervalidasi dan harus mengembalikan instance. Test tidak dijalankan pada slice ini; API persistence dan kebijakan numeric/effective-date masih pending.


## Progress P-33 ? status kerja efektif pada laporan absensi

- Laporan sebelumnya menginferensikan `tanpa_catatan` hanya dari `employees.active` saat ini. Akibatnya, deactivation menghapus inferensi pada seluruh tanggal lama, atau riwayat yang dipilih untuk pegawai nonaktif tidak menunjukkan hari saat pegawai masih bekerja.
- Laporan kini membaca audit transisi status `employee_activated`/`employee_deactivated` dan merekonstruksi status saat awal shift; employee baru aktif secara default sejak tanggal masuk. Hari kerja yang berada setelah tanggal nonaktif tidak dianggap alfa, sedangkan catatan hadir/lembur eksplisit tetap ditampilkan. Route perubahan status kini mengaudit before/after dan no-op tidak membuat event palsu.
- Regression test source dibuat untuk deactivation sebelum/selepas awal shift, reactivation, dan batas waktu tepat awal shift. Source compile serta diff hygiene telah diperiksa; test/API/PDF fixture belum dijalankan. P-33 masih PARTIAL sampai acceptance database dan filter direkonsiliasi.

## Lanjutan P-20/P-39/P-40 � pencarian dan dialog kiosk

- Pencarian karyawan kini memiliki status mencari, hasil kosong, dan error API yang berbeda; kegagalan jaringan menampilkan pesan serta aksi coba lagi. Respons dari query yang sudah kedaluwarsa diabaikan.
- Dialog PIN, konfirmasi, dan hasil memiliki nama aksesibel, modal semantics, focus trap Tab/Shift+Tab, fokus awal, Escape untuk menutup, dan pemulihan fokus. Kontrol keypad diberi label aksesibel; pilihan mode absensi diumumkan sebagai tombol toggle, bukan tab tanpa panel.
- Token lembur sessionStorage kini diisolasi per token kiosk agar kiosk berbeda dalam tab yang sama tidak berbagi nilai token.
- `npx --yes yarn@1.22.22 build` berhasil (compiled successfully); `git diff --check` bersih. Belum ada acceptance browser/error-injection, screen reader, kontras, pengukuran touch target, atau uji API/database; P-20/P-39/P-40 tetap PARTIAL.
