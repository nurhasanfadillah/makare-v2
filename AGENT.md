# STANDAR KERJA PROYEK APLIKASI

## 1. Tujuan dan Prinsip Utama

Bangun aplikasi yang benar-benar berfungsi, mudah digunakan, aman pada aspek fundamental, dan menyelesaikan kebutuhan operasional. Prioritaskan fitur inti, aturan bisnis, alur kerja end-to-end, serta UI/UX yang fungsional. Hindari analisis tanpa implementasi, fitur tambahan yang tidak diperlukan, abstraksi berlebihan, refactoring besar tanpa alasan, dan penyempurnaan detail sekunder ketika fungsi utama belum selesai.

Keputusan, kebutuhan, dan arsitektur yang sudah disepakati harus dipertahankan. Ubah hanya jika ditemukan alasan teknis atau bisnis yang kuat, lalu catat alasan dan dampaknya.

## 2. Discovery yang Efektif, Bukan Penghambat Implementasi

Ketika pengguna meminta dibuatkan aplikasi, tujuan utama agent adalah **membangun aplikasi yang berfungsi**, bukan berhenti pada analisis, proposal, atau dokumen.

1. Lakukan discovery secukupnya tetapi mendalam pada hal yang menentukan bentuk aplikasi: tujuan, pengguna/peran, alur bisnis utama, aturan kritis, data, integrasi, dan batasan.
2. Baca konteks yang sudah tersedia dari percakapan, lampiran, spesifikasi, PRD, tracker, repository, dan aplikasi berjalan. Jangan meminta ulang informasi yang sudah diberikan.
3. Tanyakan hanya hal yang benar-benar belum jelas dan berpotensi mengubah ruang lingkup, aturan bisnis, model data, keamanan, atau pilihan teknologi. Gabungkan pertanyaan penting secara efisien.
4. Untuk detail nonkritis, ambil keputusan yang paling masuk akal, catat sebagai asumsi, lalu lanjutkan implementasi. Jangan menunggu semua detail kecil diklarifikasi.
5. Discovery dapat berlanjut sambil membangun aplikasi. Perbarui pemahaman dan dokumen ketika fakta baru ditemukan.
6. Hindari wawancara panjang, analisis berulang, atau perencanaan yang terlalu rinci sebelum ada hasil nyata. Setelah tujuan dan alur utama cukup jelas, segera mulai membangun fondasi dan fitur.

**Default eksekusi:** bila pengguna meminta aplikasi dibuat, langsung kerjakan aplikasi sampai terbentuk dan seluruh modul dalam ruang lingkup telah diimplementasikan. Jangan hanya memberikan rencana, prompt, atau contoh kode ketika lingkungan dan akses yang tersedia memungkinkan implementasi langsung.

## 3. Dokumen dan Rencana Kerja yang Ringkas serta Hidup

Buat dokumentasi minimum yang cukup untuk mengarahkan implementasi, lalu lengkapi secara bertahap selama pengerjaan. Dokumen bukan gerbang birokratis yang boleh menunda pembangunan aplikasi.

- **Master Plan:** tujuan, ruang lingkup, urutan tahap, prioritas, dependensi, dan definisi selesai.
- **PRD:** pengguna, modul, alur utama, aturan bisnis, kebutuhan, dan acceptance criteria yang bisa diuji.
- **Technical Plan:** stack, arsitektur, skema database, autentikasi/otorisasi, penyimpanan file, dan deployment.
- **UI/UX Guideline:** tema, navigasi, layout, komponen, responsivitas, dan state antarmuka.
- **Dokumen pendukung:** ERD, matriks role-permission, daftar API, test plan, deployment guide, dan ADR dibuat sesuai kebutuhan nyata proyek.

Mulai dengan versi ringkas yang cukup untuk memulai coding. Perbarui dokumen sejalan dengan implementasi dan temuan. Jangan menghabiskan waktu menyusun dokumen yang belum dibutuhkan, menduplikasi informasi, atau menunggu semua dokumen sempurna sebelum mulai membangun.

## 4. Standar Teknologi dan Infrastruktur

### Stack yang dikunci

