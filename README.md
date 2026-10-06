# Screener Saham IDX (portable)

Aplikasi desktop sederhana untuk menyaring saham IDX berdasarkan **fase bandar**
(akumulasi → spring → markup → distribusi) + nilai. Screener dulu, klik saham →
langkah demi langkah. Tanpa mengetik perintah.

## Menjalankan (2 cara)

1. **Paling mudah (butuh Python 3.8+):** klik dua kali **`Jalankan Screener.vbs`**.
   Peramban terbuka sendiri. Untuk berhenti: klik dua kali **`Matikan Screener.vbs`**.
2. **Portable tanpa Python:** klik dua kali **`Screener Saham.exe`** (bila disertakan).
3. **Instalasi cepat (opsional):** klik dua kali **`Install.bat`** untuk membuat
   shortcut "Screener Saham" di Desktop + Start Menu. Hapus dengan **`Uninstall.bat`**.

Portable: seluruh folder ini bisa disalin ke flashdisk; jalankan dari mana saja.

## Cara pakai

1. Jalankan aplikasi → peramban terbuka.
2. Klik **Download Data** (daftar pantau, akurat) atau **Scan Seluruh Pasar**
   (seluruh IDX via TradingView, ~845 saham). Data KSEI + harga/fundamental
   diambil otomatis.
3. Pindai tabel; klik satu saham untuk melihat langkah demi langkah
   (keputusan → nilai & MOS → fase & bukti → rencana eksekusi → catatan).

### Pengaturan unduhan

- **Download Data** mengunduh **daftar pantau** saja (default 10 emiten),
  dikonfigurasi di `data/config.json` → `daftar_saham`.
- **Scan Seluruh Pasar** mengunduh **seluruh emiten** IDX (~845, TradingView).
- Ubah daftar pantau & panjang seri KSEI lewat panel **Pengaturan unduhan**
  di aplikasi (atau edit `data/config.json` langsung, lalu muat ulang).

## Sumber data (gratis)

| Data | Sumber |
|---|---|
| Kepemilikan asing/lokal per emiten (bulanan) | KSEI |
| Seluruh pasar: harga, PE/PB/ROE, RSI, SMA, rentang | TradingView scanner |
| Harga & fundamental watchlist (harian) | Yahoo Finance + laporan IDX |

Aliran asing **harian** IDX (GetStockSummary) sedang diblokir Cloudflare dari
jaringan umum, jadi belum bisa otomatis. Proxy gratis: KSEI (bulanan) + TradingView.

## Struktur folder

```
app/       aplikasi server (app-screener.py)
web/       antarmuka (screener-praktis.html; screener-saham-indonesia.html = lanjutan)
scripts/   penarik data (fetch-ksei.py, fetch-data-idx.py)
data/      keluaran & cache (ksei.json, data-idx.csv, pasar.json, cache-*)
docs/      panduan metodologi + PRODUCT.md/DESIGN.md
contoh/    data contoh/ilustrasi
tests/     uji (node tests/_test-praktis.js)
logs/      log aplikasi (screener-app.log)
```

## Uji

```
node tests/_test-praktis.js
```

## Catatan

Bukan nasihat investasi. Fase bandar dihitung dari harga/volume + kepemilikan
bulanan; verifikasi sebelum bertransaksi. Warna: naik = merah, turun = hijau.
