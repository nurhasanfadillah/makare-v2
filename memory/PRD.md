# MAKARE â€” PRD dan Sumber Rencana Produk

Dokumen ini adalah ringkasan kerja produk dan status repo, bukan pengganti spesifikasi. Acceptance criteria lengkap, ERD konseptual, skenario uji, keputusan terbuka, dan tahapan produk tetap merujuk ke [Spesifikasi Lengkap v1.1](../doc/MAKARE_Spesifikasi_Lengkap_v1.1.md). Instruksi implementasi dan cakupan modul merujuk ke [Master Implementation Prompt](../doc/MAKARE_MASTER%20IMPLEMENTATION%20PROMPT%20FOR%20BUILD.md); gate audit, keamanan, verifikasi, dan release merujuk ke [MAKARE 2 Master Execution Prompt](../doc/MAKARE_2_Master_Execution_Prompt_Production_Readiness.md).

**Tanggal konsolidasi:** 2026-10-31
**Status produk:** dalam pengembangan; belum terbukti siap rilis.
**Status bukti pada sesi ini:** audit statis dan pemeriksaan sintaks terbatas; acceptance produk, test suite, build frontend, staging, dan database non-production belum diverifikasi.

## 1. Visi dan cakupan produk

MAKARE adalah aplikasi administrasi karyawan berbahasa Indonesia untuk mengelola karyawan, absensi, jam kerja, lembur, kasbon, payroll, tutup buku, koreksi periode final, catatan karyawan, laporan/PDF, pengaturan, akun/role, kiosk publik, dan audit.

Cakupan yang tercantum dalam spesifikasi adalah keseluruhan plan produk. Pernyataan PRD lama â€œrilis pertama: inti duluâ€ dibaca sebagai pelaksanaan bertahap, bukan penghapusan modul wajib. Seluruh fitur tetap dilacak sampai selesai atau sampai pemilik secara tertulis menyetujui penundaan/penghapusan.

Personas:

- **Administrator:** tindakan administratif dan payroll sesuai otorisasi.
- **Operator Input:** absensi hari ini sesuai batas akses server; tidak mendapat akses ke payroll, kasbon, settings, catatan pribadi, atau koreksi historis.
- **Kiosk publik:** absensi melalui token aktif, tanpa akses panel admin atau data pribadi/finansial.

Prinsip produk: waktu dan keputusan transaksi divalidasi server; data final payroll disimpan sebagai snapshot immutable; koreksi menggunakan transaksi terpisah yang terlacak; absensi Alfa tidak otomatis memotong gaji; kasbon dan finalisasi bersifat transaksional/idempoten; kiosk tidak menyimpan transaksi offline.

## 2. Sumber kebenaran dan konflik

Urutan prioritas mengikuti MAKARE 2: keputusan bisnis/UI yang eksplisit dan disetujui pemilik, spesifikasi lengkap yang disetujui, implementasi aktual, lalu asumsi engineering. Dokumen implementasi lama memuat ketentuan â€œfinalâ€, sedangkan spesifikasi v1.1 juga menyimpan sejumlah pertanyaan terbuka. Jangan menutup konflik itu dengan asumsi diam-diam.

