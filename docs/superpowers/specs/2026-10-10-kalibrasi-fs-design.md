# Spec: Kalibrasi Minimal Skor FS (P2 Kualitas + dedup DER di P5)

Tanggal: 2026-10-10. Status: disetujui user (Seksi 1 + 2). Pendekatan A.

## Masalah

Kasus sehat pun Kualitas cuma ~20/30. Akar: skala `ROE/25` terlalu keras
(ROE 15% yang bagus hanya dapat 60% poin ROE), dan DER≥2 dihukum dua kali
(P2 nol poin + P5 minus 4). Terbukti via run langsung `fundSkor()`:
kasus sehat → `{valuasi:0, kualitas:20.4, ...}` (valuasi 0 karena data uji
tanpa EPS/ekuitas, bukan bug).

Bukan bug: `dividen d < 0` benar (dividen dibayar = outflow kas negatif,
lih. `scripts/fetch-fund-gabungan.py:114-115`).

## Perubahan (hanya 2 baris logika, struktur tetap)

1. `web/screener-praktis.html:969`: `clamp(roe / 25, 0, 1)` →
   `clamp(roe / 20, 0, 1)`. ROE 20% = poin penuh; ROE 15% naik 60%→75%.
   Multiplier `×0,24` tetap (maks qRaw 100 → 24 + 4 kas + 2 margin = pas 30).
2. `web/screener-praktis.html:1010`: hapus pengurang
   `if (derN >= 2) { p5 -= 4; ... }`. DER tetap dihukum sekali di P2.
   Catatan teks DER dipertahankan tanpa potongan skor (transparan).

Efek terukur: kasus sehat +~1,2 di Kualitas; kasus DER≥2 naik +4 di AntiTrap.

## Dibekukan (tidak diubah)

P1, P3, P4, bobot 30+30+10+10+20, Tier A≥75/B 60–74/C<60, ambang display
mentah (≥21/≥14/≥7 Bagus dst.), helper `fsSkala10/fsLabel/fsPilar/fsVerdict`.

## Verifikasi (saat implementasi, pola RED-dulu)

- Tambah kasus di `tests/test-fs-display.js`: ROE 15% → Kualitas naik vs
  baseline; DER≥2 → `p.trap` tak lagi minus 4, catatan DER tetap ada.
- Wajib hijau: `node tests/_test-praktis.js` (terutama cek `fs: sehat
  total>=75 tier A`), `test-rk.py`, `test-makro.py`, `test-cash-quality.py`.
- 4 gagal pra-eksis di `_test-praktis.js` (umur fase, kontrak, TF segmented,
  ekspor BOM) di luar cakupan; tidak boleh tambah gagal baru.
