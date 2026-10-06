# Spec: Info Sektoral — Sektor Rame + Narasi Otomatis

Tanggal: 2026-10-03 | Pendekatan: A (frontend-only agregasi) | Status: disetujui user
File target: `web/screener-praktis.html` (satu-satunya file yang diubah)

## 1. Latar & tujuan

Pengguna ingin tahu sektor mana yang sedang ramai (rotasi sektoral) plus narasi
pendek, misal terkait data center atau oil. Aplikasi offline tanpa sumber berita,
sehingga narasi hanya boleh deskriptif dari angka (top sektor + pendorong + breadth)
— tidak boleh mengklaim sebab ("oil naik", "isu data center").

Sukses: setelah Download/Scan/Muat Contoh, strip makro menyebut sektor terkuat dan
panel sektoral menampilkan peringkat semua sektor + 1 kalimat narasi + pendorong.

Keputusan yang disetujui: narasi auto dari angka, tampil di strip makro + panel
sektoral, metrik return 1 bulan + breadth, dihitung dari data yang sedang dimuat.

## 2. Arsitektur & komponen (hanya `web/screener-praktis.html`)

1. `SP.agregatSektor(data)` — fungsi murni baru di modul `SP`, diekspor di `return`.
   Input: array record hasil `SP.build()` (`{kode, sektor, r}`). Output: array
   `{sektor, avg1m, hijau, total, pendorong: [{kode, ret}]}` urut `avg1m` menurun.
2. `SP.narasiSektor(agregat, totalEmiten)` — fungsi murni baru, output 1 string narasi.
3. Strip `#macro` (`renderMacro`): tambah 1 item Sektor peringkat 1. Bila regime
   pasar belum dimuat tapi data saham ada, makro tampil berisi item Sektor saja
   (sebelumnya makro hidden total — perilaku lama dipertahankan hanya bila tidak
   ada data sama sekali).
4. Panel lipatan baru `details.adv#sektorPanel` di bawah panel tabel: narasi + tabel
   peringkat. Tanpa CSS baru (reuse `.adv`, `.adv table`, `.mut`, `.pos/.neg`).
5. `renderSektor()`: pengisi panel, dipanggil dari `rebuild()`.

Tidak diubah: `detectFase`, `valuasi`, `skor`, `aksi`, `build`, `matchMetode`,
kolom tabel utama, ekspor CSV, drawer, kontrak, horizon banner.

## 3. Data flow

`S._csvRows + S.ksei` → `SP.build()` → `S.data` → `rebuild()` memanggil
`render()` (ada), `renderHorizon()` (ada), `renderSektor()` (baru).
`renderMacro()` membaca `SP.agregatSektor(S.data)[0]`. Tidak ada fetch tambahan.

## 4. Definisi agregasi (fixed)

- Return per emiten: `toNum(r.ret20)` (Perf.1M TradingView / ret20 Yahoo; kosong → 0).
- Hijau: `ret > 0`. Nol/kosong dihitung netral (tidak hijau, tidak merah).
- `avg1m` = rata-rata aritmetika return anggota, dibulatkan 1 desimal.
- Sektor kosong/putih → grup `"Lainnya"`.
- Pendorong = 2 kode dengan return tertinggi per sektor (beserta nilainya).
- Urutan: `avg1m` menurun.

## 5. Template narasi (fixed, tanpa klaim di luar angka)

- Normal: `"{Top} memimpin {avg}% sebulan ({h}/{t} saham hijau), didorong {KODE} {r}% dan {KODE} {r}%."`
- Agregat kosong / semua return kosong: `"Belum ada data return sektoral pada muatan ini."`
- Total emiten < 15: tambah `" (sampel kecil — paling bermakna setelah Scan Seluruh Pasar)"`.
- Tanda angka mengikuti konvensi: positif merah (`pos`), negatif hijau (`neg`) saat dirender.

## 6. Error handling & edge case

- `S.data` kosong dan tanpa regime: makro tetap hidden seperti sekarang; panel menampilkan pesan
  "Belum ada data — klik Download Data / Scan Seluruh Pasar / Muat Contoh."
- Impor manual tanpa `ret20`/`sektor`: tidak NaN (via `toNum`), masuk grup "Lainnya".
- Mode pasar tanpa KSEI: agregat tetap jalan (tidak butuh `k`).
- `renderMacro` tanpa agregat: item Sektor tidak dirender (bukan "—").

## 7. Testing

- `node tests/_test-praktis.js` tetap hijau + cek baru: agregat data contoh
  menghasilkan grup Energi & Keuangan dengan avg terhitung; string HTML berisi
  `id="sektorPanel"` dan `"Rotasi sektoral"`.
- Manual: Muat Contoh → makro menyebut sektor top + panel terisi; Scan Pasar →
  peringkat masuk akal (≈10 sektor IDX-IC); Download Data (10 emiten) → label sampel kecil.

## 8. Non-goals (YAGNI)

- Tanpa fetch berita/headline, tanpa klaim sebab sektoral, tanpa bobot market-cap
  (rata-rata aritmetika saja), tanpa grafik, tanpa filter tabel per sektor,
  tanpa ubah backend Python, tanpa rebuild `.exe` (launcher sudah mode source).