| Topik | Sumber dan kondisi | Perlakuan PRD |
|---|---|---|
| Cakupan produk | Spesifikasi v1.1 dan prompt implementasi mencantumkan modul Aâ€“M; PRD lama menyebut rilis inti dahulu. | Semua modul tetap backlog wajib dengan urutan bertahap. Perubahan cakupan memerlukan keputusan pemilik. |
| Stack | Repo saat ini React/CRA + JavaScript + Tailwind/shadcn dan FastAPI/asyncpg/PostgreSQL. Prompt implementasi mencantumkan Next.js/TypeScript/Drizzle/Better Auth/Vercel sebagai arsitektur target, sementara spesifikasi v1.1 mengatakan pilihan final mengikuti audit. | Stack aktual adalah fakta repo. Target lama adalah opsi/arah, bukan mandat rewrite yang terbukti disetujui. Pertahankan arsitektur modular saat ini sampai pemilik menyetujui perubahan material. Database Neon dicatat sebagai pilihan pengguna di PRD lama, tetapi koneksi/environment tidak diverifikasi sesi ini. |
| Arah visual | Prompt implementasi menyebut gradien 110deg; spesifikasi v1.1 menyebut 135deg. Palet dan light mode sama. | Konflik sudut gradien belum diputuskan. Pertahankan palet/light mode; jangan melakukan redesign atau mengubah token gradien sebelum keputusan dikunci. |
| Toleransi tepat di batas | Spesifikasi v1.1 menyatakan default 08:30 inklusif; implementasi harus konsisten. | Catat sebagai keputusan spesifikasi sementara dan verifikasi bahwa kode sesuai; jangan mengubah tanpa bukti keputusan lebih baru. |
| Jam pertama terlambat | Spesifikasi mewajibkan blok jam pertama jadwal dikecualikan secara konsisten, tetapi mengakui definisi interval dan interaksi istirahat perlu diuji. | P0: verifikasi fungsi aktual dan semua kasus kombinasi; keputusan yang berdampak pada gaji harus dikunci sebelum payroll produksi. |
| Pengakuan durasi gaji | Klarifikasi pemilik terbaru: menit toleransi ditambahkan ke durasi eligible lalu jam dibayar dibulatkan ke bawah: `floor((eligible_minutes + tolerance_minutes) / 60) * 60`; berlaku regular dan overtime. Overtime mulai dihitung pada akhir jadwal reguler meski tombol Masuk lembur ditekan lebih awal. | Formula dan clamp overtime menjadi acceptance baru. Toleransi mana yang menjadi `tolerance_minutes` (setting toleransi terlambat vs ambang pembulatan vs setting terpisah) masih dimintakan konfirmasi; urutan terhadap blok jam pertama/istirahat tetap diuji. |
| Default potongan kasbon | Spesifikasi v1.1 dan MAKARE 2 mengharuskan usulan awal Rp0 tanpa override; batas tetap saldo dan net sebelum kasbon. | Kriteria wajib. PRD lama belum menyebut bug/default aktual dengan jelas; verifikasi UI â†’ preview â†’ server â†’ finalisasi. |
| Rilis production | MAKARE 2 melarang status production-ready tanpa test kritis, migration, keamanan, backup/restore dan UAT yang terbukti. | Tidak ada klaim siap produksi berdasarkan dokumen atau keberadaan kode saja. |

### Keputusan produk yang masih terbuka dari spesifikasi Â§21

1. Single-company atau multi-tenant.
2. Apakah operator boleh mengoreksi catatan absensi hari ini sebelum tutup hari.
3. Definisi teknis blok jam pertama yang gugur dan interaksinya dengan istirahat/sesi terlambat.
4. Cara menghitung irisan istirahat saat terlambat, pulang awal, atau tidak bekerja selama seluruh interval.
5. Sumber setting menit toleransi pengakuan gaji dan urutannya setelah istirahat/blok jam pertama; formula pengakuan jam kini mengikuti klarifikasi pemilik.
6. Apakah tarif berada di level perusahaan, karyawan, atau kombinasi; rancangan mengasumsikan tarif aktual per karyawan dapat disnapshot.
7. Apakah koreksi memerlukan persetujuan administrator kedua.
8. Bentuk slip setelah koreksi; model spesifikasi memilih adjustment terpisah dengan snapshot asli tetap immutable.
9. Format employee ID dan kebijakan nomor yang tidak digunakan kembali.
10. Jadwal global atau beberapa jadwal/shift untuk fase awal.
11. Penanganan sesi yang tidak pernah ditutup dan kewenangan penutupan administratif.
12. Pembatalan transaksi keliru sebelum periode dikunci.
13. Kebutuhan cabang, mata uang selain IDR, pajak/iuran, ekspor akuntansi, dan integrasi eksternal.
14. Retensi, ekspor, backup, serta penghapusan data pribadi.

Keputusan mengenai waktu/gaji/data historis harus ditetapkan pemilik sebelum release payroll. Asumsi tidak boleh dianggap sebagai persetujuan.

## 3. Kriteria produk menurut modul

Rincian acceptance dan test tetap berada di spesifikasi v1.1 Â§Â§2â€“20. Daftar di bawah mengunci cakupan PRD agar tidak hilang ketika workstream audit berjalan.

