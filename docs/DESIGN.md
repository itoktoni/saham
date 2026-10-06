# DESIGN.md — Screener Praktis Saham IDX

Sistem visual untuk `screener-praktis.html`. Mode: **Operate**. Dibuat 2026-10-01.

## Karakter

Tenang, padat, cepat dibaca. Registrasi "alat kerja finansial": teks kecil rapi, angka tabular, warna dipakai hanya untuk makna. Tanpa gradien dekoratif, tanpa animasi berlebih.

## Token warna

```
--bg:#f5f7f9   latar halaman
--panel:#fff   kartu/tabel
--panel2:#fafbfc  header tabel & sebagainya
--ink:#161a20  teks utama
--ink2:#3d444d teks sekunder
--muted:#5b6470  teks redup (>=4.5:1 di latar putih & abu)
--line:#e3e7ec / --line2:#eef1f4  garis
--accent:#1f5fd0 / --accent2:#eaf1fd / --accentink:#123a86  aksi & fokus
--up:#c62828 (naik/positif)   --down:#17795e (turun/negatif)
```

### Warna semantik fase bandar

```
Akumulasi  #17795e  hijau  — bandar mengumpulkan
Spring     #1f5fd0  biru   — kocokan/shakeout (trigger)
Markup     #c62828  merah  — harga diangkat
Distribusi #b26a00  oranye — bandar menjual
Netral     #8a8f98  abu    — belum jelas
```

## Tipografi

Skala nyata (body 12px → h3 15px → h2 18px → h1 21px; lompatan ≥1.25×, mencegah hierarki datar).
Font: stack sistem (`-apple-system, Segoe UI, Roboto, Arial`). Angka: `font-variant-numeric: tabular-nums` pada kolom numerik.

## Bentuk & ruang

- Radius: `--r:12px` kartu; 9–10px kontrol; 99px pil/badge.
- Bayangan: `--sh` halus tunggal.
- Grid halaman: satu kolom, full-width (`main` tanpa `max-width`) agar tabel memakai lebar layar.

## Komponen

- **Header lengket**: judul + 3 tombol (Impor Data, Muat Contoh, Ekspor CSV).
- **Strip makro**: satu baris, tersembunyi bila `pasar.json` belum dimuat.
- **Bar alert**: perubahan fase sejak kunjungan terakhir (localStorage `sp_fase`).
- **Tabel kandidat**: header bisa diklik untuk urut; kolom `Kode · Nama · Harga · Fase · Asing% · ΔAsing 1m · Rata2 Asing · Upside · MOS% · Skor · Aksi`.
- **Badge fase** & **badge aksi** (`Beli` hijau / `Pantau` kuning / `Hindari` merah).
- **Bar skor** inline (lebar = skor/100).
- **Drawer** (bukan halaman baru): 5 langkah — Keputusan → Nilai & MOS → Fase & Bukti → Rencana Eksekusi (TP/SL/lot) → Catatan.
- **Lipatan "Lanjutan"**: cara ambil data, arti fase, rumus skor, keterbatasan.

## Aksesibilitas

- Heading berurut (h1 → h2 sr-only "Hasil screening" → h3).
- Kontras teks ≥ 4.5:1 (muted dipergelap ke `#5b6470`).
- `.sr-only` untuk judul tersembunyi.
- `@media print` menyembunyikan kontrol.

## Batasan

Satu file, tanpa CDN/gambar eksternal. Responsif turun ke satu kolom < 640px. Preferensi sistem (dark mode) belum diimplementasikan — kandidat pekerjaan berikutnya.