- **Hosting dan deployment:** Vercel.
- **Database utama:** Neon dengan PostgreSQL.
- **Penyimpanan file:** tentukan sesuai jenis dan pola penggunaan file. Aset statis seperti ikon dapat disimpan bersama aset aplikasi; logo atau file yang perlu diunggah/dikelola saat aplikasi berjalan gunakan object storage yang sesuai (Cloudflare R2 menjadi pilihan default bila cocok). Simpan metadata dan referensi file di database, bukan binary file di tabel database kecuali ada alasan kuat.

### Pemilihan teknologi lainnya

Tentukan teknologi frontend, backend, ORM, validasi, UI component, autentikasi, testing, dan library berdasarkan kebutuhan nyata proyek. Pilih solusi yang stabil, kompatibel dengan Vercel dan Neon, mudah dipelihara, memiliki dokumentasi baik, serta tidak menambah kompleksitas yang tidak dibutuhkan. Jelaskan alasan dan trade-off keputusan utama sebelum mengunci stack. Verifikasi dokumentasi dan versi resmi terbaru ketika keputusan bergantung pada perubahan teknologi atau library.

### Autentikasi dan otorisasi

- Utamakan login menggunakan **username dan password**.
- Gunakan mekanisme autentikasi yang mendukung kebutuhan tersebut dan kompatibel dengan stack proyek.
- Rancang otorisasi berbasis peran/hak akses sesuai kebutuhan; autentikasi saja tidak cukup untuk melindungi data.
- Terapkan penyimpanan password yang aman, validasi sesi, pembatasan akses, dan perlindungan rute/server action/API.
- Jangan mengasumsikan seluruh pengguna memiliki email atau menjadikan login email sebagai metode utama, kecuali kebutuhan proyek mengharuskannya.

## 5. Standar UI/UX

Gunakan tampilan modern, profesional, konsisten, dan berorientasi pada efisiensi kerja.

- Pilih salah satu arah visual sesuai karakter aplikasi: **Navy Prestige** atau **Obsidian Studio**.
- Gunakan font **Inter**.
- Gunakan **small corner radius**; hindari komponen yang terlalu membulat.
- Pastikan hierarki visual, kontras, keterbacaan, navigasi, feedback aksi, empty state, loading state, error state, dan success state dirancang dengan jelas.
- Terapkan desain **mobile-first** dan pastikan seluruh aplikasi mobile-friendly, bukan sekadar mengecilkan tampilan desktop. Uji layout pada ukuran layar kecil dan desktop.
- UI harus terhubung dengan fungsi nyata. Setiap tombol, formulir, menu, navigasi, filter, dan aksi harus memiliki perilaku yang benar.
- Gunakan design token, komponen, dan pola interaksi yang konsisten.

## 6. Standar Struktur dan Kualitas Kode (AI-Friendly)

Susun kode agar mudah dipahami, ditelusuri, diuji, dan dilanjutkan oleh manusia maupun AI:

- Gunakan struktur folder dan pemisahan tanggung jawab yang jelas serta konsisten.
- Pisahkan UI, business logic, akses data, validasi, autentikasi/otorisasi, dan utilitas sesuai kebutuhan proyek.
- Gunakan penamaan file, fungsi, variabel, tipe, dan skema yang deskriptif serta konsisten.
- Utamakan tipe data yang jelas, validasi terpusat, fungsi yang fokus, dan komponen yang dapat digunakan ulang secara wajar.
- Hindari file atau fungsi yang terlalu besar, duplikasi logika, dependensi yang tidak perlu, dan abstraksi prematur.
- Letakkan aturan bisnis penting pada lapisan yang tepat; jangan hanya mengandalkan validasi di sisi UI.
- Berikan komentar pada keputusan atau logika yang tidak mudah dipahami, bukan komentar yang sekadar mengulang kode.
- Sediakan README, contoh konfigurasi environment tanpa secret, instruksi instalasi, migrasi, pengujian, dan deployment.
- Jangan menaruh secret, kredensial, atau data sensitif di repository maupun client-side.

## 7. Urutan Pengerjaan Paling Efektif: Bangun Aplikasi Terlebih Dahulu

Ikuti alur berikut. Sesuaikan detail dengan skala proyek, tetapi pertahankan prinsip bahwa implementasi aplikasi adalah prioritas utama.

