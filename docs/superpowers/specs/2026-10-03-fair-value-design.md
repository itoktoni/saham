# Spec: Kolom Fair Value + Rincian Metode di Drawer

Tanggal: 2026-10-03 | Pendekatan: A (kolom + rincian, frontend-only) | Status: disetujui user
File: `web/screener-praktis.html` (satu-satunya file yang diubah)

## 1. Latar & tujuan

Nilai intrinsik (fair value) sudah dihitung `valuasi()` sebagai median 3 metode,
tapi angka mentahnya hanya tampil di drawer dan turunannya (Upside/MOS) di tabel.
Pengguna ingin angka FV terlihat di tabel + tahu pecahan tiap metode pembentuknya
(untuk menilai seberapa solid median tersebut).

## 2. Perubahan `valuasi()` (kompatibel mundur)

- Tiga komponen diberi nama eksplisit: `graham` (eps>0 → eps*(7+g)*7.8/11.4),
  `roepbv` (bvps>0 & roe>0 → bvps*(roe/10)), `growth` (bvps>0 & roe>0 →
  bvps*(1+roe/100)^5). Rumus TIDAK berubah.
- Return tambah `rincian: {graham, roepbv, growth}` (0 bila tak valid) dan
  `nMetode` (1–3, jumlah komponen valid). Field lama tidak berubah.
- Median dihitung dari komponen valid saja, sama seperti sekarang.
- Skor/aksi/bobot Nilai tidak berubah (tetap memakai MOS).

## 3. Kolom tabel "FV"

- Posisi setelah kolom MOS. Isi: `nf(val.intrinsic, 0)`; hijau (`neg`) bila
  intrinsic > harga, merah (`pos`) bila di bawah; 0/kosong → "—".
- Sortable via `get` mengembalikan intrinsic (0 di dasar).
- Ekspor CSV: tambah kolom `fv` di AKHIR baris (append, tidak menggeser kolom lama).

## 4. Rincian drawer (langkah 2, Nilai & MOS)

- Di bawah "Nilai intrinsik (median metode)": 3 baris `FV Graham`,
  `FV ROE-PBV`, `FV Equity growth` (angka dibulatkan, "—" bila tak valid) + baris
  "Median dari {n} metode valid". Prefix "FV" membedakan dari komentar kode.
- Data tanpa fundamental (Scan Pasar kosong) → semua "—", tanpa error.

## 5. Error handling & edge case

- Semua angka via `toNum`/`nf` yang ada; intrinsik 0 → "—" di tabel & drawer.
- Test lama (`MOS positif saat murah`, sebaran fase, aksi) tetap hijau.

## 6. Testing

- `node tests/_test-praktis.js` hijau + cek baru: valuasi sintetik mengembalikan
  3 komponen + median benar; string HTML `t: "FV"`, ketiga label metode.
- Manual: Muat Contoh → kolom FV terisi + drawer pecahan tampil.

## 7. Non-goals (YAGNI)

- Tanpa metode valuasi baru, tanpa ubah rumus/median/bobot, tanpa ubah backend,
  tanpa filter/sort baru selain kolom, tanpa rebuild `.exe` (launcher mode source).
