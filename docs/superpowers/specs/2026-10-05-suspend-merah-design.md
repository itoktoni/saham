# Spec: Kode Emiten Merah bila Suspen (heuristik otomatis)

Tanggal: 2026-10-05 | Status: disetujui user (lanjutkan) | Pendekatan: A otomatis dulu, C riset IDX paralel
Konsumsi: record `build()` / `ambil_tv()` yang sudah ada. File diubah: `web/screener-praktis.html` (+ uji `tests/_test-praktis.js`).

## 1. Latar & keputusan

Tidak ada info suspen di sumber manapun saat ini:
- `app/app-screener.py:67` `TV_COLS` tanpa kolom status/halt.
- `scripts/fetch-data-idx.py` Yahoo `quoteSummary/chart` tanpa flag suspen.
- `scripts/fetch-sahamscope.py` hanya `pulse + acc + insider`.
- IDX `GetCompanyProfiles` hanya `KodeEmiten, NamaEmiten, Sektor, SubSektor, PapanPencatatan`.

User memilih: terapkan deteksi otomatis dulu, riset IDX jalan paralel sebagai follow-up.

## 2. Desain (Pendekatan A)

Fungsi murni `SP.suspen(x)` di modul `SP`, display-only, tanpa ubah skor/fase/filter:

```js
function suspen(x) {
  var r = (x && x.r) || {};
  if (toNum(r.harga) <= 0) return true;
  if (toNum(r.nilai_harian) <= 0) return true;
  if (toNum(r.s_vol_ratio) <= 0) return true;
  var s = String(r.sumber || "").toLowerCase();
  if (s.indexOf("harga kosong") >= 0) return true;
  return false;
}
```

- Ragu -> jangan merah (false negative lebih aman).
- Tanpa data -> tidak merah, bukan error.

UI: 1 baris CSS + 1 titik render kolom kode tabel utama:
- CSS: `td.kode-susp, .kode-susp { color:#d00; font-weight:700 }`
- Render: bila `SP.suspen(x)` bungkus kode dengan class tersebut + `title="diduga suspensi (heuristik)"`.
- Berlaku juga di kartu quest/drawer bila menampilkan kode (pakai fungsi sama, tanpa duplikasi logika).
- Export di `return` modul SP: `suspen: suspen`.

## 3. Error handling & edge case

- Saham super sepi tapi tidak suspen bisa ikut merah (keterbatasan heuristik yang diterima user).
- `bars_30` kosong tidak dipakai sebagai sinyal (banyak emiten pasar tanpa riwayat).
- localStorage / arsip quest tidak berubah.

## 4. Testing

- `tests/_test-praktis.js` blok baru: volume 0 -> `SP.suspen true`; normal -> false; `{}` -> false; string HTML mengandung `kode-susp`.
- Manual: Download Data -> cari emiten nilai_harian 0 / harga kosong -> kode merah; reload tetap merah; emiten normal tetap hitam.

## 5. Non-goals (YAGNI)

- Tanpa fetcher IDX baru di spec ini; tanpa field `susp` backend; tanpa filter/exclude suspen dari bounty; tanpa ubah skor/aksi/fase.
- Follow-up terpisah (spec C): riset endpoint notasi khusus / pengumuman suspensi IDX, bila ketemu tinggal ganti isi `SP.suspen` baca flag resmi tanpa ubah UI.
