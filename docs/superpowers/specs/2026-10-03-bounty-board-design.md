# Spec: Bounty Board — Misi Malam Ini (Sub-proyek 3 dari 4)

Tanggal: 2026-10-03 | Pendekatan: A (interaktif + arsip) | Status: disetujui user
Konsumsi: `S.scope` (pulse + series + insider), `S.data` (fase, nilai_harian).
File: `web/screener-praktis.html` (satu-satunya file yang diubah)

## 1. Latar & keputusan

Ritual EOD <3 menit: tepat 3 kandidat/quest per malam dari pulse T-1 + streak +
insider, dengan keputusan Terima/Lewat yang tercatat (anti-overtrading).
Tanpa data scope → tidak ada kartu (bukan skor 0).

## 2. Skoring (`SP.bounty`, murni, fixed)

- Input: array record `build()` + `S.scope`. Syarat masuk: ada entry scope
  DAN `nilai_harian ≥ Rp5.000.000.000`.
- Bobot 0–100: pulse 50 (kode di `pulse.top_net_buy` → 50, else 0);
  streak 30 (`n/5 × 30`, n = titik net-buy top-1 buyer 5 terakhir);
  insider 20 (buy ≤60 hari, banding string ISO, tanggal tak valid dilewati).
- Output 3 teratas: `{kode, skor, rinci: {pulse, streak, insider}, jejak:
  {broker, hit, insiderNama, likuid}}`. Seri → streak lebih baru dulu
  (implisit via urutan stabil: bobot sama → kode abjad? TENTUKAN: seri =
  prioritas streak count, lalu abjad kode — deterministik).
- Tanpa entry scope untuk semua → array kosong.

## 3. Aksi + arsip (`localStorage sp_bounty`)

- Struktur: `{YYYY-MM-DD: {KODE: {status: "dipantau"|"lewat", alasan}}}`
  alasan wajib bila lewat: "Terlalu jauh" | "Sepi" | "Tunggu besok".
- Terima → baris tabel disorot (class) + penghitung "dipantau (n)" di panel.
- Arsip: bila ada kunci tanggal < hari ini, tampilkan tanggal terbaru lampau
  read-only (1 hari ke belakang saja).
- Rebuild/Download ulang hari sama: keputusan dicocokkan ulang per kode
  (tidak hilang).

## 4. UI (`details.adv#questPanel` setelah panel sektoral)

- Judul "Misi Malam Ini" + badge "data {tgl pulse}" (honesty).
- Kartu: ticker + skor + breakdown "50+18+20" + jejak
  ("OD 4/5 · insider ERWIN · likuid") + tombol Terima/Lewat + klik kartu drawer.
- Tanpa scope/pulse: teks "Butuh Download Data (SahamScope)."

## 5. Error handling & edge case

- `pulse.top_net_buy` kosong → semua skor tanpa komponen pulse (bukan error).
- Keputusan untuk kode yang hilang dari watchlist → arsip tetap tampil
  (riwayat), papan aktif mengabaikan.
- localStorage gagal → papan tetap render, keputusan sesi saja (try/catch).

## 6. Testing

- Smoke `SP.bounty` sintetik: bobot 50/30/20 tepat; illiquid tersingkir;
  tepat 3 teratas; seri deterministik; tanpa scope → [].
- String HTML: `questPanel`, "Misi Malam Ini", `sp_bounty`.
- Manual: Download → 3 kartu + breakdown → Terima/Lewat → reload awet →
  (simulasi tanggal) arsip tampil.

## 7. Non-goals (YAGNI)

- Tanpa check-in pagi, tanpa skip-ledger mingguan, tanpa capital-sizer,
  tanpa arsip >1 hari, tanpa ubah skor/aksi, tanpa backend.
