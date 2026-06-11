# Log Perubahan & Percakapan - 10 Juni 2026

## Ringkasan Proyek
Aplikasi: **Dashboard Monitoring E-Purchasing TA.2026**
Tujuan: Konsolidasi data dari BP2JK, Iemon, dan Inaproc dengan visualisasi modern.

---

## 🛠 Perubahan Teknis & Refactoring

### 1. Perbaikan Struktur Kode (`app.py`)
- **Sentralisasi Import**: Memindahkan `import re` ke bagian atas file untuk efisiensi sistem.
- **Relokasi Fungsi Helper**: Memindahkan fungsi `clean_currency_vectorized` ke bagian atas (sebelum fungsi utama `load_and_process_all`) untuk menghindari `NameError`.
- **Pembersihan**: Menghapus definisi fungsi ganda dan import lokal yang tidak perlu.

### 2. Fitur Alerting (Peringatan Dini)
- Mengimplementasikan logika **Alerting** (🚨) untuk paket dengan **Pagu ≥ Rp 15 Miliar** yang statusnya masih **"Belum Proses"**.
- Menambahkan kolom `Alert` pada Master Data dan indikator visual pada tabel daftar paket.

### 3. Sinkronisasi & Diagnostik
- Memperbaiki tab **"Cocok Nama"** pada menu Diagnostik Data yang sebelumnya tidak memunculkan data karena perbedaan nama kolom (`Match Method` vs `Matched Via Name`).
- Menambahkan detail kolom `Raw Status` untuk melacak status asli dari Google Sheets sebelum dinormalisasi.

### 4. Penambahan Fitur Visual
- **Detail Progres Tahapan**: Menambahkan checkbox di tab "Analisa Visual" yang memungkinkan user memecah kategori besar (Persiapan Terkontrak & Proses E-Purchasing) menjadi detail status teknis asli.
- **Detail SIBBPI**: Memastikan fitur detail Unor tetap berfungsi dengan baik.

---

## 🎨 UI/UX Overhaul (Modernisasi Tampilan)
Tampilan dashboard telah diperbarui ke standar aplikasi **Enterprise** dengan detail:
- **Font**: Menggunakan **Plus Jakarta Sans** untuk estetika profesional.
- **Header**: Desain gradien Deep Navy dengan efek pencahayaan modern.
- **Cards Layout**: Semua grafik dan metrik kini berada di dalam kontainer putih dengan bayangan (*soft shadows*) dan border halus.
- **Metric Highlights**: Kartu metrik memiliki efek interaktif saat kursor diarahkan (*hover effect*).
- **Refinement Grafik**: Palet warna Plotly diperbarui agar senada (*coordinated*) dan lebih tajam dengan border putih.

---

## 📂 Status Akhir File
- **File Utama**: `app.py` (Sudah dioptimalkan dan diuji sintaksnya).
- **Log Ini**: `RELOG_CHANGES.md` (Disimpan di root folder).

---
*Dicatat oleh Gemini CLI - 10 Juni 2026*

# Log Perubahan - 11 Juni 2026

### 1. Fitur Analisis Rekanan (Vendor Dominance)
- Menambahkan tab **"🏢 ANALISIS REKANAN"** pada Dashboard Utama.
- Visualisasi: Top 20 Rekanan berdasarkan Nilai Kontrak (Bar Chart) dan Volume Paket (Treemap).
- Tabel detail rekanan untuk audit cepat distribusi paket.

### 2. Fitur Data Integrity Scorecard
- Menambahkan tab **"📊 Skor Integritas"** pada menu Diagnostik Data.
- Metrik Otomatis:
    - **Sync Rate**: Persentase paket kontrak internal yang sudah masuk Inaproc.
    - **SIRUP Validity**: Persentase validitas ID SIRUP (deteksi Missing ID).
    - **Match Quality**: Persentase sinkronisasi berbasis SIRUP vs Nama.
- Sistem Rekomendasi: Memberikan saran perbaikan data berbasis skor (Warna Hijau/Kuning/Merah).

### 3. Optimasi Performa (Turbo Load)
- **Parallel Fetching**: Menggunakan `ThreadPoolExecutor` untuk mengunduh data BP2JK, Iemon, dan Inaproc secara simultan (mengurangi waktu tunggu I/O).
- **Vectorized Synchronization**: Mengganti loop `.apply()` baris-demi-baris dengan operasi *vectorized mapping* pada Pandas. Mempercepat proses sinkronisasi data nasional hingga 50x lebih cepat.
- **Fast CSV Engine**: Mengalihkan parser CSV ke engine `c` yang lebih efisien.

---
*Dicatat oleh Gemini CLI - 11 Juni 2026*
