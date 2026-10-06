# Spec: Exit-Liquidity Alarm (Sub-proyek 2 dari 4)

Tanggal: 2026-10-03 | Pendekatan: A (level + premium + bargain, warning-only) | Status: disetujui user
Konsumsi: `S.scope` fondasi + ekstensi titik series. Berikutnya: bounty board (3).
File: `scripts/fetch-sahamscope.py`, `web/screener-praktis.html`
Tidak diubah: `app/app-screener.py` (format terus generik), skor/aksi/kontrak.

## 1. Latar & keputusan

Peringatan (bukan blokir): user yang beli jauh di atas harga jual rata-rata broker
distributor adalah exit liquidity yang direncanakan. Ambang simetris ±3%.
Sisi hijau (bargain) sebagai invers. Tanpa kolom tabel baru.

## 2. Ekstensi cache (fondasi v2)

- `ringkas_acc`: titik series menjadi `[nval, cum, bavg, savg]`; `bavg`/`savg`
  boleh null (API null) — hanya `nval`/`cum` yang di-`or 0`-kan.
- Cache tambah `"v": 2`. Frontend: `S.scope.v !== 2` → drawer menampilkan
  "Cache scope lama — klik Download Data untuk refresh level broker."
- Ukuran tetap KB-an untuk watchlist; TTL 24 jam dan perilaku gagal tak berubah.

## 3. Matematika level (`SP.exitLevel`, murni, fixed)

- Input: record `x` (harga, fase) + `entry` scope. Output:
  `{tipe: "alarm"|"bargain"|null, premium, level, broker: [kode], teks}`.
- Alarm: 3 seller terbesar `top_sellers` → per broker rata-rata `savg` dari ≤20
  titik terakhir yang non-null → level = rata-rata level broker-broker valid
  (butuh ≥2 valid, bila tidak → null "tak cukup data").
  premium% = (harga−level)/level×100. Alarm bila premium ≥ +3% DAN fase
  Distribusi/Markup DAN jumlah nval 20 titik ketiga seller < 0.
- Bargain: 3 buyer terbesar → rata-rata `bavg`; bila harga ≤ level×0.97
  (≥3% di bawah) → tipe bargain. Alarm dan bargain mutually exclusive
  (cek alarm dulu).
- Semua angka via `toNum`; harga/level ≤0 → null.

## 4. UI (drawer langkah 3, bawah blok kombo)

- Alarm (merah, `.warn`): "Harga {h} berada {p}% di atas rata-rata jual
  {OD, AK} ({l}). Risiko jadi exit liquidity."
- Bargain (hijau, `.note`): "Harga {h} berada {p}% di bawah rata-rata beli
  {broker} ({l})."
- Netral/buta: abu "tak cukup data savg broker" ATAU pesan refresh cache bila v≠2.
- Selalu sebut broker + level (bukti) + catatan "indikasi — kode broker
  campuran banyak klien, bukan vonis".

## 5. Error handling & edge case

- Cache v1 (tanpa avg): pesan refresh, bukan alarm palsu, bukan crash.
- Titik null semua / <2 broker valid → null.
- Tanpa entry scope → blok kombo existing sudah menangani ("butuh Download");
  blok level ikut menampilkan pesan yang sama.

## 6. Testing

- Python: `ringkas_acc` fixture bertitik lengkap → titik 4-elemen, null lestari.
- Node: sintetik premium +4%/Distribusi → alarm + broker disebut; +1% → null;
  tanpa savg → null; bargain −4% → hijau; cache v1 → pesan refresh (via entry
  tanpa avg); string HTML "Level broker".
- Manual: Download ulang → drawer BBCA dkk blok level tampil; (opsional)
  cache lama → pesan refresh.

## 7. Non-goals (YAGNI)

- Tanpa blokir/override kontrak, tanpa kolom tabel, tanpa churn-adjustment
  scalper (ditunda; label kejujuran mencakup risikonya), tanpa ubah TTL/fallback.
