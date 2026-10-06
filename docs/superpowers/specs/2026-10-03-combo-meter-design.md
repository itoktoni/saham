# Spec: Combo Meter C0–C3 (Sub-proyek 1 dari 4)

Tanggal: 2026-10-03 | Pendekatan: A (kolom + bukti, display-only) | Status: disetujui user
Konsumsi: `S.scope` dari fondasi (sub-proyek 0). Berikutnya: exit-alarm (2), bounty (3).
File: `web/screener-praktis.html` (satu-satunya file yang diubah)

## 1. Latar & keputusan

Lima sumber SahamScope + fase bandar digabung menjadi satu level keyakinan kasar
C0–C3. Display-only: skor/aksi 0–100 TIDAK berubah (kalibrasi aman). UNKNOWN eksplisit
agar tak ada presisi palsu.

## 2. Bukti (fixed, `SP.combo(x, entry)` murni)

Input: record `x` (`fase`) + `entry` scope emiten (`{acc:{top_buyers,series}, insider:[...]}`).
Tanpa entry → `{level: -1 (tampil "—"), bukti: []}`.

- **E1 Streak broker:** broker = `top_buyers[0]`; 5 titik terakhir `series[broker]`;
  YES bila ≥3 titik `nval>0`. Tanpa series/broker → UNKNOWN. Bukti teks:
  `"{BROKER} {n}/5 hari net-buy"`.
- **E2 Insider ≤60 hari:** cari item `action_type=buy` dengan selisih tanggal ≤60 hari
  dari hari ini (banding string ISO `YYYY-MM-DD`, tanpa lib tanggal). YES bila ada;
  teks `"{nama} +{changes_value} ({tgl})"` + jabatan bila `badges` ada, bila tidak
  tambah "(tanpa info jabatan)". Ada data tapi tak ada buy ≤60 hari → NO.
  Tanpa data insider → UNKNOWN.
- **E3 Fase:** YES bila `x.fase` Spring/Akumulasi; NO bila lainnya (selalu diketahui).
- **Breaker:** fase Distribusi ATAU ada `action_type=sell` ≤60 hari → `breaker: true`
  dengan alasan teks.

## 3. Level (fixed)

- Level = jumlah YES (0–3) → label C0–C3.
- C3 wajib E3 YES (tanpa fase → maks C2). Breaker → maks C1.
- UNKNOWN dihitung 0 untuk level, chip tampil "?".

## 4. UI

- Kolom **"Combo"** setelah Likuid: badge C3 hijau (`a-beli`) / C2 biru (`b-spring`-like,
  reuse class badge fase) / C1 kuning (`a-pantau`) / C0 abu (`b-netral`) / "—" mut.
  Tooltip ringkasan 3 bukti. Sortable via level (-1 di dasar).
- Drawer langkah 3, di bawah blok akumulasi: **"Kombo smart-money"** — 3 chip
  (hijau YES / merah NO / abu "?") + baris breaker merah bila aktif +
  catatan "display-only, tidak mengubah skor".
- Tanpa scope (Scan Pasar/impor): kolom "—", drawer blok menampilkan
  "Butuh Download Data (cache SahamScope)."

## 5. Error handling & edge case

- Tanggal insider tak valid/kosong → item dilewati (bukan NO paksa).
- `series` pendek (<5 titik): pakai yang ada; syarat tetap ≥3 positif
  (deret <3 titik → tidak bisa YES → NO bila data ada).
- Semua angka via `toNum`; `S.scope.emiten` absen → "—".

## 6. Testing

- `node tests/_test-praktis.js` hijau + cek baru: sintetik 3-YES → C3;
  breaker sell → C1 + alasan; fase NO → maks C2; tanpa entry → "—";
  string HTML `t: "Combo"`, "Kombo smart-money".
- Manual: Download → kolom + chip drawer benar (cocokkan 1 saham dengan
  `data/sahamscope.json`); Scan Pasar → "—".

## 7. Non-goals (YAGNI)

- Tanpa ubah skor/aksi, tanpa bobot/desimal, tanpa decay timer umur sinyal
  (ditunda ke bounty board bila perlu), tanpa backend, tanpa rebuild `.exe`.
