# Spec: Tema Narasi + 5 Metode ID + Panel Smart-Money

Tanggal: 2026-10-03 | Pendekatan: A (penuh) | Status: disetujui user
File: `scripts/fetch-tema.py` (baru), `data/tema.json` + `data/tema-manual.json`,
  `web/screener-praktis.html`. Tidak diubah: backend lain, skor/aksi.

## 1. Latar & keputusan

Alur: narasi tema (oil/AI/data center) → filter metode pola → bandingkan harga kita
vs harga smart money + PNL mereka + upside tersisa. Istilah ID disetujui:
Jelang Breakout, Barang Kering, Kontraksi VCP, Lolos Resistance, Kocokan Terakhir.
Sumber harga SM: asing + broker + insider (yang ada).

## 2. Tema (`fetch-tema.py` + `tema.json`)

- Scraper stdlib: ~10 halaman detail kurasi sesaham (coal, crude-oil, lignite,
  minyak-gas, gold, gold-ore, nickel-ore, nickel-matte, data-center,
  aplikasi-jasa-internet), 1 halaman/2 detik, UA sopan, timeout 30 dtk.
- Parse: baris `/emiten/KODE` + kolom Harga Wajar (format ID "1,15 T"/"450,16 M"/"—").
- `data/tema.json`: `{diambil, tema: [{nama, deskripsi, sumber:[slug], emiten:[...], wajar:{KODE:angka}}]}`,
  cache 30 hari. `data/tema-manual.json` (tidak ditimpa scraper):
  `{tambahan: {TEMA:[KODE]}, deskripsi: {TEMA: teks}}` — gabung saat serve.
- Serve: Python baca kedua file saat Download (tanpa fetch bila cache segar) →
  `S.tema`. Gagal/absen → dropdown hidden.
- Etika: cache lama + pamit ke pemilik situs disarankan.

## 3. Metode (5 preset, `SP.matchMetode`)

- Nilai: "Jelang Breakout" (pos 0,55–0,75, vol 1,0–1,5, closeabove, bukan spring),
  "Barang Kering" (= sideways lama), "Kontraksi VCP" (= lama),
  "Lolos Resistance" (pos ≥0,75, vol ≥1,3, closeabove),
  "Kocokan Terakhir" (= s_spring). Nilai lama tak dikenal → "Semua".
- Tooltip EN + syarat angka per opsi. Dropdown Tema AND Metode AND Fase AND search.

## 4. Panel smart-money (`SP.smartMoney`, drawer langkah 3)

- Input: record + entry scope + tema wajar. Output:
  `{baris: [{sumber, avg, pnl}], terbaik: {sumber, avg}, jarakPct, upsidePct}`.
- Baris: Asing (avg/harga/PNL via data ada), Broker top (avg bavg top-1 + PNL;
  butuh scope v2), Insider (harga+tanggal terakhir). Absen → "—".
- Vonis: "Harga kita {x}% di {bawah/atas} avg {sumber}" +
  "Mereka sudah +{x}% · upside tersisa {y}% ke FV" (upside = intrinsic).
  Pembanding utama = avg valid terendah.
- Aturan "jangan terlalu atas": bila harga > +10% di atas avg termurah →
  vonis merah "Terlalu jauh di atas harga smart money — rawan distribusi,
  jangan chase; tunggu pullback ke dekat avg mereka." Bila fase Distribusi
  pula → teks ditambah "Fase distribusi terdeteksi."
  Ambang fixed +10%.
- Semua angka via `toNum`/`nf`; harga/avg ≤0 → baris "—".

## 5. UI

- Toolbar: dropdown Tema + baris narasi (deskripsi + "(n saham, m di atas FV sesaham)").
- Drawer: blok "Smart money vs harga kita" (3 baris + vonis).
- Tanpa kolom tabel baru (YAGNI).

## 6. Testing

- Smoke: `SP.smartMoney` sintetik (harga<avg → bawah; PNL/upside benar);
  `matchMetode` 2 aturan baru; string HTML Tema/metode/panel.
- Manual: tema contoh → filter+narasi; Download → drawer cocok vs KSEI/scope.

## 7. Non-goals (YAGNI)

- Tanpa auto-narasi berita, tanpa ubah rumus fase/skor, tanpa kolom baru,
  tanpa rebuild `.exe`.
