# Suspend Merah Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Kode emiten diduga suspensi tampil teks merah otomatis via heuristik frontend.

**Architecture:** Fungsi murni `SP.suspen(x)` menilai record yang sudah ada (harga/nilai_harian/vol_ratio/sumber); `render()` membungkus kode dengan class `kode-susp`; 1 baris CSS merah. Display-only, tanpa ubah skor/fase/filter/backend.

**Tech Stack:** Vanilla JS satu file HTML tanpa CDN (`web/screener-praktis.html`), Node smoke test (`tests/_test-praktis.js`).

## Global Constraints

- Satu file HTML offline tanpa CDN — tidak tambah dependensi eksternal.
- Display-only: tanpa ubah skor/aksi/fase; tanpa field backend baru.
- Ragu -> jangan merah (false negative lebih aman); tanpa data = tidak merah.
- Tanpa ubah skor/aksi/fase; tanpa rebuild `.exe` (launcher mode source).

---

### Task 1: `SP.suspen` + uji smoke

**Files:**
- Modify: `web/screener-praktis.html`
- Test: `tests/_test-praktis.js`

**Interfaces:**
- Consumes: `SP.toNum` (ada); record `build()` (`x.r.harga`, `x.r.nilai_harian`, `x.r.s_vol_ratio`, `x.r.sumber`).
- Produces: `SP.suspen(x)` -> `boolean`; dipakai Task 2.

- [ ] **Step 1: Tambah blok uji yang gagal**

Di `tests/_test-praktis.js`, tepat sebelum `console.log(gagal` akhir (sebelum rekap), sisipkan:
```js
// 16) suspen heuristik
{
  const xSusp = { kode: "ZZZZ", r: { harga: "1000", nilai_harian: "0", s_vol_ratio: "0", sumber: "Yahoo Finance + IDX - kualitas baik" } };
  const xOk = { kode: "BBCA", r: { harga: "9000", nilai_harian: "9000000000", s_vol_ratio: "1.2", sumber: "Yahoo Finance + IDX - kualitas baik" } };
  cek("suspen: nilai 0 -> true", SP.suspen(xSusp) === true);
  cek("suspen: normal -> false", SP.suspen(xOk) === false);
  cek("suspen: tanpa data -> false", SP.suspen({}) === false);
  cek("suspen: harga kosong -> true", SP.suspen({ r: { harga: "0", nilai_harian: "100", s_vol_ratio: "1" } }) === true);
}
```

- [ ] **Step 2: Jalankan uji untuk pastikan gagal**

Run: `node tests/_test-praktis.js`
Expected: FAIL / `TypeError: SP.suspen is not a function` pada 4 cek baru; cek lama PASS.

- [ ] **Step 3: Implementasi minimal**

Sisipkan setelah akhir fungsi `bounty` (baris `}` tepat sebelum `// ---------- banding kompetitor se-industri`), di dalam modul `SP`:
```js
  // ---------- suspen heuristik (display-only) ----------
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
Di blok `return` modul SP (baris `smartMoney: smartMoney, bounty: bounty,`), tambahkan `suspen: suspen,` sehingga menjadi:
```js
    smartMoney: smartMoney, bounty: bounty, suspen: suspen, pesaing: pesaing,
```

- [ ] **Step 4: Jalankan uji sampai lolos**

Run: `node tests/_test-praktis.js`
Expected: PASS — "Semua uji lulus", termasuk 4 cek baru blok 16.

- [ ] **Step 5: Commit**

```bash
git add web/screener-praktis.html tests/_test-praktis.js
git commit -m "feat: tambah SP.suspen heuristik suspensi"
```

---

### Task 2: Render kode merah + CSS

**Files:**
- Modify: `web/screener-praktis.html` (CSS 1 baris, render kolom kode, cek string test)
- Test: `tests/_test-praktis.js` + manual browser

**Interfaces:**
- Consumes: `SP.suspen` dari Task 1; `render()` tabel utama (`S.data`, `x.kode`).
- Produces: UI selesai. Tidak ada API baru.

- [ ] **Step 1: Tambah 2 cek string ke uji (gagal dulu)**

Di blok cek string HTML (dekat `cek("panel quest ada"`, blok 7), tambah:
```js
  cek("suspen dipakai", html.includes("SP.suspen"));
  cek("css kode-susp ada", html.includes("kode-susp"));
```

- [ ] **Step 2: Jalankan uji untuk pastikan 2 cek baru gagal**

Run: `node tests/_test-praktis.js`
Expected: FAIL tepat pada 2 cek baru; semua cek lama PASS.

- [ ] **Step 3: CSS + render**

Di CSS setelah baris `.kode{font-weight:700;font-size:13px}` tambahkan:
```css
.kode-susp{color:#d00;font-weight:700}
```
Di `render()` ubah baris:
```js
        '<td class="kode">' + x.kode + "</td>" +
```
menjadi:
```js
        '<td class="kode' + (SP.suspen(x) ? " kode-susp" : "") + '"' + (SP.suspen(x) ? ' title="diduga suspensi (heuristik: harga/nilai/volume 0)"' : "") + ">" + x.kode + "</td>" +
```
Quest (satu baris, reuse fungsi sama): di `renderQuest()` ubah `'<b>' + q.kode + "</b>"` menjadi `'<b class="' + (SP.suspen({ kode: q.kode, r: ((S.data.filter(function (z) { return z.kode === q.kode; })[0] || {}).r || {}) }) ? "kode-susp" : "") + '">' + q.kode + "</b>"` — bila terlalu berisik boleh lewati, tabel utama tetap wajib.

- [ ] **Step 4: Jalankan uji sampai lolos**

Run: `node tests/_test-praktis.js`
Expected: PASS — "Semua uji lulus".

- [ ] **Step 5: Uji manual browser (wajib)**

1. Jalankan via `Jalankan Screener.vbs` + Download Data -> cari emiten `nilai_harian 0` / `harga kosong` -> kode merah dengan tooltip.
2. Emiten normal tetap hitam; reload tetap konsisten.
3. Cek quest `Misi Malam Ini` tidak rusak (fungsi renderQuest tidak diubah).

- [ ] **Step 6: Commit**

```bash
git add web/screener-praktis.html tests/_test-praktis.js
git commit -m "feat: kode emiten suspen tampil merah"
```
