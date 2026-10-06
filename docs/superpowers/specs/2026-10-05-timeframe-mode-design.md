# Spec: Mode Timeframe (Scalping / Kilat / Mingguan / Bulanan)

Tanggal: 2026-10-05 | Status: disetujui user (pendekatan B) | File diubah: `web/screener-praktis.html`, `tests/_test-praktis.js`

## 1. Latar & keputusan

Skor tunggal 0–100 (`SP.skor`, bobot Nilai 15 / Kualitas 30 / Timing 15 / Aliran 10 / MomRev 30)
dikalibrasi untuk horizon 3 bulan (lift +4,8pp; pada 1 bulan hanya +2,5pp — nyaris acak).
Bukti lapangan: trader pasang posisi pre-market pada label Akumulasi → merah semua,
sementara Markup/Distribusi naik +2%. Akarnya: label Akumulasi deskriptif (20 hari ke
belakang, sideways + vol kering), bukan prediktif intraday; saham yang naik +2%
bervolume otomatis keluar kriteria Akumulasi (simulasi: jadi Markup).

Dropdown horizon lama (`sp_horizon`: >3 bulan / 1–3 bulan / ≤1 bulan) hanya label +
peringatan — tidak mengubah skor/filter/aksi. Spec ini menggantinya dengan 4 mode yang
mengubah perilaku. User memilih pendekatan B (skor + aksi per mode), menolak A (label
saja) dan C (mesin kontrak full).

## 2. Mode & max-hold

| Mode | Max hold | Arti |
|---|---|---|
| Scalping | max 1 day | Wajib keluar hari yang sama |
| Kilat | max 2–3 day | Beli hari ini, jual maks H+3 |
| Mingguan | max 1 week | Pegang s/d 7 hari |
| Bulanan | max 1 month | Skor penuh seperti sekarang |

- Tiap baris tampil chip countdown SISA (`H+n` / `KDL` merah bila lewat max-hold).
- Lewat max-hold → aksi turun paksa menjadi Pantau/Hindari (tidak lagi Beli).
- Mode tersimpan di `localStorage sp_tf`; default Bulanan (perilaku lama).

## 3. Bobot skor & filter per mode (Nilai/Kualitas/Timing/Aliran/MomRev)

| Mode | Bobot | Filter |
|---|---|---|
| Scalping | 0/10/30/30/30 (MOS & fundamental diabaikan) | Likuid ≥ Rp5M, `vol_ratio ≥ 1.0`, fase Distribusi disembunyikan |
| Kilat | 10/20/30/15/25 | Likuid ≥ Rp1M, Distribusi tidak bisa Beli |
| Mingguan | 15/25/20/10/30 | Likuid ≥ Rp500jt |
| Bulanan | 15/30/15/10/30 (rumus sekarang, tak berubah) | Likuid ≥ Rp500jt |

JUJUR: bobot Scalping/Kilat/Mingguan adalah tebakan beralasan TANPA backtest.
Banner kalibrasi wajib menampilkan "belum terkalibrasi" untuk ketiga mode itu sampai
diukur ulang. Satu-satunya angka terkalibrasi adalah Bulanan.

## 4. Aksi & aturan keluar per mode

- Semua mode: fase Distribusi → Hindari (tanpa kecuali).
- Scalping: Beli hanya Markup/Spring + peringatan cut −3% intraday (teks, bukan order).
- Kilat: Beli hanya Markup + ARA-kedua valid; lock ARA H+0 dilarang beli (aturan 2026-10-04).
- Mingguan: aksi standar + Spring/Akumulasi boleh Beli.
- Bulanan: aksi standar sekarang, tak berubah.

## 5. UI

- Segmented control 4 mode di atas tabel utama; menggantikan dropdown `sp_horizon` lama
  di drawer (key lama tetap dibaca sekali untuk migrasi → Bulanan bila `3`).
- Chip SISA max-hold per baris; chip `KDL` merah bila lewat.
- Banner: untuk 3 mode baru tampilkan "bobot belum terkalibrasi — pakai sebagai filter,
  bukan ramalan".

## 6. Testing

`tests/_test-praktis.js` blok baru:
1. Skor Scalping identik untuk dua record yang hanya beda MOS (MOS diabaikan).
2. Distribusi → aksi Hindari di keempat mode.
3. Chip KDL muncul saat umur posisi > max-hold mode aktif.
4. Cek string: HTML memuat `sp_tf` dan 4 label mode.
Manual: ganti mode → skor/aksi/filter berubah; reload persist; KDL muncul.

## 7. Non-goals (YAGNI)

- Tanpa order/trailing-cut otomatis (peringatan teks saja).
- Tanpa backtest ulang / tanpa ubah rumus Bulanan.
- Tanpa ubah `SP.suspen`, bounty, combo, exitLevel (kompatibel, tak tersentuh).
- Tanpa rebuild `.exe` (launcher mode source).

## 8. Self-review

- Placeholder: tidak ada (semua angka & aturan eksplisit).
- Konsistensi: chip KDL + downgrade aksi (§2) selaras dengan aturan aksi (§4); filter
  likuiditas (§3) selaras dengan masalah likuiditas tiny (BLTZ 16M) kemarin.
- Scope: satu file HTML + satu file uji; tidak menyentuh backend/fetcher.
- Ambiguitas: "ARA-kedua valid" didefinisikan di aturan 2026-10-04 (volume ≥50% H+0);
  "cut −3%" adalah peringatan teks.
