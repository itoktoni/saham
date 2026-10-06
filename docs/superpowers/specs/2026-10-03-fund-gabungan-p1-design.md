# Spec: P1 Combine Fundamental + Display Provenance

Tanggal: 2026-10-03 | Status: disetujui user (build mode)
Cakupan: P1 SAJA (combine + tampil; skor TIDAK berubah). P2 wiring skor terpisah.

## 1. Aturan prioritas (fixed)

| Field | Prioritas | Konflik (>25%) |
|---|---|---|
| ROE, EPS, DER, PBV, BVPS | IndoPremier Q → sesaham TTM → Yahoo | Flag + tampil dua-duanya |
| Arus kas OCF/FCF/dividen | Sesaham (tunggal) | — |
| Tren naik/turun/datar | IndoPremier ≥6 titik, else Yahoo | — |
| FV banding | Graham sesaham vs median kita | Selisih >30% → flag |
| Klasifikasi/tema | Sesaham → sektor lama | — |

## 2. `scripts/fetch-fund-gabungan.py` (stdlib)

- `ambil_fund(kode)`: sesaham `/emiten/KODE` (rasio, kas, klasifikasi, sejenis,
  FV Graham, Piotroski) + IndoPremier `fundamental.php?code=K&quarter=5`
  (deret kuartal). Delay 2 dtk, timeout 30, best-effort per emiten.
- Output/emiten: `{nilai:{}, sumber:{}, flag:[], tren:{}, kas:{}, fv_graham,
  klasifikasi:{}, sejenis:[]}`. Tulis `data/fund-gabungan.json` + `diambil`.
- Angka ID ("1,15 T", "39,87%", "—") → parser rupiah/persen (reuse pola scraper tema).

## 3. Server (`app/app-screener.py`)

- `muat_fund(kodes)`: baca cache; bila basi (>30 hari)/absen → fetch via
  `load_mod`, best-effort try/except → `{}`. Tanpa fetch → hasil tetap ok.
- `muat_semua`: `"fund": fund`. Rute `GET /api/fund` (pola tema, baca disk).

## 4. Frontend (`web/screener-praktis.html`)

- `S.fund` (Download + init `/api/fund`, pola tema). `SP.gabung(r, entry)` murni:
  override TAMPILAN (bukan `skor()`).
- Drawer langkah 2: nilai + badge sumber per baris; blok Arus Kas + lampu;
  tren panah; FV Graham vs kita; flag konflik merah.
- Tanpa kolom tabel baru.

## 5. Testing

- Fixture HTML kedua situs → parse tepat. `gabung`: prioritas + flag + fallback.
- Smoke hijau. Manual 1 emiten cocok vs situs. Gagal total → Yahoo-only.

## 6. Non-goals

- Tanpa ubah `skor()`/`aksi`/kalibrasi (P2), tanpa kolom baru, tanpa rebuild exe.
