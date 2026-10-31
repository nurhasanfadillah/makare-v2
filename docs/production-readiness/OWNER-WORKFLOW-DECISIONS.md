# Keputusan Pemilik: Alur implementasi MAKARE

Tanggal dicatat: 2026-10-31

## Urutan pekerjaan

1. Lengkapi seluruh modul dan integrasikan langsung ke database/backend/UI sesuai spesifikasi.
2. Gunakan database lokal atau staging dengan data sintetis dan status non-production yang dapat dibuktikan selama implementasi. Jangan menunggu fase audit untuk pertama kali menyambungkan modul ke database.
3. Pemeriksaan ringan per modul diperbolehkan untuk menjaga hasil implementasi, tetapi tidak menggantikan acceptance akhir.
4. Setelah seluruh modul selesai, bekukan scope lalu lakukan audit menyeluruh per modul dan lintas modul. Perbaiki temuan, ulangi acceptance terkait, dan dokumentasikan bukti serta risiko.

## Batas keamanan database

- Jangan menjalankan test, migration, atau operasi tulis terhadap database production.
- Pemilik mengonfirmasi pada 2026-10-31 bahwa data Neon saat ini adalah data uji/coba dan boleh dipakai untuk implementasi serta acceptance.
- Pemeriksaan sebelum migration menemukan tabel berisi akun uji, satu karyawan uji, absensi, lembur, kasbon, catatan, dan audit; tidak ada payroll period. Migration `001` dan `002` diterapkan tanpa menghapus data yang ada.
- URL Neon yang sama dipakai untuk runtime dan migration sementara sesuai arahan pemilik. Gunakan endpoint pooler untuk keduanya selama keputusan ini berlaku; migration `001` dan `002` telah berhasil diaplikasikan. Endpoint direct tetap direkomendasikan oleh Neon untuk workflow migration berikutnya.
- API kini berjalan pada Vercel dan health check live menunjukkan database Neon tersambung. Aplikasi web dipublikasikan di Vercel; deployment dan acceptance lanjutan dicatat di `EXECUTION-STATE.md`.
- Konfigurasi lokal yang disiapkan: `compose.dev.yaml` mengikat PostgreSQL hanya ke loopback pada port 55432; `backend/.env.local.example` memilih database tersebut dan hanya mengizinkan SSL disable untuk `APP_ENV=development`.
- Docker lokal tidak tersedia, tetapi tidak menghalangi acceptance karena URL Neon uji telah disetujui pemilik dan koneksinya telah berhasil diverifikasi.
- Setelah Docker tersedia, perintah lokal (PowerShell) yang disiapkan: `Copy-Item backend/.env.local.example backend/.env.local`; `docker compose -f compose.dev.yaml up -d --wait`; lalu dari folder `backend`, set `$env:MAKARE_ENV_FILE='.env.local'` dan jalankan API. Jangan menyalin/menimpa `backend/.env` yang sudah ada.
- Jangan menyalin kredensial `.env` cloud ke konfigurasi lokal atau menampilkan nilainya.

## Instruksi untuk sesi berikutnya

Perlakukan keputusan ini sebagai arahan tetap pemilik: database-first saat menyelesaikan implementasi modul, gunakan Neon URL yang tersedia sementara, selesaikan semua modul dan alur bisnis dahulu, kemudian audit per modul. Pemilik memberi otorisasi untuk memakai target Neon saat ini sebagai data uji; catat bukti migrasi, test, dan data yang dibuat/dibersihkan.

## Baseline aturan bisnis yang didelegasikan

Pada 2026-10-31 pemilik memberi otoritas penuh untuk menyelesaikan aplikasi, alur bisnis, dan integrasi lokal/Neon/Vercel/GitHub tanpa banyak pertanyaan. Agar DEC-01–10 tidak menahan implementasi, gunakan baseline berikut sesuai spesifikasi dan klarifikasi pemilik yang sudah ada. Catat sebagai baseline fase pertama; jangan mengklaim baseline ini telah mendapat persetujuan bisnis terpisah.

- Satu perusahaan per deployment; mata uang Rupiah/IDR. Multi-tenant, cabang, pajak/iuran khusus, integrasi pihak ketiga, dan mata uang lain di luar fase pertama.
- Operator hanya membuat status absensi untuk hari WIB berjalan. Perubahan, koreksi, atau tanggal historis hanya administrator dengan alasan dan audit.
- Toleransi absensi tepat 30 menit bersifat inklusif. Untuk keterlambatan di atas toleransi, jam pertama adalah blok waktu jadwal 60 menit pertama; overlap istirahat dikurangkan dari interval eligible yang tersisa.
- Pengakuan durasi menggunakan `floor((eligible_minutes + late_tolerance_minutes) / 60) * 60` setelah perhitungan overlap istirahat dan aturan blok jam pertama; formula sama untuk regular/lembur. Ini menggunakan setting toleransi yang sudah ada.
- Tarif reguler/lembur melekat pada karyawan dan nilainya disnapshot saat tutup buku; komponen manual dihitung terpisah dari jam hadir.
- Satu administrator boleh mengesahkan koreksi payroll dengan alasan wajib, idempotency, audit, dan adjustment terpisah; snapshot tutup buku asal tidak berubah. Persetujuan administrator kedua dan slip versi baru tidak menjadi bagian fase pertama.
- Kode karyawan monotonik unik dan tidak digunakan ulang; satu jadwal global, satu sesi reguler dan satu sesi lembur yang saling eksklusif; sesi yang tertinggal ditangani administrator melalui koreksi tercatat; penghapusan absensi/payroll final tidak tersedia.
- Data personal/attendance/payroll disimpan sebagai histori sampai administrator melakukan pengelolaan sesuai kebijakan perusahaan. Tidak ada purge otomatis; retensi yang diwajibkan hukum masih menjadi risiko yang harus dinilai sebelum produksi umum.
- Dari konflik visual 110°/135°, gunakan sudut 135° yang disebut spesifikasi lengkap dan pertahankan token lainnya.


## Konfirmasi data uji dan pembersihan

Pada 2026-10-31 pemilik menegaskan bahwa seluruh data yang ada adalah data uji/coba. Setelah acceptance live, seluruh baris bisnis, payroll uji, akun sementara, departemen bernama TEST, serta audit uji dihapus dalam transaksi Neon; dua akun aplikasi, empat departemen, pengaturan awal, dan migration ledger dipertahankan. Pengaturan direset ke default aman dan semua sesi dicabut.