1. **Discovery inti:** pahami kebutuhan, pengguna, alur bisnis, aturan kritis, dan batasan. Ajukan hanya pertanyaan yang benar-benar menghalangi keputusan utama.
2. **Rencana awal singkat:** tentukan ruang lingkup, daftar modul awal, dependensi, acceptance criteria inti, stack, dan desain dasar. Buat Master Plan/PRD/Technical Plan versi awal sebagai dokumen hidup.
3. **Fondasi aplikasi:** siapkan repository, environment, Vercel, Neon, skema/migrasi database, autentikasi username-password, otorisasi dasar, struktur kode AI-friendly, layout, dan design system.
4. **Bangun seluruh modul:** implementasikan modul berdasarkan dependensi dan prioritas bisnis. Selesaikan setiap modul secara fungsional—UI, backend/API, validasi, penyimpanan, hak akses, feedback, dan integrasi yang diperlukan.
5. **Integrasikan alur utama:** pastikan semua modul tersambung dan proses bisnis dari awal sampai akhir dapat dijalankan. Lakukan pemeriksaan penting dan terarah selama pengembangan, bukan audit menyeluruh berulang kali.
6. **Pastikan kelengkapan implementasi:** cocokkan semua modul terhadap spesifikasi, PRD, tracker, dan aplikasi. Tidak boleh ada modul wajib yang masih belum dibuat atau parsial sebelum masuk tahap audit menyeluruh.
7. **Audit menyeluruh setelah aplikasi terbentuk:** jalankan audit UI sampai API/database, keamanan, role, perhitungan, laporan, ekspor, mobile, aksesibilitas, dan operasional.
8. **Perbaiki dan uji ulang:** selesaikan temuan berdasarkan risiko, lakukan regression test pada area terkait, dan dokumentasikan bukti serta sisa risiko.
9. **Deployment dan handover:** siapkan deployment Vercel, verifikasi integrasi Neon dan storage, dokumentasikan konfigurasi serta panduan penggunaan, kemudian nyatakan kondisi kesiapan secara jujur.

### Batas antara pemeriksaan saat coding dan audit akhir

- **Selama pembangunan:** lakukan hanya pemeriksaan minimum yang penting untuk mencegah fondasi rusak, seperti build/type check bila tersedia, validasi migrasi, uji login dan akses peran dasar, integritas data, serta smoke test alur kritis yang sedang dibuat.
- **Setelah seluruh modul terbentuk:** lakukan audit mendalam dan pengujian yang lebih luas sesuai Bagian 10.
- Jangan menunda aplikasi jadi demi mengejar test coverage, penyempurnaan teknis, dokumentasi panjang, atau audit detail yang bisa dilakukan setelah implementasi lengkap.
- Jangan menunda atau mengorbankan keamanan fundamental, perlindungan data, autentikasi/otorisasi, maupun pengujian yang mencegah kehilangan/kerusakan data.

### 7.1 Mulai dengan Vertical Slice yang Representatif

Setelah fondasi minimum siap, bangun satu alur bisnis representatif dari ujung ke ujung sebelum memperluas pola implementasi ke seluruh modul. Pilih alur yang cukup penting untuk membuktikan fondasi aplikasi, misalnya login sesuai role, membuat satu data/transaksi inti, menyimpan ke Neon, menampilkan kembali data, dan menerapkan otorisasi server. Sesuaikan contoh dengan domain proyek.

Tujuannya adalah membuktikan lebih awal bahwa frontend, backend/API, database, autentikasi/otorisasi, dan pola UI dapat bekerja bersama. Setelah slice ini berjalan, gunakan pola yang sudah terbukti untuk mempercepat modul lain. Jangan menjadikan vertical slice sebagai alasan untuk menunda pembangunan seluruh modul atau membuat proof-of-concept terpisah yang tidak menjadi bagian aplikasi.

### 7.2 Prioritaskan Fitur P0, P1, dan P2

Kelompokkan kebutuhan berdasarkan dampaknya terhadap kemampuan aplikasi beroperasi:

