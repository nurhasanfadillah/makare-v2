# MASTER IMPLEMENTATION PROMPT — MAKARE
## Manajemen Karyawan Redone

### 1. Peran dan tujuan

Bertindak sebagai tim pengembang aplikasi senior yang mencakup Product Engineer, Software Architect, Database Engineer, UI/UX Engineer, Security Engineer, dan QA Engineer.

Bangun MAKARE, aplikasi manajemen karyawan berbahasa Indonesia untuk mengelola data karyawan, absensi, jam kerja, lembur, kasbon, penggajian, catatan karyawan, laporan, dan tutup buku.

Tujuan implementasi adalah menghasilkan aplikasi yang benar-benar berfungsi, aman, dapat diuji, dan siap dikembangkan. Jangan berhenti pada dashboard statis atau mockup.

**Instruksi awal:**
1. Periksa kode, struktur direktori, dependensi, konfigurasi, halaman, komponen, database, dan integrasi yang sudah ada.
2. Buat laporan singkat tentang kondisi aktual proyek.
3. Identifikasi fitur yang sudah berjalan, belum selesai, masih berupa mockup, dan belum tersedia.
4. Buat rencana implementasi bertahap berdasarkan kondisi aktual.
5. Setelah itu, implementasikan secara bertahap. Jangan menulis ulang seluruh proyek jika perubahan terarah sudah cukup.
6. Jangan mengubah atau menghapus data yang sudah ada tanpa persetujuan eksplisit.
7. Jangan mengklaim suatu fitur selesai sebelum implementasi dan pengujiannya dapat diverifikasi.

### 2. Ketentuan yang sudah final

Semua ketentuan berikut adalah keputusan produk yang sudah disetujui. Jangan menggantinya dengan asumsi baru.

**UI/UX final**

- Midnight Navy: `#0B1F3A`
- Royal Blue: `#174EA6`
- Gradient Blue: `#4F7DF3`
- Cool Canvas: `#F4F7FB`
- Surface utama: `#FFFFFF`
- Gradasi utama: `#174EA6` menuju `#4F7DF3`
- Mode terang.
- Kepadatan antarmuka seimbang.
- Karakter korporat premium seperti aplikasi perbankan.
- Gradasi tegas dan dominan pada area visual utama, tetapi tabel dan formulir tetap terang serta mudah dibaca.

**Peran pengguna**

1. Administrator: akses penuh sesuai izin.
2. Operator Input: hanya mencatat absensi hari ini.
3. Mode Input Publik/Kiosk: akses absensi melalui tautan publik aktif tanpa akses ke panel admin.

**Aturan bisnis yang telah disepakati**

- ID karyawan otomatis, unik, dan tidak berubah.
- Karyawan memiliki status aktif atau nonaktif.
- Mode payroll: Harian Berbasis Jam dan Manual.
- Status absensi: Hadir, Sakit, Izin, dan Alfa.
- Status Alfa hanya untuk dokumentasi dan analisis; tidak otomatis mengurangi gaji.
- Jadwal kerja dan istirahat menggunakan pengaturan global pada tahap awal.
- Waktu transaksi resmi berasal dari server dengan zona waktu aplikasi WIB.
- Shift lintas tengah malam mengikuti tanggal Masuk.
- Durasi disimpan dalam menit dan ditampilkan sebagai jam serta menit.
- Operator tidak dapat mengubah absensi historis.
- Keluar lebih awal membutuhkan PIN khusus yang berumur pendek dan terikat pada transaksi. degenerate oleh administrator.
- Kiosk tidak menyimpan antrean transaksi offline.
- Lembur menggunakan sesi terpisah dan harus ditolak oleh server jika fitur lembur nonaktif.
- Tarif reguler, tarif lembur, dan komponen gaji manual dapat ditentukan per karyawan.
- Perubahan data master tidak boleh mengubah payroll historis secara diam-diam.
- Payroll final disimpan sebagai snapshot yang tidak dapat diedit langsung.
- Koreksi payroll dilakukan melalui transaksi penyesuaian yang tercatat.
- Potongan kasbon tidak boleh melebihi saldo tersedia atau gaji bersih sebelum kasbon.
- Gaji bersih setelah kasbon tidak boleh negatif.
- Tutup buku harus atomik dan tidak boleh menghasilkan finalisasi atau potongan ganda.

