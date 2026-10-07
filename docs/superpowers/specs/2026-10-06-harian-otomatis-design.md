# Spec: Data Harian Otomatis Seluruh Pasar (IDX Stock Summary)

Tanggal: 2026-10-06
Status: disetujui user (scope: seluruh pasar, tampil di screening)

## 1. Latar
- Otomatis harian seluruh pasar saat ini hanya `data/live-scan.json` (TradingView: close, volume, `nilai_harian = close*volume`, tanpa `freq`).
- `freq/value/volume` resmi per emiten hanya tersedia sebagai CSV training manual
  (`data/training/training-YYYY-MM-DD.csv`: `tanggal,tipe,kode,harga,naik_pct,nilai,volume,freq`).
- IDX menyediakan Stock Summary per emiten per hari (High/Low/Close/Volume/Value/Frequency),
  pola endpoint sama dengan `GetIndexSummary` yang sudah dipakai di
  `scripts/fetch-data-idx.py:631` (`hitung_likuiditas`, baris 720-775).
- Tes cepat tanpa sesi Cloudflare menghasilkan HTTP 403; kode sudah punya pola
  pemanasan sesi Cloudflare (`scripts/fetch-data-idx.py:1283-1305`) yang wajib dipakai ulang.

## 2. Tujuan
- Fetch otomatis `Volume, Value, Frequency (+ High/Low/Close)` per emiten untuk seluruh
  pasar (~900 emiten) per hari perdagangan.
- Tampilkan kolom `Freq` dan `Value` di web screener (mode pasar).
- Format selaras dengan CSV training agar bisa menggantikan input manual.

## 3. Non-tujuan
- Tidak mengubah logika skor/valuasi yang sudah ada.
- Tidak menyimpan intraday/orderbook.
- Tidak memaksa fetch pasar penuh tiap scan; fetch harian bersifat batch harian.

## 4. Arsitektur
- Satu fungsi baru di `scripts/fetch-data-idx.py`: `fetch_stock_summary(tanggal)`
  sejajar `hitung_likuiditas()`, memakai sesi HTTP yang sama (pemanasan + retry).
- Satu output baru: `data/harian-YYYYMMDD.json`:
  `{dibuat, tanggal, jumlah, sumber, saham: [{kode, high, low, close, volume, value, freq}]}`
- Satu pembaca di `app/app-screener.py`: endpoint `/api/harian?tanggal=YYYYMMDD`
  (default: file terbaru) yang di-merge ke hasil `/api/scan` berdasarkan `kode`.
- Dua kolom baru di `web/screener-praktis.html` tabel mode pasar: `Freq`, `Value (Rp)`.
  Format suffix `B/M/K` mengikuti konvensi training CSV.

## 5. Data flow
1. `python scripts/fetch-data-idx.py --harian [YYYYMMDD]` (default: hari perdagangan terakhir).
2. Pemanasan Cloudflare → request `GetStockSummary?date=` → paginasi seluruh emiten.
3. Tulis `data/harian-YYYYMMDD.json` secara atomik (tulis tmp + rename).
4. App serve via `/api/harian`; web fetch lalu merge by `kode` saat render mode pasar.
5. Weekend/libur: tidak ada data → tulis file dengan `jumlah: 0` + `catatan`, jangan crash.

## 6. Error handling
- 403/timeout: retry maks 3x, tiap retry diawali pemanasan ulang sesi.
- Gagal total: fungsi kembalikan `None`, CLI log jujur, file lain (Yahoo/TradingView)
  tetap diproses; tidak boleh memblokir data yang sudah ada (pola sama seperti
  `likuiditas: null` di `data/pasar.json` saat ini).
- Validasi minimal: tiap baris harus punya `kode, close, volume, value, freq`;
  baris tanpa kode dibuang; angka dinormalisasi via `num()`/`clean()` yang sudah ada.

## 7. Testing
- Verifikasi 1 hari: bandingkan `data/harian-<tgl>.json` vs halaman Stock Summary IDX
  manual untuk 3 emiten (contoh acuan: GOTO, IATA, PPRI pada 2026-10-06).
- Pastikan `value/volume/freq` cocok (toleransi format suffix).
- Pastikan web merge tidak merusak mode watchlist/impor yang sudah ada.
- Pastikan tidak ada regresi pada `pasar.json` dan `live-scan.json`.

## 8. Kriteria sukses
- Perintah `--harian` menghasilkan file JSON valid untuk 1 hari perdagangan.
- Kolom `Freq` dan `Value` tampil di screener mode pasar.
- Kegagalan network tercatat di log dan tidak merusak file lama.

## 9. Risiko
- Endpoint/parameter IDX berubah atau Cloudflare memperketat → mitigasi: gunakan ulang
  kelas sesi yang sama, simpan respons mentah untuk diagnosis, dokumentasikan parameter
  aktual yang terbukti jalan.
- Fetch ~900 emiten lambat → mitigasi: satu request paginasi server-side (bukan per kode),
  delay sopan, cache per tanggal.