- **P0 — Critical / Must Have:** wajib tersedia agar alur inti, keamanan dasar, integritas data, dan operasi minimum aplikasi dapat berjalan.
- **P1 — Important:** fitur penting untuk menyelesaikan proses operasional utama dan kebutuhan pengguna yang telah disepakati.
- **P2 — Enhancement / Nice to Have:** penyempurnaan, kenyamanan, otomasi tambahan, atau fitur yang tidak menghalangi operasi inti.

Selesaikan P0 terlebih dahulu, kemudian P1. Kerjakan P2 setelah kebutuhan wajib terpenuhi atau bila biayanya kecil dan tidak menghambat prioritas utama. Prioritas harus mempertimbangkan dependensi, risiko, dampak bisnis, dan keputusan ruang lingkup; jangan memakai label prioritas untuk menghilangkan kebutuhan yang sudah disepakati.

### 7.3 Integrasikan Modul Secara Bertahap

Integrasi dilakukan selama development ketika modul dan dependensinya tersedia, bukan ditunda sampai seluruh modul selesai. Hubungkan modul dengan data dan proses terkait sedini mungkin, lalu lakukan pemeriksaan integrasi penting pada setiap alur yang dibangun. Contohnya, transaksi dihubungkan dengan pelanggan, pembayaran, dan sumber data laporan sesuai dependensi proyek.

Pemeriksaan bertahap ini merupakan bagian dari implementasi dan smoke test minimum, bukan pengganti audit menyeluruh. Audit lintas modul yang mendalam tetap dilakukan setelah seluruh modul dalam ruang lingkup lengkap.

### 7.4 Gunakan Preview Deployment Sejak Awal

Siapkan alur deployment preview Vercel sedini mungkin setelah fondasi aplikasi dan environment minimum tersedia. Gunakan preview untuk memeriksa hasil implementasi pada lingkungan yang mendekati deployment, menguji layout mobile/desktop, serta menemukan masalah build, konfigurasi, dan integrasi lebih awal.

Pisahkan environment dan kredensial development/preview/production dengan benar. Gunakan database atau branch Neon yang sesuai untuk preview agar pengujian tidak merusak data produksi. Jangan menempatkan secret produksi di client-side atau environment yang tidak semestinya. Preview bukan tanda aplikasi siap rilis; production release tetap mengikuti audit akhir dan gerbang release.

### 7.5 Kendalikan Scope dan Perubahan

Selama development, agent dapat menemukan ide atau kebutuhan tambahan. Jangan otomatis memperluas ruang lingkup. Untuk setiap usulan baru:

- Tentukan apakah diperlukan agar alur inti bekerja, merupakan kebutuhan yang sudah disepakati, atau hanya enhancement.
- Catat usulan P2/backlog bila tidak menghambat operasi inti.
- Jangan membiarkan fitur tambahan menggeser penyelesaian P0/P1.
- Catat perubahan kebutuhan, alasan, dampak pada jadwal/dependensi/data/arsitektur, dan keputusan yang diambil.
- Pertahankan keputusan yang sudah disepakati kecuali ada alasan bisnis atau teknis yang kuat.

Jika perubahan berdampak pada aturan bisnis, hak akses, skema data, atau ruang lingkup utama, perbarui PRD, acceptance criteria, dan dokumen terkait sebelum atau bersamaan dengan implementasi.

### 7.6 Gunakan Gerbang Kemajuan Proyek yang Jelas

Pantau proyek melalui empat gerbang berikut dan catat status aktualnya di `PROJECT_STATE.md`:

1. **G1 — Foundation:** repository, environment, database, autentikasi/otorisasi dasar, design system, dan satu vertical slice representatif telah dibangun serta pemeriksaan minimum yang relevan telah dijalankan.
2. **G2 — Implementation Complete:** seluruh modul wajib dalam ruang lingkup sudah lengkap secara implementasi dan terintegrasi; inventarisasi serta acceptance criteria telah diperbarui. Ini belum berarti audit selesai.
3. **G3 — Verification Complete:** audit menyeluruh telah dijalankan, temuan ditangani, pengujian ulang dilakukan, bukti dan area yang belum dapat diuji dicatat, serta sisa risiko dinyatakan.
4. **G4 — Release Ready:** deployment production, konfigurasi environment, koneksi database/storage, migrasi, akses pengguna, dokumentasi operasional, dan kesiapan handover telah diperiksa sesuai ruang lingkup.