### 3. Audit awal dan strategi perubahan

Sebelum mengimplementasikan fitur:

- Periksa struktur proyek dan framework yang benar-benar digunakan.
- Identifikasi halaman, komponen, API, model data, autentikasi, serta integrasi yang sudah ada.
- Periksa apakah data menggunakan database nyata atau hanya array lokal dan data contoh.
- Periksa apakah kontrol akses ditegakkan di server atau hanya melalui antarmuka.
- Periksa pengujian, konfigurasi lingkungan, migrasi database, dan penanganan error.
- Buat daftar gap dengan prioritas Critical, High, Medium, dan Low.
- Pertahankan komponen dan pola yang sudah baik.
- Hindari perubahan dependensi besar tanpa alasan teknis yang jelas.

Jangan mengklaim audit berhasil jika file atau konfigurasi yang relevan tidak dapat diakses. Laporkan keterbatasan tersebut.

### 4. Arsitektur dan standar kode

Target arsitektur yang direncanakan:

- TypeScript.
- Next.js App Router dan React.
- Tailwind CSS dan shadcn/ui.
- Neon PostgreSQL.
- Drizzle ORM.
- Better Auth.
- Zod untuk validasi.
- React Hook Form untuk formulir kompleks.
- TanStack Query jika pola pengambilan data client memang membutuhkannya.
- Vitest untuk pengujian unit/integrasi yang sesuai.
- Playwright untuk pengujian alur end-to-end.
- GitHub Actions untuk pemeriksaan otomatis.
- Vercel sebagai target deployment yang direncanakan.

Gunakan satu aplikasi modular dengan pemisahan fitur yang jelas. Hindari microservices atau lapisan abstraksi tambahan tanpa kebutuhan nyata.

Struktur yang direkomendasikan, disesuaikan dengan framework aktual:

- `src/app/` — routing dan halaman.
- `src/features/employees/`
- `src/features/attendance/`
- `src/features/overtime/`
- `src/features/cash-advances/`
- `src/features/payroll/`
- `src/features/closing/`
- `src/features/reports/`
- `src/features/employee-notes/`
- `src/features/settings/`
- `src/features/kiosk/`
- `src/components/ui/`
- `src/lib/`
- `src/server/`
- `src/db/`
- `src/tests/`

Jangan membuat direktori kosong yang tidak diperlukan. Simpan aturan bisnis dalam modul yang dapat diuji, bukan tersebar di komponen UI.

Gunakan TypeScript yang ketat, fungsi dengan tanggung jawab jelas, validasi server, penanganan error konsisten, dan konfigurasi environment yang tervalidasi. Jangan pernah mengekspos secret atau kredensial database ke browser.

### 5. Design system MAKARE

Implementasikan token desain terpusat:

- Primary dark: `#0B1F3A`
- Primary: `#174EA6`
- Primary gradient: `linear-gradient(110deg, #174EA6 0%, #4F7DF3 100%)`
- Page background: `#F4F7FB`
- Surface: `#FFFFFF`
- Main text: `#172A46`
- Secondary text: warna netral dengan kontras yang memadai
- Border: abu-abu kebiruan lembut
- Success: hijau semantik
- Warning: amber semantik
- Error/destructive: merah semantik

Warna status harus selalu disertai teks atau ikon yang relevan. Jangan mengandalkan warna saja, dengan menyesuaikan desain jangan mengorbankan estetika.

Gunakan:

- Tipografi sans-serif profesional.
- Hierarki heading, label, angka, dan metadata yang jelas.
- Radius komponen konsisten.
- Bayangan ringan dan terukur.
- Ikon dari satu sistem yang konsisten.
- Fokus keyboard yang terlihat.
- Tombol dan target sentuh yang nyaman.
- Komponen reusable untuk form, tabel, badge status, dialog, alert, toast, loading, empty state, dan error state.

