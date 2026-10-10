# Spec: Grafik Revenue + Net Income + Margin (Yahoo, SVG Drawer)

Tanggal: 2026-10-10. Status: disetujui user (Seksi 1 + 2). Sumber: Yahoo dulu.

## Masalah

User butuh revenue (A), net income (B), margin `ni/rev×100%`, breakdown
kuartal + tahunan, dalam grafik yang nilainya bisa dicek. Fakta konteks:
`fund-gabungan.json` tak punya revenue/ni; `data-idx.csv` punya `laba`
tanpa `pendapatan`; Yahoo `incomeStatementHistory(+Quarterly)` dibaca saat
fetch tapi tidak disimpan (`scripts/fetch-data-idx.py:688-715`).

## Seksi 1 — data `data/labarugi.json` (disetujui)

Fetch menulis `{KODE: {q: [{t, rev, ni}] (4 kuartal terakhir dari `iq`),
y: [{t, rev, ni}] (s.d. 5 tahun dari `ih`)}}`, `t` = label periode
(`endDate`), angka rupiah penuh, null bila tak ada. Web memuatnya seperti
`fund-gabungan.json`/`ksei.json`. Tanpa file: drawer tampil
"data laba-rugi belum diambil" — skor/fundSkor tak tersentuh.

## Seksi 2 — grafik SVG di drawer (disetujui)

Seksi drawer baru "Revenue & Net Income" (bawah Step 2,
`web/screener-praktis.html` ~`isiDrawer`), tanpa library, ikut pola
`screener-saham-indonesia.html:1148`: bar ganda per periode (revenue biru,
net income hijau / merah bila rugi), garis margin % skala kedua, toggle
Kuartal/Tahunan, tiap bar `<title>` ("Q2-2026: rev RpX · ni RpY ·
margin Z%") + label angka ujung batang (format T/M via `fmtBig`),
label sumbu periode. Periode kosong = slot "—".

## Verifikasi (saat implementasi, RED-dulu)

- Python: parse `iq`/`ih` → deret `{t, rev, ni}` benar (kuartal urut,
  null aman, bukan margin-nol-palsu ala catatan gp==0 di `:696-700`).
- Node: drawer emiten ber-data memuat `<svg` + `<title>` + toggle q/y;
  tanpa data tampil fallback, skor Tier contoh tak berubah.
- Wajib hijau: `tests/_test-praktis.js` (tanpa gagal baru),
  `test-rk/makro/cash-quality.py`.