Jangan melewati gerbang hanya berdasarkan perkiraan. Catat kriteria yang belum terpenuhi, bukti yang tersedia, pengecualian, dan risiko. Sesuaikan kedalaman pemeriksaan dengan skala aplikasi, tetapi jangan menghapus gerbang keamanan dasar, kelengkapan implementasi, verifikasi, atau kesiapan rilis.

## 8. Inventarisasi Modul dan Gerbang Penyelesaian

Sebelum menyatakan implementasi selesai atau memulai audit menyeluruh, lakukan inventarisasi menyeluruh terhadap seluruh kebutuhan dan kondisi aplikasi. Jangan hanya mengandalkan ingatan atau satu dokumen.

### 8.1 Sumber inventarisasi

Gunakan sumber yang tersedia dan relevan: brief/percakapan, spesifikasi dan aturan bisnis, PRD/Master Plan, tracker/work log, repository dan database, serta aplikasi berjalan/deployment bila tersedia.

Buat inventarisasi awal yang praktis sebelum atau saat implementasi dimulai, kemudian cocokkan dan lengkapi selama pengerjaan. Jangan menghabiskan waktu mengaudit seluruh repository atau aplikasi secara mendalam sebelum membangun, kecuali proyek yang diminta memang berupa audit atau pengembangan lanjutan dari sistem yang sudah berjalan.

Catat perbedaan penting antara spesifikasi, tracker, kode, database, dan aplikasi. Jangan menganggap fitur sudah tersedia hanya karena tercantum di dokumen atau terlihat pada UI.

### 8.2 Daftar modul dan acceptance criteria

Buat daftar modul, submodul, fungsi, dan acceptance criteria inti dalam `MODULE_INVENTORY.md`, `ACCEPTANCE_CRITERIA.md`, atau tracker yang sudah digunakan. Cukup rinci untuk memastikan tidak ada fitur wajib tertinggal, tetapi jangan menjadikan inventarisasi sebagai pekerjaan dokumentasi yang menghambat coding. Lengkapi detailnya seiring modul dibangun.

Gunakan status berikut secara konsisten:

- **Belum dibuat:** belum ada implementasi yang dapat digunakan.
- **Parsial:** sebagian UI, fungsi, alur, atau integrasi sudah ada, tetapi belum memenuhi cakupan implementasi.
- **Sudah diterapkan — belum terverifikasi:** perubahan/kode telah dibuat, tetapi belum didukung pengujian yang memadai.
- **Terverifikasi:** acceptance criteria telah diuji dan didukung bukti yang dapat ditelusuri.
- **Terblokir:** belum dapat diselesaikan karena dependensi atau keputusan yang belum tersedia; catat penyebab dan tindakan berikutnya.
- **Tidak berlaku:** hanya dengan alasan yang jelas dalam ruang lingkup proyek.

Jangan menyamakan “sudah diterapkan” dengan “terverifikasi”. Untuk inventarisasi awal, status boleh diperbarui bertahap. Sebelum audit akhir, seluruh daftar harus direkonsiliasi terhadap spesifikasi dan kondisi aplikasi.

### 8.3 Rencana penyelesaian

Susun urutan implementasi yang praktis berdasarkan dependensi, nilai guna, dan dampak operasional. Prioritaskan fondasi data dan proses yang dibutuhkan modul lain. Pada aplikasi yang memiliki payroll/absensi, pastikan aturan dan sumber data perhitungannya dipahami sejak awal; prioritaskan pula autentikasi, akses peran, laporan, dan proses operasional sesuai dependensinya.

Rencana cukup jelas untuk memulai dan mengarahkan pekerjaan. Hindari perencanaan berlebihan atau menunggu seluruh detail teknis sempurna sebelum implementasi.

### 8.4 Penyelesaian modul secara utuh

Selesaikan setiap modul sebagai satu alur fungsional end-to-end, bukan hanya membuat halaman atau UI. Sesuaikan kebutuhan modul, pastikan komponen berikut tercakup:

- UI lengkap: halaman, navigasi, formulir, tabel, filter, aksi, feedback, loading, empty, success, dan error state.
- API/backend/server action yang diperlukan dengan kontrak input-output dan penanganan error yang jelas.
- Validasi di sisi server sebagai otoritas utama, ditambah validasi UI untuk pengalaman pengguna.
- Penyimpanan dan pengambilan data, relasi, constraint, migrasi, serta integritas database.
- Autentikasi dan otorisasi untuk setiap aksi serta data berdasarkan role/permission dan batas kepemilikan yang berlaku.
- Alur normal, kondisi batas, kegagalan yang relevan, dan pemulihan yang aman tanpa merusak atau menggandakan data.
- Integrasi dan keterkaitan dengan modul lain sesuai proses bisnis.

Selama implementasi, jalankan pemeriksaan terarah yang diperlukan untuk memastikan pekerjaan dapat dilanjutkan. Namun, catat hasilnya sebagai pemeriksaan implementasi, bukan sebagai audit menyeluruh atau bukti bahwa seluruh acceptance criteria telah terverifikasi.

### 8.5 Gerbang sebelum audit menyeluruh

Audit menyeluruh baru dimulai setelah seluruh modul dalam ruang lingkup telah diimplementasikan secara lengkap dan inventarisasi diperbarui. Sebelum melewati gerbang ini:

- Tidak boleh ada modul dalam ruang lingkup yang berstatus **Belum dibuat** atau **Parsial** tanpa pengecualian ruang lingkup yang terdokumentasi dan disetujui.
- Seluruh acceptance criteria harus dipetakan ke implementasi dan statusnya dicatat secara jujur.
- Item yang baru diterapkan tetapi belum diuji tetap berstatus **Sudah diterapkan — belum terverifikasi**.
- Dependensi, item terblokir, asumsi, dan pengecualian harus terlihat jelas; jangan menyembunyikannya dengan mengubah status.

Gerbang ini berarti **kelengkapan implementasi**, bukan klaim bahwa aplikasi sudah lolos audit atau siap produksi.

## 9. Pemeriksaan Minimum Selama Implementasi

Selama membangun aplikasi, lakukan pemeriksaan secukupnya agar masalah mendasar tidak menumpuk. Fokus pada:

- Build/type check atau pemeriksaan dasar yang tersedia ketika perubahan besar dilakukan.
- Migrasi dan koneksi database, constraint penting, serta penyimpanan data yang benar.
- Login, sesi, otorisasi dasar di server/API, dan pembatasan akses data sesuai peran.
- Validasi server untuk input dan aturan bisnis kritis.
- Smoke test alur utama modul yang sedang dibuat, terutama proses yang dapat mengubah atau menghapus data serta perhitungan penting.
- Penanganan error paling penting agar kegagalan tidak menyebabkan kebocoran, data korup, atau duplikasi.

Jangan melakukan audit mendalam setiap kali satu modul selesai. Pengujian lengkap lintas modul, eksplorasi semua skenario gagal, pemeriksaan keamanan terperinci, aksesibilitas menyeluruh, dan regression suite dilakukan pada tahap audit setelah seluruh modul lengkap, sesuai Bagian 10.

Keamanan dasar tidak boleh ditunda: jangan menyimpan password secara plaintext, jangan mengekspos secret, jangan mengandalkan validasi UI saja, dan jangan membiarkan API/server action mengakses data tanpa autentikasi serta otorisasi yang sesuai. Catat secara jujur perubahan yang diterapkan dan pemeriksaan minimum yang benar-benar dijalankan. Jangan mengklaim sudah diaudit atau terverifikasi tanpa bukti.

## 10. Audit Menyeluruh Setelah Semua Modul Lengkap

Setelah gerbang kelengkapan implementasi pada Bagian 8.5 terpenuhi, lakukan audit menyeluruh dari antarmuka pengguna hingga API/backend dan database. Audit harus berbasis acceptance criteria serta bukti, bukan sekadar inspeksi visual atau checklist yang tidak dijalankan.

Cakupan minimal audit:

1. **Kelengkapan dan konsistensi:** semua modul, submodul, halaman, endpoint, proses, dan integrasi sesuai spesifikasi, PRD, tracker, serta aplikasi berjalan.
2. **UI dan UX:** navigasi, tombol, formulir, filter, pencarian, pagination, feedback, loading/empty/error/success state, konsistensi desain, dan perilaku layar kecil.
3. **Alur bisnis:** uji end-to-end untuk alur normal, kondisi batas, input tidak valid, data kosong, konflik, kegagalan dependensi, serta pembatalan/pemulihan yang relevan.
4. **API dan backend:** autentikasi request, validasi server, otorisasi setiap operasi, kontrak data, penanganan error, race condition atau duplikasi yang relevan, dan proteksi terhadap akses langsung yang tidak sah.
5. **Database dan integritas data:** schema, relasi, constraint, migrasi, transaksi, konsistensi perhitungan, query, isolasi data, serta perilaku create/read/update/delete sesuai aturan.
6. **Role dan hak akses:** uji setiap role untuk akses yang diizinkan dan ditolak pada UI, API/server action, dan data; termasuk akses lintas pengguna/tenant bila berlaku.
7. **Privasi dan keamanan:** kebocoran data, paparan secret, akses data sensitif, validasi input, manajemen sesi/password, konfigurasi deployment, dan risiko keamanan relevan lainnya.
8. **Perhitungan dan aturan domain:** hitung ulang contoh kasus normal, batas, pembulatan, perubahan data, dan kondisi khusus. Untuk payroll/absensi, uji aturan sumber waktu/kehadiran, keterlambatan, lembur, izin/cuti, komponen upah, potongan, periode, dan rekap sesuai spesifikasi proyek.
9. **Laporan dan ekspor:** akurasi angka dan agregasi terhadap data sumber, filter/periode, hak akses, format, kelengkapan, serta konsistensi hasil ekspor dengan tampilan.
10. **Operasional dan integrasi:** proses lintas modul, notifikasi atau layanan eksternal, kegagalan integrasi, retry, logging, dan kesiapan operasional yang termasuk ruang lingkup.
11. **Mobile dan aksesibilitas:** responsivitas pada ukuran layar relevan, interaksi sentuh, fokus keyboard, label kontrol, kontras, struktur semantik, dan aksesibilitas dasar.
12. **Kualitas teknis dan deployment:** build, type check, lint, test suite yang tersedia, konfigurasi environment, koneksi Vercel-Neon-storage, migrasi, serta log/error penting.

Gunakan kombinasi pemeriksaan otomatis dan manual yang relevan. Catat area yang tidak dapat diuji, alasan, dampak, dan cara verifikasi alternatif. Jangan menyatakan cakupan audit 100% bila ada area yang belum diuji.

## 11. Perbaikan Temuan, Pengujian Ulang, dan Bukti

Setiap temuan audit harus memiliki ID atau referensi, lokasi/modul, deskripsi, langkah reproduksi, dampak, tingkat prioritas/risiko, bukti, rekomendasi, penanggung jawab bila relevan, dan status.

Alur wajib untuk setiap temuan:

1. Catat temuan dan bukti awal.
2. Analisis akar masalah sejauh bukti memungkinkan.
3. Tentukan rekomendasi dan risiko bila tidak diperbaiki.
4. Terapkan perbaikan dan catat file, schema, endpoint, atau modul yang berubah.
5. Jalankan ulang pengujian yang gagal serta regression test pada area terkait.
6. Simpan bukti hasil pemeriksaan ulang dan ubah status hanya sesuai hasil aktual.

Gunakan status **Open**, **In Progress**, **Fixed — Belum Diverifikasi**, **Verified**, atau **Deferred/Accepted Risk**. Perubahan kode saja hanya dapat mengubah status menjadi **Fixed — Belum Diverifikasi**, bukan **Verified**. Temuan yang ditunda harus memiliki alasan, dampak, mitigasi bila ada, dan pihak/keputusan penerima risiko bila relevan.

Buat `AUDIT_PLAN.md` dan `AUDIT_REPORT.md` atau dokumentasi setara. Laporan akhir harus memuat cakupan, metode, lingkungan/versi yang diuji, acceptance criteria yang diperiksa, hasil dan bukti, temuan, perbaikan, hasil pengujian ulang, area yang tidak dapat diuji, serta sisa risiko. Jangan menghapus riwayat temuan setelah diperbaiki.

## 12. Pencatatan Progres dan Project State

Catat perkembangan proyek secara berkelanjutan agar pekerjaan dapat dilanjutkan tanpa kehilangan konteks. Minimal sediakan:

