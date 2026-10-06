# Spec: Likuiditas + Bar Akumulasi Harian

Tanggal: 2026-10-03 | Pendekatan: A (backend kirim bars + frontend render) | Status: disetujui user
File: `scripts/fetch-data-idx.py`, `web/screener-praktis.html`
Tidak diubah: `app/app-screener.py` (field mengalir otomatis), skor/aksi/fase, ekspor CSV.

Keputusan: broker afiliasi DIBATALKAN (tidak ada sumber gratis; IDX diblokir).
Scope: label likuiditas + 30 bar akumulasi harian di drawer.

## 1. Likuiditas (frontend saja)

- Ambang fixed: `nilai_harian >= Rp5.000.000.000` → Likuid, di bawahnya → Sepi.
  Sama dengan preseden `minNilai 5e9` di `screener-saham-indonesia.html`.
- Kolom tabel baru "Likuid" setelah kolom Aksi: badge hijau `Likuid` / abu `Sepi`,
  tooltip = nilai transaksi harian terformat ("Rp12,4M/hari").
- Drawer: baris "Nilai transaksi harian" di area bukti (langkah 3).
- `nilai_harian` sudah ada di kedua mode; kosong/nol → tampil "—" (bukan Sepi).

## 2. Data bar harian (backend)

- `build_record()` di `scripts/fetch-data-idx.py` menambah field `bars_30`:
  30 pasangan `[tutup, volume]` terakhir dari chart Yahoo (tutup dibulatkan ke
  integer via `clean`, volume dibulatkan ke lot). Bila chart < 30 hari, kirim
  seadanya (boleh < 30, tidak di-padding).
- `bars_30` ikut JSON `saham` lewat `ambil_emiten()` tanpa perubahan app
  (verifikasi: tidak ada strip field generik di sana selain `_catatan`).
- CSV impor manual / mode Scan Pasar: field absen → frontend fallback.

## 3. Heuristik akumulasi (frontend, `SP.barAkumulasi`)

- Fungsi murni di modul `SP`, diekspor: input `bars_30`, output array
  `{h: 0–100 (volume relatif terhadap max), c: "H"|"M"|"A"}`.
- Aturan fixed: dasar = rata-rata volume deret; hari ke-i (i≥1):
  hijau (H, serapan) bila `tutup[i] > tutup[i-1]` dan `vol[i] >= rata-rata`;
  merah (M, sebaran) bila `tutup[i] < tutup[i-1]` dan `vol[i] >= rata-rata`;
  abu (A) untuk ostatnya. Hari pertama selalu abu (tanpa pembanding).
- Jujur: ini heuristik harga×volume, BUKAN data broker. Label di UI:
  "heuristik harga×volume — bukan data broker".

## 4. Render drawer

- Langkah 3 (Fase & Bukti) tambah blok "Akumulasi 30 hari": 30 bar vertikal
  (lebar ~8px, tinggi = `h%`, warna via class inline: hijau `#17795e`,
  merah `#c62828`, abu `#c9cfd6`) + legenda "hijau = hari serapan ·
  merah = hari sebaran · abu = sepi" + catatan heuristik.
- Warna di blok ini arthya khusus akumulasi (bukan konvensi naik-turun);
  legenda eksplisit mencegah salah baca.
- Fallback (tanpa `bars_30`): teks "Bar harian hanya tersedia dari
  Download Data (butuh riwayat Yahoo)."

## 5. Error handling & edge case

- `bars_30` kosong/singkat: render seadanya; array kosong → fallback text.
- Volume nol semua: tinggi bar 0, tidak ada pembagian nol (guard max>0).
- Nilai transaksi nol: badge "—", bukan Sepi.

## 6. Testing

- `node tests/_test-praktis.js` hijau + cek baru: sintetik naik+vol tinggi
  → H; turun+vol tinggi → M; datar → A; string HTML `barAkumulasi`/`bars_30`.
- Manual: Download Data → drawer tampil 30 bar; Scan Pasar → fallback tampil;
  kolom Likuid terisi di kedua mode.

## 7. Non-goals (YAGNI)

- Tanpa data broker (dibatalkan), tanpa ambang likuiditas tunable, tanpa ubah
  `app-screener.py`, tanpa kolom filter likuiditas, tanpa rebuild `.exe`
  (launcher mode source).