| ID | Modul | Kriteria ringkas |
|---|---|---|
| P-01 | Auth, akun, role | Password aman, sesi kedaluwarsa/dapat dicabut, server memeriksa hak pada setiap route; akses operator/admin/kiosk terpisah. |
| P-02 | Karyawan/departemen | CRUD, cari/filter/detail, employee ID otomatis unik immutable, status aktif, tarif/komponen, PII dibatasi, perubahan penting diaudit. Karyawan nonaktif tak boleh absen. |
| P-03 | Dashboard | Ringkasan operasional berbasis data server, sesuai role, tanpa angka demo yang disamarkan sebagai nyata. |
| P-04 | Pengaturan | Identitas, hari/jam kerja, istirahat, toleransi, pembulatan, tarif, lembur, early leave, akun/role dan konfigurasi kiosk; perubahan penting menyimpan actor/time/before/after/effective policy. |
| P-05 | Absensi manual/operator | Status Hadir/Sakit/Izin/Alfa, tanggal hari ini untuk operator, waktu server, input/koreksi historis hanya admin dengan alasan dan audit. Alfa bukan potongan gaji. |
| P-06 | Absensi sesi | Server time, satu sesi terbuka, Keluar harus punya Masuk, status karyawan aktif, tanggal shift malam mengikuti tanggal Masuk, transaksi aman saat concurrent. |
| P-07 | Perhitungan waktu | Batas jadwal, overlap istirahat, toleransi, blok jam pertama, pembulatan satu kali, komponen durasi dapat diaudit; sesi terbuka punya kebijakan eksplisit. |
| P-08 | Lembur | Sesi tersendiri, durasi diakui hanya setelah akhir jadwal reguler (clamp jika Masuk lembur lebih awal), memakai formula toleransi pengakuan yang sama dengan regular, tarif dan istirahat sesuai kebijakan, server menolak ketika nonaktif, tidak terhitung ganda sebagai reguler. |
| P-09 | Kiosk/token | Token kuat, aktif/nonaktif/rotasi dan token lama ditolak server; hanya karyawan hourly aktif; PIN lembur sesuai kebijakan; UI fullscreen, konfirmasi, hasil server, reset state, tanpa antrean offline/PII. |
| P-10 | Kasbon | Grant/ledger/saldo, potongan awal Rp0, batas saldo dan net sebelum kasbon, saldo sisa terbawa, transaksi terkait snapshot, tidak ada pemotongan ganda. |
| P-11 | Payroll/preview | Mode hourly/manual; breakdown durasi/komponen/potongan; snapshot aturan dan tarif yang digunakan; Alfa tidak mengurangi gaji. |
| P-11a | Manajemen gaji manual | Halaman admin khusus menampilkan komponen master pada pratinjau periode berjalan dan snapshot per periode tutup buku; periode final hanya-baca dan koreksi memakai alur adjustment. Closing preview dapat menambah/mengubah/menghapus daftar komponen efektif periode; daftar yang difinalisasi masuk snapshot. Verifikasi UI/API/DB masih berjalan. |
| P-12 | Tutup buku | Rentang berurutan dan tidak overlap, preview, konfirmasi, snapshot immutable, kasbon, locking dan idempotensi dalam satu transaksi. |
| P-13 | Mode Koreksi | Alasan wajib, dampak before/after, actor/time/referensi, adjustment terpisah dan audit, tanpa mengubah snapshot; rekap/slip menampilkan koreksi. |
| P-14 | Catatan karyawan | Admin-only; judul/kategori/tanggal/isi/pembuat/waktu, riwayat perubahan, tidak tampil di kiosk/laporan publik. |
| P-15 | PDF dan laporan | Daftar karyawan, rekap gaji, slip, rekap/laporan kehadiran, payroll, kasbon, riwayat tutup buku; sumber periode final adalah snapshot + koreksi resmi. |
| P-16 | Audit | Aksi sensitif tercatat dengan aktor/waktu/entity/result dan before/after aman; audit tidak diedit melalui UI biasa; tanpa token/password/PII yang tak perlu. |
| P-17 | UX | Design system light mode, responsif desktop/tablet, kiosk touch-first, form validation, loading/ready/saving/success/error/network states, konfirmasi tindakan sensitif, akses keyboard/label/kontras. |
| P-18 | Keamanan dan operasional produk | HTTPS, RBAC, validasi, rate limit, idempotensi, transaksi DB, privasi, backup dan recovery. Kriteria teknis release dirinci di MAKARE 2. |

## 4. Stack dan kondisi repository

Fakta yang terlihat pada source saat audit 2026-10-31:

- Frontend: React 19, Create React App + CRACO, JavaScript, Tailwind, shadcn/ui, React Router.
- Backend: FastAPI + asyncpg; PostgreSQL; schema DDL dan seed dijalankan saat startup lewat `backend/schema.py`.
- Domain kode utama: `core.py`, `schema.py`, `security.py`, `rules.py`, `services.py`, `routes_admin.py`, `routes_attendance.py`, `routes_payroll.py`.
- Test backend tersedia pada `backend/tests/`; file test juga mencakup rule payroll, penyesuaian payroll, dan API.
- Branch saat pemeriksaan `main`, HEAD `99eab3c` (`Koreksi Payroll...`). Working tree telah memiliki perubahan lokal implementasi Catatan Karyawan dan direktori `doc/` untracked; perubahan itu dipertahankan dan bukan bukti keberhasilan produk.
- Lingkungan DB/deployment, migration versioned, CI, backup/restore, staging, dan UAT tidak dibuktikan melalui pemeriksaan ini.

## 5. Status implementasi yang diketahui

Gunakan `PARTIAL` untuk kode yang ada namun tidak melalui acceptance menyeluruh; `NOT VERIFIED` untuk klaim lama yang tidak diuji ulang. Tidak ada fitur yang dinyatakan `DONE â€” VERIFIED` dalam konsolidasi ini.

| Area | Status | Bukti yang diketahui | Gap utama |
|---|---|---|---|
| Auth/RBAC | PARTIAL | `security.py`, login, route guards, user management terlihat. | Matrix endpoint, token lifecycle, konfigurasi produksi, RBAC test belum dijalankan. |
| Karyawan/settings/absensi/kiosk | PARTIAL | Halaman dan route ada menurut source/PRD lama. | Audit end-to-end, privasi, race, semua edge case dan role matrix belum dibuktikan. |
| Kasbon/payroll/closing | PARTIAL | Route/services/schema dan test file ada; PRD lama melaporkan implementasi inti. | Default Rp0, perhitungan penuh, transaksi/concurrency, DB dan acceptance saat ini belum dijalankan. |
| Koreksi payroll | PARTIAL | Commit HEAD `99eab3c`; PRD lama menyebut preview/apply, audit, batas nilai dan PDF. | Klaim test pada 2026-10-25 adalah catatan historis, tidak diulang dalam sesi audit ini; acceptance live belum dibuktikan. |
| Catatan karyawan | PARTIAL â€” belum terverifikasi | Dalam working tree sesi ini ditambahkan schema, route admin, UI dan revisions. | Belum ada migration versioned; belum diuji terhadap DB, API, role, atau browser. |
| Laporan | PARTIAL/NOT VERIFIED | PDF payroll disebut PRD lama. | Cakupan daftar karyawan, attendance, payroll, kasbon serta filter/export belum ditelusuri tuntas. |
| UI responsif/a11y | NOT VERIFIED | UI design dan beberapa state component tampak di source. | Audit per halaman/viewport/keyboard/contrast belum dilakukan. |
| Database/migration | GAP | Auto-DDL startup terlihat; tidak ada migration directory terinventarisasi. | Versioning, schema drift, upgrade, rollback/recovery dan contract tests. |
| CI/test/build | GAP / NOT RUN | Test sources tersedia. | Test suite tidak dijalankan; frontend build tidak dijalankan karena `frontend/node_modules` tidak ada; workflow CI tidak ditemukan dalam inventaris. |
| Security/release ops | NOT VERIFIED | Sebagian kontrol terlihat di source. | CORS/config/secret/bootstrap/rate-limit/dependency, logs, backup/restore, runbooks, staging/UAT belum selesai. |

Riwayat test yang dicatat PRD terdahulu (iterasi 2026-10-25) dipertahankan sebagai catatan historis saja, bukan hasil verifikasi terkini. Pemeriksaan sesi konsolidasi: `python -m py_compile backend/schema.py backend/routes_admin.py` selesai tanpa syntax error; `git diff --check` selesai tanpa whitespace error. Test suite dan build frontend tidak dijalankan.

## 6. Backlog dan urutan pengerjaan

Backlog wajib mengikuti seluruh kriteria produk P-01 sampai P-42, keputusan DEC-01 sampai DEC-10, dan semua workstream audit/release di master tracker. Daftar modul di atas meringkas produk; setiap acceptance diuji dan dilacak terpisah. Urutan di bawah mengadaptasi tahapan spesifikasi §22 dan prioritas keselamatan MAKARE 2; urutan tidak membatalkan modul produk.