Gradasi dominan pada header dashboard, hero area, ringkasan KPI terpilih, dan kiosk. Jangan memberikan gradasi pada setiap kartu atau baris tabel.

Semua halaman harus menggunakan design token yang sama. Jangan menulis warna secara acak per halaman.

### 6. Modul dan perilaku aplikasi

#### A. Dashboard

Tampilkan ringkasan yang relevan:

- Karyawan aktif.
- Kehadiran hari ini.
- Keterlambatan.
- Aktivitas terbaru yang diizinkan.
- Status periode payroll.
- Ringkasan lembur atau kasbon bila relevan.

Dashboard harus menggunakan data database nyata ketika backend tersedia. Selama menggunakan data demo, tampilkan label yang jelas bahwa data tersebut hanya contoh.

#### B. Data Karyawan

Fitur:

- Daftar, pencarian, filter, detail, tambah, edit, dan nonaktifkan karyawan.
- ID unik dan tidak dapat diedit setelah dibuat.
- Nama lengkap, jenis kelamin, alamat, tanggal lahir, nomor KTP opsional, kontak, departemen (data dikelola di setting atau sesuikan agar bisa di tambah, edit dan hapus), tanggal masuk, mode payroll, serta status aktif/nonaktif.
- Tarif reguler, tarif lembur, dan komponen manual per karyawan sesuai mode payroll.
- Validasi data wajib dan keunikan ID.
- Pembatasan akses terhadap data pribadi sensitif.

Karyawan nonaktif tidak boleh melakukan absensi baru.

#### C. Absensi manual

Alur:

1. Pilih karyawan.
2. Pilih status Hadir, Sakit, Izin, atau Alfa.
3. Tanggal otomatis hari ini.
4. Jika Hadir, waktu awal menggunakan waktu server.
5. Simpan dan tampilkan hasil.

Operator hanya boleh melakukan input hari ini. Perubahan tanggal dan koreksi historis hanya tersedia melalui izin administrator yang sesuai.

#### D. Absensi berbasis sesi

Alur:

1. Pilih karyawan.
2. Server memeriksa status karyawan dan sesi aktif.
3. Catat Masuk dengan waktu server.
4. Catat Keluar hanya jika ada Masuk valid yang belum ditutup.
5. Hitung durasi efektif setelah pengurangan istirahat yang berlaku.

Tolak sesi ganda, Keluar tanpa Masuk, karyawan nonaktif, serta transaksi yang tidak valid. Gunakan constraint dan/atau transaksi database untuk menangani permintaan bersamaan.

#### E. Jam Kerja dan Istirahat

Sediakan pengaturan global:

- Hari kerja.
- Jam masuk dan pulang reguler.
- Jadwal istirahat.
- Toleransi keterlambatan.
- Aturan pengakuan jam pertama.
- Aturan pembulatan durasi.
- Batas jam reguler.
- Kebijakan Keluar lebih awal.

Perubahan pengaturan penting harus diaudit dan tidak boleh mengubah payroll final yang sudah terkunci.

#### F. Lembur

Sediakan:

- Aktivasi/nonaktivasi lembur.
- Sesi Masuk/Keluar lembur terpisah.
- Tarif lembur per karyawan.
- Riwayat dan validasi sesi.
- Pengaturan istirahat lembur yang jelas.

Jika lembur nonaktif, backend wajib menolak transaksi lembur baru meskipun frontend dimanipulasi.

#### G. Kasbon

Sediakan:

- Pencatatan pemberian kasbon.
- Riwayat transaksi.
- Saldo tersedia.
- Potongan yang diusulkan pada payroll.
- Saldo setelah potongan.
- Hubungan transaksi kasbon dengan periode payroll.

Rumus batas potongan:

`Potongan Kasbon = min(Saldo Kasbon Tersedia, max(0, Gaji Bersih Sebelum Kasbon))`

Sisa kasbon dibawa ke periode berikutnya. Hindari memperbarui saldo melalui edit langsung tanpa transaksi yang dapat ditelusuri.

