# Spec: Download Detail Sementara dari Scan (Checklist)

Tanggal: 2026-10-03 | Pendekatan: centang + checklist + POST /api/detail | Status: disetujui user
File: `app/app-screener.py`, `web/screener-praktis.html`
Prinsip: SEMENTARA — tidak menulis config.json / daftar-saham.txt / cache watchlist.

## 1. Latar & keputusan

Hasil Scan (dangkal) harus bisa naik kelas ke data detail tanpa menghancurkan
watchlist tersimpan. Mekanisme: centang baris → checklist otomatis 3 syarat →
tombol Download Detail → tampil sementara + tombol Kembali.

## 2. UI (hanya mode Scan)

- Kolom centang pertama di tabel, header-nya "centang semua"; HANYA dirender
  bila `S.mode === "pasar"`. State `S.picked = {}` (kode → true), reset tiap
  rebuild dari sumber baru.
- Bar checklist `#cekBar` di atas tabel (hidden bila 0 tercentang): per kode
  3 lampu dari data baris: Likuid (`nilai_harian ≥ 5M`), Bukan Distribusi
  (`fase !== "Distribusi"`), MOS terhitung (`val.intrinsic > 0`).
  Format: `BBCA ✅✅✅ · ANTM ✅❌✅`.
- Tombol `#btnDetail` "Download Detail (N)" di toolbar (hidden bila 0 picked
  atau bukan mode pasar). Banner `#detailBar` kuning saat `S.modeDetail`:
  "Detail sementara N saham — watchlist tersimpan tidak berubah" + tombol
  `#btnKembali` → klik Download normal (watchlist tersimpan).
- Mode dilacak: `S.mode = "pasar"|"watchlist"` diset di handler Scan/Download/
  Contoh/Impor (Contoh/Impor = "watchlist"? Bukan keduanya — set "impor":
  centang hidden kecuali "pasar"). Sederhana: centang + tombol hanya bila
  `S.mode === "pasar"`.

## 3. Backend `POST /api/detail`

- Body JSON `{kodes: [...]}` → `bersih_kode`, maks 30 (lebih → 400),
  kosong → 400. GET ke rute ini → 404 (hanya POST).
- Ambil: `ambil_emiten(kodes)` (Yahoo+IDX, reuse; gagal per emiten dilewati
  seperti biasa) + `ambil_scope(kodes)` (best-effort try/except → `{}`) +
  KSEI dari cache/server yang ada (tanpa fetch ulang bila cache hit;
  bila miss → `ambil_ksei()` penuh seperti Scan).
- Respons: `{ok, jumlah, ksei, saham, scope, tema, dibuat}` (tema dari
  `muat_tema()` yang ada). Gagal total (saham kosong) → 502.
- DILARANG menulis: config.json, daftar-saham.txt, cache "emiten"/"ksei"/"scope"
  (pakai pembuat langsung, bukan `cache_ambil`, agar cache watchlist utuh).

## 4. Frontend handler

- `btnDetail`: POST kodes tercentang → `S._csvRows`, `ingestKsei`, `S.scope`,
  `S.tema`, `S.picked = {}`, `S.modeDetail = true`, `S.mode = "detail"`,
  `rebuild()` (+ render cekBar hidden), toast jumlah.
- `btnKembali`: `S.modeDetail = false` → panggil ulang handler Download normal.
- Drawer/kolom/fitur lain tak berubah (scope ikut → kombo/level/smBox jalan).

## 5. Error handling & edge case

- Server mati/API Yahoo gagal total → toast error, tabel tidak berubah.
- Kode gagal per emiten → dilewati + toast menyebut yang gagal (dari log `gagal`)?
  Minimal: toast "N dari M berhasil".
- Double-klik tombol saat fetch → disabled selama fetch (pola tombol yang ada).

## 6. Testing

- Python/HTTP: POST body salah → 400; `{kodes:["BBCA","TLKM"]}` → 2 baris +
  scope 2 kunci; `config.json` + `daftar-saham.txt` byte-identik sebelum/sesudah;
  GET /api/detail → 404.
- Node: string tombol/banner/kolom/`/api/detail`; smoke hijau.
- Manual: Scan → centang 3 (satu illiquid) → checklist benar → Detail →
  drawer penuh → Kembali → watchlist lama.

## 7. Non-goals (YAGNI)

- Tanpa ubah watchlist tersimpan, tanpa filter/sort checklist, tanpa batas
  checklist memblokir (hanya informasi), tanpa rebuild `.exe`.
