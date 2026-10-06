# Spec: Banding Kompetitor Se-Industri di Drawer

Tanggal: 2026-10-03 | Status: disetujui user (build mode)
File: `web/screener-praktis.html` (satu-satunya file yang diubah)

## 1. Latar & keputusan

Tiap saham sudah punya `klasifikasi.industri` + daftar `sejenis` dari sesaham
(di `S.fund.emiten`). Drawer menampilkan daftar centang sejenis + tombol
Banding; data peer yang belum termuat diambil segar via `GET /api/stock`.

## 2. Sumber kompetitor (fixed)

- Peer = record di `S.data` (selain diri sendiri) yang kodenya ada di
  `sejenis[kode]` ATAU `klasifikasi.industri[0]`-nya sama.
- Urutan: sesuai urutan `sejenis`, sisanya (satu industri tapi tak disebut
  sejenis) di belakang; maksimal 7 peer (8 baris dengan diri sendiri).
- Tanpa entry fund untuk kode ybs → blok menampilkan fallback
  "Belum ada data pembanding — klik Download Data." (pola fallback existing).

## 3. Fungsi murni `SP.pesaing(kode, data, fundMap)`

- Output: `{industri, peers[record], med:{per,pbv,roe,mos}, rankPbv, rankRoe, n, vonis}`.
- `med` = median nilai finite per kolom (PER negatif ikut dihitung apa adanya;
  kolom kosong → "—").
- `rankPbv` = peringkat PBV menaik (1 = termurah), `rankRoe` = peringkat ROE
  menurun (1 = tertinggi), `n` = ukuran grup (diri + peer). Nilai tak valid
  tidak ikut peringkat (rank = null → vonis pakai kata "tak terbandingkan").
- `vonis` (tanpa klaim beli/jual, bahasa sederhana):
  "Di antara {n} {industri} yang termuat ({kode-kode}), {kode} PBV-nya
  {termurah|urutan ke-X dari n|termahal}, ROE {tertinggi|urutan ke-X|terendah}."
  Industri kosong → pakai frasa "saham sejenis".

## 4. UI — interaktif (revisi disetujui user)

- Blok **"Banding kompetitor"** (drawer langkah 2, setelah fundBox):
  baris mapping "Industri: **{industri}**" + daftar centang seluruh `sejenis`
  (tanda "(termuat)" bila kodenya ada di tabel) + tombol **Banding**.
- Klik Banding → untuk tiap yang dicentang: pakai record tabel bila ada,
  bila tidak fetch `GET /api/stock?kode=X` (segar, paralel, best-effort per
  kode; yang gagal dilewati + disebut di catatan) → render tabel
  Kode|Harga|PER|PBV|ROE|FV|MOS|Fase|Skor (baris diri ditebalkan) +
  baris median + `vonis` dalam `.note` ke div hasil.
- Pilihan centang tersimpan per saham (`S._bandingPick`) selama sesi;
  hasil selalu diambil ulang (segar) tiap tekan Banding.
- Tanpa centang → teks "Pilih dulu siapa yang dibandingkan."

## 5. Testing

- Smoke `SP.pesaing` sintetik: peer matching via sejenis + industri,
  cap 7, median benar, rank benar, tanpa fund → fallback shape.
- String HTML: "Banding kompetitor", "SP.pesaing", "btnBanding", "saingPick".
- Manual: Download → drawer BBNI → centang BBCA/BMRI → Banding → tabel
  segar + median + vonis; tanpa fund → fallback.

## 6. Non-goals (YAGNI)

- Tanpa scrape halaman industri per klik, tanpa ubah skor/fase/aturan,
  tanpa kolom baru, tanpa rebuild `.exe`.
