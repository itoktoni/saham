# Spec: Tambah ke Watchlist dari Scan (Checklist) — REVISI

Tanggal: 2026-10-03 (revisi; menggantikan "Download Detail Sementara") | Status: disetujui user
File: `web/screener-praktis.html` (satu-satunya file yang diubah)
Prinsip: dicentang = masuk daftar kode watchlist (APPEND, bukan replace, bukan sementara).

## 1. Latar & keputusan (revisi)

Desain "tampilan sementara + POST /api/detail" DIBATALKAN atas koreksi user:
kode yang dicentang harus masuk ke watchlist tersimpan (append). Alur:
Scan → centang → checklist otomatis → tombol Tambah → Download otomatis.

## 2. UI (hanya mode Scan/pasar)

- Kolom centang pertama di tabel + header "centang semua"; HANYA bila
  `S.mode === "pasar"`. State `S.picked = {}`.
- Bar `#cekBar`: per kode 3 lampu (Likuid ≥Rp5M · Bukan Distribusi ·
  MOS terhitung) ✅/❌ + legenda. Gagal syarat boleh tetap ditambah.
- Tombol `#btnTambah` "Tambah ke Watchlist (N)" di toolbar (hidden bila
  0 picked/bukan pasar). Klik → GET `/api/config` → gabung (union, urutan lama
  dipertahankan, duplikat dibuang) → POST `/api/config` → otomatis klik
  Download → toast "N kode ditambahkan, mengunduh detail…".
- Mode: `S.mode` = watchlist/pasar/impor (tanpa mode "detail", tanpa banner
  kembali). `daftar_saham` + `bulan_ksei` lama dipertahankan saat POST
  (bulan dibaca dari config yang baru di-GET).

## 3. Backend: tidak ada perubahan

Reuse `GET/POST /api/config` yang sudah ada. Tidak ada endpoint baru.

## 4. Error handling & edge case

- Config berubah di tengah (race): single-user lokal, GET-merge-POST cukup.
- POST gagal → toast error, tabel tidak berubah.
- Double-klik → disabled selama proses (pola tombol yang ada).

## 5. Testing

- Node: string tombol/cekBar/kolom; smoke hijau.
- Manual: Scan → centang 3 → cekBar benar → Tambah → config.json bertambah
  3 kode (urutan lama utuh) → Download otomatis jalan → drawer penuh.

## 6. Non-goals (YAGNI)

- Tanpa endpoint baru, tanpa replace watchlist, tanpa filter/sort checklist,
  tanpa rebuild `.exe`.