- **PROJECT_STATE.md:** kondisi aktual proyek, fase saat ini, gerbang yang sudah/belum dilewati, milestone, modul dan statusnya, keputusan terkunci, asumsi, dependensi, blocker, sisa risiko, serta next steps.
- **MODULE_INVENTORY.md:** daftar modul/submodul dan status kelengkapan implementasi serta verifikasinya.
- **ACCEPTANCE_CRITERIA.md:** kriteria penerimaan per modul/fungsi, pemetaan ke implementasi, status uji, dan bukti.
- **WORK_LOG.md:** catatan setiap tahap/sesi, perubahan yang benar-benar diterapkan, file/modul terdampak, pemeriksaan yang dijalankan, hasil aktual, dan pekerjaan berikutnya.
- **ISSUES_AND_FIXES.md:** temuan, dampak/prioritas, akar masalah bila diketahui, rekomendasi, tindakan perbaikan, pemeriksaan ulang, bukti, dan status.
- **AUDIT_PLAN.md / AUDIT_REPORT.md:** rencana, cakupan, hasil audit, bukti, pengecualian, dan risiko tersisa.
- **CHANGELOG.md:** ringkasan perubahan penting per versi atau milestone.

Setelah setiap pekerjaan penting, perbarui status modul dan work log. Sebelum mengakhiri sesi, perbarui `PROJECT_STATE.md` dengan kondisi sebenarnya, termasuk apa yang sudah diterapkan, apa yang sudah diuji, apa yang belum diverifikasi, blocker, dan langkah berikutnya. Jangan mengubah status menjadi terverifikasi tanpa bukti.

## 13. Kriteria Fitur dan Proyek Dianggap Selesai

Sebuah modul dianggap **lengkap secara implementasi** apabila seluruh cakupan dan acceptance criteria-nya sudah memiliki implementasi UI, backend/API, validasi, penyimpanan, hak akses, alur gagal yang relevan, dan integrasi yang diperlukan. Status ini belum berarti modul telah lolos audit.

Sebuah modul dianggap **terverifikasi** hanya apabila acceptance criteria yang relevan telah diuji, hasilnya tercatat, dan bukti dapat ditelusuri.

Proyek dianggap **siap digunakan** apabila seluruh modul dalam ruang lingkup sudah lengkap, audit menyeluruh telah dilakukan, temuan kritis/tinggi telah diperbaiki atau secara eksplisit diterima sebagai risiko, pengujian ulang menunjukkan hasil yang dapat diterima, deployment dan integrasi telah diverifikasi, dokumentasi tersedia, serta `PROJECT_STATE.md` mencerminkan kondisi sebenarnya. Semua sisa risiko dan area yang belum dapat diuji harus dinyatakan secara terbuka.

## 14. Prinsip Prioritas Akhir

Urutan prioritas kerja adalah:

1. Pahami kebutuhan inti dan aturan bisnis yang menentukan bentuk aplikasi.
2. Buat rencana serta inventarisasi modul secukupnya agar implementasi terarah.
3. Bangun fondasi dan **selesaikan seluruh modul aplikasi** beserta alur bisnis yang diperlukan.
4. Jaga keamanan fundamental, autentikasi/otorisasi, validasi server, dan integritas data selama pembangunan; lakukan pengujian penting dengan cakupan minimum yang proporsional.
5. Setelah seluruh modul lengkap, lakukan audit menyeluruh, perbaiki temuan, dan jalankan pengujian ulang.
6. Lakukan penyempurnaan performa, refactoring, aksesibilitas lanjutan, dan detail sekunder sesuai risiko serta kebutuhan.

**Makna yang harus diikuti agent:** ketika pengguna meminta dibuatkan aplikasi, segera bergerak dari discovery inti ke implementasi. Target pertama adalah aplikasi yang terbentuk dan seluruh fitur wajibnya berfungsi. Audit detail bukan penghambat pembangunan; audit detail dilakukan setelah semua modul lengkap. Namun, keamanan fundamental dan pemeriksaan penting yang mencegah kerusakan data tetap diterapkan sejak awal. Dokumentasikan progres, keputusan, asumsi, temuan, perbaikan, bukti pengujian, dan sisa risiko secara akurat.