1. **P0 â€” Integritas bisnis dan data:** cocokkan seluruh aturan attendance/payroll dengan spec; periksa kasbon default Rp0 dan cap; time zone, overnight, break overlap, batas toleransi, jam pertama, rounding; payroll snapshot, koreksi, concurrency/idempotency.
2. **P0 â€” Fondasi database/keamanan:** database/schema drift, versioned migrations tanpa kehilangan histori, authorization matrix, secrets/bootstrap, CORS, rate limiting, input/privacy/audit.
3. **P1 â€” Tutup fitur produk:** validasi Catatan Karyawan; employee detail/change history; seluruh laporan/PDF; filter dan date picker; UX mobile/aksesibilitas.
4. **P1 â€” Verifikasi dan CI:** unit, API/database, migration, authorization, concurrency, frontend dan E2E; CI dengan data sintetis, lint dan build.
5. **P1 â€” Operabilitas:** structured logs/request IDs, health/readiness, backup policy dan restore drill, deployment/rollback, rotasi secret, incident response dan SOP/onboarding.
6. **Gate rilis:** staging dengan target terkonfirmasi, smoke test, UAT checklist dan persetujuan bisnis; laporan release hanya berdasarkan bukti aktual. Tidak ada perubahan production tanpa persetujuan eksplisit.
7. **P2 â€” Kinerja/penyempurnaan:** ukur latency database/app sebelum optimasi; responsif/mobile card Absensi dan perbaikan UX hanya berdasarkan gap terverifikasi.

Rencana batch, dependensi, dan exit gate berikutnya ada di [`EXECUTION-PLAN.md`](../docs/production-readiness/EXECUTION-PLAN.md). Output/backlog terperinci untuk setiap item, status dan bukti akhir berada di [`MASTER-PLAN-TRACKER.md`](../docs/production-readiness/MASTER-PLAN-TRACKER.md). Tracker tersebut memuat acceptance spesifikasi, keputusan bisnis, audit dan release; ringkasan status di dokumen ini tidak menggantikan tracker.

## 7. Risiko yang ditemukan dalam sumber

- Prompt implementasi di `doc/` memuat nilai kredensial/secret dalam plaintext. Nilai tersebut sengaja tidak disalin ke PRD/tracker. Pemilik sistem perlu memperlakukan credential terkait sebagai terekspos dan merotasinya melalui proses yang aman; jangan memasukkan nilai baru ke repo atau log.
- Konfigurasi default CORS wildcard di backend dan bootstrap credentials/PIN di schema perlu ditinjau untuk environment produksi; keberadaannya di source tidak membuktikan bahwa nilai default masih aktif pada production.
- DDL saat startup tidak memberi migration history yang versioned/reviewable.
- Default potongan kasbon Rp0 adalah acceptance eksplisit yang perlu ditelusuri dari UI hingga finalisasi.
- Klaim test historis tidak membuktikan status runtime saat ini.

## 8. Kebijakan status dan perubahan PRD

- Jangan memakai `DONE â€” VERIFIED` tanpa acceptance aktual dan bukti.
- Catat `NOT RUN`, `BLOCKED`, atau `NEEDS BUSINESS DECISION` sesuai matriks MAKARE 2; jelaskan alasan/buktinya.
- Sumber spesifikasi tidak diubah oleh PRD. Update PRD ini hanya konsolidasi: scope, konflik, konteks stack, status bukti, backlog dan prioritas.
- Sebelum pekerjaan fitur berikutnya dipilih, perbarui master tracker agar benar-benar mencakup semua modul, aturan Â§20, keputusan Â§21, tahapan Â§22, serta workstream audit dan release. Setelah itu, implementasikan item berurutan tanpa menghilangkan item yang belum selesai.

## 9. Riwayat revisi

| Tanggal | Perubahan |
|---|---|
| 2026-10-25 | PRD awal merangkum rilis inti, koreksi payroll, status implementasi dan backlog. |
| 2026-10-31 | Konsolidasi terhadap seluruh dokumen plan di `doc/`; scope modul dan keputusan terbuka dirinci; konflik/stack/status test diberi label; Catatan dan temuan audit dicatat sebagai belum terverifikasi; rahasia dari sumber tidak disalin. |