#### H. Penggajian

Dua mode payroll:

**Harian Berbasis Jam**

`Gaji Kotor = (Tarif Reguler × Jam Dibayar) + (Tarif Lembur × Jam Lembur Valid) + Tambahan Penghasilan`

**Manual**

`Gaji Kotor = jumlah seluruh (Nominal Komponen × Volume)`

Komponen manual dapat memiliki nama, nominal, volume, dan keterangan. Absensi tetap tersedia untuk dokumentasi, tetapi tidak otomatis menentukan gaji pada mode Manual.

Payroll harus menampilkan:

- Periode penggajian.
- Durasi aktual.
- Durasi istirahat.
- Penyesuaian keterlambatan.
- Durasi yang memenuhi syarat.
- Hasil pembulatan.
- Jam dibayar.
- Jam dan nominal lembur.
- Komponen tambahan.
- Gaji kotor.
- Potongan sah lainnya.
- Gaji bersih sebelum kasbon.
- Saldo kasbon.
- Potongan kasbon.
- Gaji bersih akhir.

Nominal ditampilkan dalam Rupiah dengan format konsisten. Jangan menyembunyikan dasar perhitungan di balik angka total.

#### I. Tutup Buku

Alur:

1. Ambil tanggal awal dari hari setelah tutup buku terakhir.
2. Administrator memilih tanggal akhir yang tidak melebihi hari ini.
3. Sistem membuat pratinjau payroll.
4. Administrator memeriksa seluruh rincian.
5. Administrator menyesuaikan potongan kasbon dalam batas.
6. Sistem menampilkan ringkasan final.
7. Administrator mengonfirmasi.
8. Server mengunci periode, menyimpan snapshot payroll, mencatat potongan kasbon, dan menyelesaikan periode berikutnya sebagai satu transaksi atomik.

Ketentuan:

- Finalisasi harus idempoten.
- Klik ganda atau request berulang tidak boleh membuat snapshot maupun potongan ganda.
- Kegagalan transaksi harus di-rollback.
- Periode terkunci tidak dihitung ulang secara diam-diam.
- Slip gaji dan rekap final menggunakan snapshot yang tersimpan.

#### J. Mode Koreksi

Koreksi wajib:

- Memerlukan hak akses yang tepat.
- Memerlukan alasan.
- Menyimpan aktor, waktu, referensi periode, dan transaksi terkait.
- Menampilkan nilai sebelum dan sesudah bila relevan.
- Menunjukkan dampak finansial sebelum konfirmasi.
- Menyimpan perubahan sebagai transaksi penyesuaian.
- Tidak menimpa snapshot payroll asli.
- Tidak menggandakan potongan kasbon.

#### K. Catatan Karyawan

Sediakan judul/kategori, tanggal, isi catatan, pembuat, waktu pembuatan, riwayat perubahan penting, dan pembatasan akses.

#### L. Laporan dan PDF

Sediakan:

- Daftar Karyawan PDF.
- Rekap Gaji PDF.
- Slip Gaji PDF.
- Rekap Kehadiran PDF.
- Laporan Kehadiran.
- Laporan Penggajian.
- Laporan Kasbon.
- Riwayat Tutup Buku.

Laporan periode final harus menggunakan snapshot dan penyesuaian resmi. Jangan menghitung ulang histori dari data master terbaru.

#### M. Pengaturan dan audit

Sediakan pengaturan identitas perusahaan, jadwal kerja, istirahat, toleransi keterlambatan, tarif, lembur, PIN keluar lebih awal, akun, role, serta tautan kiosk.

Catat perubahan penting dengan pelaku, waktu, nilai sebelum/sesudah bila relevan, dan hasil operasi.

### 7. Aturan payroll: keterlambatan dan pembulatan

Aturan berikut harus diimplementasikan sebagai fungsi bisnis terpisah dan diuji otomatis.

Contoh jadwal: masuk 08.00, pulang 17.00, istirahat satu jam, toleransi keterlambatan 30 menit.

