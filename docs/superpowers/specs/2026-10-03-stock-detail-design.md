# Spec: Detail On-Demand per Klik (`GET /api/stock`)

Tanggal: 2026-10-03 | Status: disetujui user (build mode)
File: `app/app-screener.py`, `web/screener-praktis.html`
Prinsip: klik = laporan segar; loading jujur (indeterminasi, tanpa checklist palsu).

## 1. Endpoint `GET /api/stock?kode=X`

- Validasi: 1 kode via `bersih_kode`; kosong/tak valid → 400.
- Ambil berurutan, tiap sumber best-effort try/except + log:
  1. Yahoo chart+fundamental via `ambil_emiten([kode])` — GAGAL TOTAL → 502
     (tanpa harga tak ada laporan).
  2. KSEI slice dari cache memori/disk (tanpa fetch baru; bulanan).
  3. Scope 1 emiten (SahamScope broker+insider; gagal → `{}`).
  4. Avg IndoPremier: DB SQLite dulu; absen → fetch 1 req + simpan; gagal → tanpa avg.
  5. Fund gabungan: cache 30 hari; absen → fetch; gagal → tanpa fund.
- rakit record via `fd.build_record` + pengayaan yang sama dengan `ambil_emiten`
  (high_52, ret20) — REUSE fungsi, tanpa duplikasi logika.
- Respons: `{ok, diambil, saham, k, scopeEntry, fundEntry, wajar}`.
  `wajar` = FV Sesaham dari tema bila ada.
- Tanpa menulis cache watchlist/config; cache disk scope/fund boleh ter-refresh
  (konsisten perilaku Download).

## 2. Drawer

- Klik → drawer buka instan: judul + bar loading indeterminasi (CSS) +
  teks "Mengambil laporan segar…".
- Respons tiba → render 5 langkah penuh (fungsi render existing, direfaktor
  terima record) + badge "diambil HH:MM" + tombol "Muat ulang" (fetch lagi).
- Gagal total → pesan error + "Coba lagi" (tanpa menutup drawer).
- Tabel utama TIDAK berubah (data tabel tetap dari Download/Scan).

## 3. Testing

- HTTP: tanpa kode → 400; `?kode=!!!` → 400; BBCA → 200 + semua kunci.
- Node: string loading/badge/muat-ulang; smoke hijau.
- Manual: klik → ≤~15 dtk laporan penuh; offline → error + coba lagi.

## 4. Non-goals

- Tanpa streaming progres palsu, tanpa ubah skor/fase/aturan, tanpa kolom baru,
  tanpa rebuild `.exe`.
