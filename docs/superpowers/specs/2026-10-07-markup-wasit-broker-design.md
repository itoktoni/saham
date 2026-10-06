# Spec: Wasit Broker untuk Markup vs Distribusi

Tanggal: 2026-10-07
Status: disetujui user (broker streak + Beli bersyarat)

## 1. Latar
- `detectFase` (`web/screener-praktis.html:332`) sudah punya fase Markup, tapi cek
  Distribusi duluan dengan kunci KSEI bulanan (`dA/dI`) yang basi untuk saham lari.
  Akibat: runner seperti CSMI +25% / ASMI +32% dicap Distribusi → skor 20-an → Hindari,
  padahal saat IHSG +1,5% mereka yang lari.
- `sMom = 50 - ret20*4` (`:827`) menghukum semua pelari (ret +25% → sMom 0).
- Aksi Markup lama (`:841`, `pos < 0.55 && sc >= 70`) mustahil untuk saham yang sudah jalan.
- Data `sahamscope.json` sudah punya series 5 hari per broker + logika streak di `combo()`.

## 2. Tujuan
- Pisahkan Markup (ikut) dari Distribusi (hindari) memakai streak broker harian.
- Runner sehat berpeluang mencapai skor ≥ 60 dan aksi Beli bersyarat.
- Tanpa data scope: perilaku lama, tidak ada yang berubah.

## 3. Non-tujuan
- Tidak mengubah bobot skor TF, valuasi, atau fase lain (Spring/Akumulasi/Netral).
- Tidak menarik scope untuk mode Scan Pasar (tetap fallback lama di sana).
- Tidak menambah label aksi baru (tetap Beli/Pantau/Hindari).

## 4. Desain

### 4.1 Wasit broker di detectFase
- `detectFase(r, k)` terima parameter ketiga opsional `entry` (scope emiten, boleh null).
- `build()` teruskan `entry` dari `(S.scope.emiten || {})[kode]` — cek dulu bentuk
  pemanggilan `build(rows, ksei, fundMap)` agar signature tetap kompatibel
  (tambah parameter opsional, jangan ubah urutan yang ada).
- Aturan baru, diletakkan SEBELUM cek Distribusi lama, hanya untuk zona atas
  (`pos >= 0.72 && vol >= 1.3`):
  - streak beli: broker top (`acc.top_buyers[0]`) net-buy ≥ 3 dari 5 hari terakhir
    (pakai hitungan yang sama dengan `combo()`) → return "Markup".
  - dominan jual: total net-sell top sellers ≥ total net-buy top buyers
    (dari `acc.top_buyers` / `acc.top_sellers`, field `nval`) → return "Distribusi".
  - `entry` kosong / series kosong → lanjut ke aturan lama apa adanya.
- Faselain tidak disentuh.

### 4.2 Lunak hukuman momentum untuk Markup terkonfirmasi
- Di `skorTF()` (dan `skor()` bila masih dipakai): jika `fase === "Markup"` DAN
  streak beli terkonfirmasi (flag dari 4.1, teruskan via parameter atau tandai di record),
  `sMom = clamp(50 - ret20*2, 20, 100)`; selain itu rumus lama `clamp(50 - ret20*4, 0, 100)`.
- Tidak ada perubahan bobot.

### 4.3 Aksi Markup = Beli bersyarat
- Ganti syarat Markup di `aksi()` dan `aksiTF()` (cabang `tf === "kilat"` memakai
  Markup juga — selaraskan ambangnya di sana bila memakai `sc >= 60`):
  `fase === "Markup" && sc >= 60 && val.mos > -15` → "Beli", selain itu "Pantau".
- Distribusi tetap "Hindari" tanpa kecuali.

### 4.4 Bonus likuiditas kandang bandar
- Fakta lapangan: big cap lamban digerakkan; bandar main di value harian 500jt–3M.
- Di `skor()` dan `skorTF()`, sebelum `sTiming = clamp(...)`: jika
  `nilai_harian` dalam [500jt, 3M] → `sTiming += 8` (selevel bonus sideways +8 yang ada).
- Di luar rentang: tidak ada bonus maupun penalti. Ambang 500jt selaras dengan
  `minLiq` mode Bulanan; angka +8 boleh di-tune nanti tanpa ubah struktur.

## 5. Error handling
- `entry` null/undefined, `acc` kosong, `series` kosong → fallback aturan lama.
  Tidak boleh throw bila scope belum diunduh.
- `nval` non-numerik → perlakukan 0 via `SP.toNum`.

## 6. Testing
- Unit (node/vm atau baca logika): 4 kasus — (a) zona atas + streak beli → Markup;
  (b) zona atas + dominan jual → Distribusi; (c) zona atas tanpa scope → hasil lama;
  (d) runner Markup+streak ret20 +25% → sMom = 20 dan skor total ≥ 60 pada
  fundamental sedang (sKualitas ~70, sNilai ~40).
- Regresi: `tests/test-harian.py` 4 passed + `tests/_smoke-ui.py` tetap OK.
- Manual: Reload + Download Data, cek saham runner berubah fase Markup dan
  muncul Beli bila syarat terpenuhi.

## 7. Kriteria sukses
- Runner dengan streak broker tampil Markup (bukan Distribusi) dan bisa Beli.
- Tanpa scope, semua fase/simulasi sama seperti sebelum perubahan.
- Tidak ada error console baru.

## 8. Risiko
- Scope hanya untuk watchlist: mode Scan Pasar tetap buta broker (dinyatakan jujur,
  bukan diperbaiki di spec ini).
- Streak broker bisa escolher bandar distribusi rapi (net-buy kecil merata) —
  mitigasi: syarat dominan-jual eksplisit di 4.1.
