# Spec: Pilihan Metode Screening (Sideways, Contraction, Spring, Breakout)

Tanggal: 2026-10-03 | Pendekatan: A (frontend-only filter) | Status: disetujui user
File target: `web/screener-praktis.html` (satu-satunya file yang diubah)

## 1. Latar & tujuan

Screener saat ini memfilter berdasarkan Fase Bandar (Akumulasi/Spring/Markup/Distribusi/Netral)
via chips. Pengguna meminta pilihan metode screening tambahan: Sideways, Contraction pattern,
plus Spring dan Breakout agar strategi swing terwakilkan sebagai preset satu klik.

Sukses: pengguna memilih metode dari dropdown, tabel tersaring dalam <1 detik, dikombinasikan
dengan filter fase + search yang sudah ada, tanpa mengubah skor/aksi terkalibrasi.

Prinsip produk yang dijaga: screener-first, satu file offline tanpa CDN, kejujuran data,
bukan nasihat investasi.

## 2. Keputusan yang sudah disetujui

- 4 preset: Sideways Dry-Out, Contraction/VCP (pendekatan), Spring/Shakeout, Breakout Markup.
- UI: satu `<select>` dropdown di toolbar (bukan chips tambahan, bukan panel parameter).
- Threshold: fixed bawaan (tanpa slider tune user).
- Pendekatan A: filter tampilan murni di JS, tanpa ubah Python/backend/skor.

## 3. Arsitektur & komponen

Hanya `web/screener-praktis.html`:

1. `SP.METODE` — daftar nama preset (konstanta).
2. `SP.matchMetode(x, nama)` — fungsi murni: input satu baris hasil `build()` (punya
   `r`, `k`, `fase`, `pos`), output boolean. Diisolasi agar jalur B (skor backend akurat)
   kelak tinggal mengganti isi fungsi tanpa menyentuh UI.
3. State `S.metode` (default `"Semua"`) + persist `localStorage sp_metode`.
4. Elemen `<select id="metode" class="mini-sel">` di `.toolbar`, sebelum search.
   Opsi Contraction berlabel `Contraction (VCP ≈)` + `title` penjelasan keterbatasan pasar.
5. `render()` — tambah satu tahap filter AND setelah filter fase dan sebelum/sesudah search:
   `if (S.metode !== "Semua") d = d.filter(x => SP.matchMetode(x, S.metode))`.
6. Event `onchange` → set `S.metode`, simpan localStorage, `render()`.

Tidak diubah: `detectFase`, `valuasi`, `skor`, `aksi`, `build`, kolom tabel, ekspor CSV
(ekspor tetap seluruh `S.data`), drawer, kontrak, horizon banner.

## 4. Data flow

`S._csvRows + S.ksei` → `SP.build()` → `S.data` (dengan `fase`, `pos`, `r.s_*`, `k.dksei_*`)
→ filter fase → filter metode (`matchMetode`) → filter search `q` → sort → render tabel.
Dropdown tidak memicu fetch ulang (`/api/download` maupun `/api/scan`).

## 5. Definisi rule fixed (satu-satunya logika baru)

Menggunakan field yang sudah dihitung `hitung_swing()` (watchlist) dan `ambil_tv()` (pasar):
definisi `s_sideways` (=1 bila lebar20 <12% dan posisi <40%) dipakai ulang apa adanya.

- Sideways Dry-Out: `s_sideways==1 AND s_vol_ratio < 1.0 AND s_spring==0`.
- Contraction/VCP pendekatan: `s_sideways==0 AND s_closeabove==1 AND s_spring==0
  AND s_vol_ratio < 1.1 AND pos in [0.25, 0.70]`.
- Spring/Shakeout: `s_spring==1`.
- Breakout Markup: `pos >= 0.50 AND s_vol_ratio >= 1.1 AND s_closeabove==1`.

Semua akses angka via `SP.toNum()` agar CSV lama/kosong tidak menghasilkan NaN.

## 6. Error handling & edge case

- Scan Pasar (TradingView) hanya punya High.1M/Low.1M tanpa riwayat multi-minggu, sehingga
  Contraction di sana murni pendekatan. Diatasi dengan label `≈` + tooltip, bukan blokir fitur.
- Field hilang (impor manual tak lengkap): default falsy → baris tidak lolos filter metode,
  tabel menampilkan pesan kosong yang sudah ada. Tidak ada throw.
- Kombinasi Fase AND Metode AND search bisa menghasilkan nol baris — perilaku yang
  diharapkan; pengguna mengembalikan dropdown ke `Semua Metode`. Tanpa reset otomatis.
- `localStorage` gagal (mode privat): dibungkus try/catch mengikuti pola `sp_horizon`/`sp_kontrak`.

## 7. Testing

- `node tests/_test-praktis.js` tetap hijau (tidak ada perubahan API mesin).
- Manual: Muat Contoh → pilih tiap metode → verifikasi kandidat muncul/hilang sesuai rule;
  uji kombinasi Fase=Akumulasi + Sideways; uji search + metode; uji reload (pilihan awet);
  uji Scan Pasar (tidak error, label ≈ tampil).

## 8. Non-goals (YAGNI)

- Tanpa slider/threshold editable, tanpa kolom tabel baru, tanpa perubahan bobot skor,
  tanpa perubahan backend Python, tanpa rebuild `.exe`, tanpa ubah ekspor CSV.

## 9. Langkah implementasi berikutnya (untuk writing-plans)

1. Tambah `<select>` + CSS reuse di toolbar.
2. Tambah `METODE` + `matchMetode` di modul `SP`.
3. Integrasi `S.metode` + `render()` + persist + event.
4. Uji smoke + manual sesuai Bagian 7.