- Masuk 08.10: status terlambat, tetapi pengakuan jam pertama tetap berlaku.
- Masuk 08.31 atau 08.35: keterlambatan melampaui toleransi sehingga jam pertama tidak diakui.
- Sisa durasi 0–29 menit: pembulatan turun.
- Sisa durasi 30–59 menit: pembulatan naik.
- Pembulatan hanya dilakukan sekali setelah penyesuaian yang relevan.
- Pembulatan tidak boleh mengembalikan jam pertama yang sudah gugur.
- Jam reguler dibatasi sampai akhir jadwal.
- Jam setelah jadwal tidak otomatis menjadi lembur.
- Istirahat yang beririsan dengan sesi kerja dikurangi sesuai kebijakan.
- Durasi efektif tidak boleh negatif.

Contoh pembulatan durasi yang memenuhi syarat:

| Durasi | Hasil |
|---|---:|
| 7 jam 28 menit | 7 jam |
| 7 jam 30 menit | 8 jam |
| 7 jam 32 menit | 8 jam |

Pisahkan durasi mentah, penyesuaian keterlambatan, durasi yang memenuhi syarat, hasil pembulatan, dan jam dibayar.

Jangan menebak aturan untuk kasus yang belum ditentukan. Buat daftar keputusan terbuka untuk ditinjau pemilik produk sebelum mengaktifkan payroll produksi.

### 8. Kiosk publik

Kiosk harus menjadi pengalaman terpisah:

- Layar penuh tanpa navigasi admin.
- Jam dan tanggal dengan acuan waktu server WIB.
- Pencarian karyawan menggunakan nama atau ID. Hanya menampilkan data karyawan dengan mode gaji harian jam.
- Pilihan Reguler/Lembur. Membuka mode lembur harus memasukan PIN dari admin saat awal membuka tab saja.
- Dialog konfirmasi sebelum transaksi.
- Status sukses/gagal yang jelas.
- Bersihkan pilihan dan data setelah transaksi atau pembatalan.
- Tidak menampilkan gaji, kasbon, KTP, alamat, nomor HP, atau catatan pribadi.
- Tombol Masuk/Keluar ditampilkan bergantian, jika belum ada status masuk maka tombol Masuk yang terlihat dan jika sudah Masuk tombol berganti jadi tombol Keluar
- Tombol sentuh besar.

Token publik harus acak, sulit ditebak, dapat dinonaktifkan, dan dapat dirotasi. Setelah rotasi, token lama langsung tidak berlaku.

Server harus memvalidasi token, status karyawan, status sesi, mode transaksi, waktu, serta aturan bisnis pada saat penyimpanan. Permintaan bersamaan tidak boleh membuat transaksi ganda.

PIN keluar lebih awal tidak boleh membuka sesi admin penuh dan tidak boleh disimpan sebagai rahasia jangka panjang di browser kiosk.

### 9. Keamanan dan privasi

Wajib menerapkan:

- Autentikasi yang sesuai untuk akun admin/operator dan manajemen akun oleh administrator.
- Otorisasi server pada setiap tindakan sensitif.
- Least privilege.
- Validasi server terhadap semua input yang tidak dipercaya.
- Proteksi sesi dan endpoint.
- Rate limiting untuk endpoint publik dan percobaan PIN.
- HTTPS pada lingkungan deployment.
- Secret hanya di environment server.
- Audit log untuk tindakan penting.
- Perlindungan data pribadi dan finansial.
- Transaksi atomik dan constraint database.
- Pencegahan request berulang.
- Pesan error yang aman tanpa membocorkan informasi internal.
- Backup dan prosedur pemulihan.

**Tujuan akhir:** MAKARE harus menjadi aplikasi manajemen karyawan yang dapat digunakan secara nyata, dengan UI/UX sesuai persetujuan final, payroll yang dapat diaudit, keamanan transaksi yang benar, dan histori keuangan yang tetap konsisten.

Kredensial yang diperlukan
Vercel: [REDACTED_VERCEL_TOKEN]
NeonDB: [REDACTED_NEON_DATABASE_URL]
Github: [REDACTED_GITHUB_TOKEN]
