# PRODUCT.md — Screener Praktis Saham IDX

Konteks produk untuk pekerjaan desain AI di proyek ini. Dibuat 2026-10-01.

## Satu kalimat

Satu file HTML offline yang menyaring saham IDX berdasarkan **fase bandar** (akumulasi → spring → markup → distribusi) + nilai, lalu satu klik membuka langkah demi langkah.

## Pengguna & momen

- Investor ritel Indonesia, modal kecil, bekerja **setelah pasar tutup (EOD)**.
- Suasana hati: ingin cepat tahu "apa yang layak dibeli / dihindari hari ini" tanpa berlembar-lembar teori.
- Konteks: buka file HTML langsung (offline), tempel data hasil skrip Python.

## Tugas utama & definisi sukses

- **Tugas:** memindai satu tabel kandidat, mengurutkan berdasarkan satu skor, dan membaca aksi (Beli / Pantau / Hindari).
- **Sukses:** dalam < 1 menit pengguna tahu 3–5 saham untuk dipantau, dan tahu mana yang sedang didistribusi. Klik baris = detail lengkap tanpa pindah halaman.

## Prinsip produk (jangan dilanggar)

1. **Screener dulu, detail belakangan.** Tabel kandidat adalah halaman; 7 langkah metodologi hanya muncul saat baris diklik.
2. **Satu file, offline, tanpa CDN.** Tanpa dependensi eksternal.
3. **Kejujuran data.** Sumber gratis: KSEI (kepemilikan bulanan) + Yahoo (harga/volume). Sumber yang tak bisa diakses diberi tahu apa adanya, tidak dipalsukan.
4. **Warna:** naik = merah, turun = hijau (konvensi pasar Indonesia).
5. **Bukan nasihat investasi.** Setiap keluaran disertai peringatan.

## Sumber data

| Data | Sumber | Frekuensi | Status |
|---|---|---|---|
| Kepemilikan asing/lokal per emiten + rata2 harga beli asing | KSEI (seri 24 bulan) | bulanan | gratis, otomatis (`fetch-ksei.py`) |
| Harga, volume, fundamental (watchlist) | Yahoo Finance + laporan IDX | harian | `fetch-data-idx.py` |
| Seluruh pasar (harga, PE/PB/ROE, RSI, SMA, rentang, puncak 52m) | **TradingView scanner** `scanner.tradingview.com/indonesia/scan` | harian | gratis, tanpa kunci, ~845 saham sekali panggil |
| Regime pasar (IHSG, BI Rate) | IDX + Yahoo + SEKI | harian | `fetch-data-idx.py --pasar` (opsional) |
| Aliran asing harian & broker summary | IDX `GetStockSummary`/`GetBrokerSummary` | harian | **terblokir Cloudflare dari mesin ini**; tidak ada sumber gratis pengganti |

**Rata2 beli asing** = rata-rata harga pembelian asing 24 bulan terakhir (harga akhir bulan KSEI × kenaikan lembar asing). **Upside** = potensi kenaikan ke nilai wajar. **Posisi asing** = untung/rugi asing = harga kini ÷ rata2 beli − 1.

## Mode

**Operate** — alat kerja. Bukan landing page, bukan dokumen.

## Cara pakai (yang diinginkan)

1. **Klik dua kali `Screener Saham.exe`** (portable, tanpa Python) — atau `Jalankan Screener.vbs` (butuh Python). Aplikasi menyala, peramban terbuka sendiri. `Install.bat` membuat shortcut Desktop/Start Menu.
2. Di aplikasi, klik **Download Data** (watchlist, akurat) atau **Scan Seluruh Pasar** (seluruh IDX via TradingView, ~845 saham). Kepemilikan KSEI + harga/fundamental diambil otomatis.
3. Pindai tabel, klik baris untuk langkah demi langkah.
4. Berhenti: `Matikan Screener.vbs` atau tutup proses `Screener Saham.exe`.

## Struktur folder

```
app/       app-screener.py (server lokal)
web/       screener-praktis.html (utama), screener-saham-indonesia.html (lanjutan)
scripts/   fetch-ksei.py, fetch-data-idx.py
data/      keluaran & cache
docs/      panduan + PRODUCT.md/DESIGN.md
contoh/    data contoh
tests/     _test-praktis.js
logs/      screener-app.log
```

## Peta artefak

- `Screener Saham.exe` — aplikasi portable (PyInstaller), tanpa perlu Python.
- `app/app-screener.py` — server lokal (stdlib) + endpoint `/api/download` & `/api/scan`.
- `Jalankan Screener.vbs` / `Matikan Screener.vbs` / `Install.bat` / `Uninstall.bat`.
- `web/screener-praktis.html` — UI screener-first (artefak utama).
- `scripts/fetch-ksei.py`, `scripts/fetch-data-idx.py` — penarik data (cadangan/manual).
- `tests/_test-praktis.js` — uji smoke mesin screener.

## Anti-goals

- Bukan tool multi-halaman dengan nav 7 langkah di depan.
- Bukan dashboard penuh grafik/matriks di halaman utama.
- Tidak meminta input manual untuk hal yang bisa diotomatiskan (mis. kuadran makro).
