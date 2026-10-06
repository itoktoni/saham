# Fair Value Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tampilkan angka fair value sebagai kolom tabel dan rincian 3 metode valuasi di drawer.

**Architecture:** `valuasi()` di `web/screener-praktis.html` menamai 3 komponennya (rumus tidak berubah); kolom FV + rincian drawer hanya membaca field baru; sepenuhnya frontend, tanpa backend.

**Tech Stack:** Vanilla JS satu file HTML (tanpa CDN), Node smoke test `tests/_test-praktis.js`. Python/backend tidak disentuh.

## Global Constraints

- Satu file HTML offline tanpa CDN — tidak tambah dependensi eksternal.
- Jangan ubah rumus valuasi, median, `detectFase`, `skor`, `aksi`, `build`, kalibrasi horizon 3 bulan.
- Semua akses angka di JS via `SP.toNum()`/`nf` yang ada; intrinsik 0 → "—".
- Warna FV ikut konvensi MOS/Upside (hijau `neg` bila murah, merah `pos` bila mahal).
- Ekspor CSV: kolom `fv` di-append di AKHIR (tidak menggeser kolom lama).
- Narasi jujur: bukan nasihat investasi (tidak ada klaim baru).

---

### Task 1: `valuasi()` mengembalikan rincian komponen

**Files:**
- Modify: `web/screener-praktis.html` (fungsi `valuasi`, blok `var v = [];` sampai `return {...}`)
- Test: `tests/_test-praktis.js` (blok 11 baru)

**Interfaces:**
- Consumes: tidak ada (fungsi murni, pakai `toNum`/`clamp` internal)
- Produces: `valuasi(r)` → field baru `rincian: {graham, roepbv, growth}` (0 bila tak valid) dan `nMetode` (0–3); field lama tidak berubah; dipakai Task 2 di kolom FV dan drawer.

- [ ] **Step 1: Tambah blok uji yang gagal (blok 11)**

Di `tests/_test-praktis.js`, tepat sebelum `console.log(gagal`, sisipkan:
```js
// 11) rincian fair value
{
  const mur = { kode: "MURAH", harga: "100", eps: "100", ekuitas: "50000", saham: "1000", laba: "10000", cagr: "10" };
  const vm = SP.valuasi(mur);
  cek("rincian: 3 komponen valid", vm.nMetode === 3 && vm.rincian.graham > 0 && vm.rincian.roepbv > 0 && vm.rincian.growth > 0, JSON.stringify(vm.rincian));
  cek("rincian: graham terbesar, median = growth", vm.rincian.graham > vm.rincian.roepbv && vm.intrinsic === vm.rincian.growth, vm.intrinsic + " vs " + vm.rincian.growth);
  const kosong = SP.valuasi({});
  cek("rincian: kosong aman", kosong.intrinsic === 0 && kosong.nMetode === 0 && kosong.rincian.graham === 0);
}
```

- [ ] **Step 2: Jalankan uji untuk pastikan gagal**

Run: `node tests/_test-praktis.js`
Expected: FAIL pada cek "rincian" (karena `vm.rincian` masih `undefined` → TypeError saat baca `.graham`); cek lama lain PASS.

- [ ] **Step 3: Implementasi minimal (rumus tidak berubah)**

Ganti blok ini di `valuasi()`:
```js
    var v = [];
    if (eps > 0) v.push(eps * (7 + g) * 7.8 / 11.4);          // Graham disesuaikan
    if (bvps > 0 && roe > 0) v.push(bvps * (roe / 10));        // ROE-PBV
    if (bvps > 0 && roe > 0) v.push(bvps * Math.pow(1 + roe / 100, 5)); // Equity growth
    v = v.filter(function (x) { return isFinite(x) && x > 0; }).sort(function (a, b) { return a - b; });
    var intrinsic = v.length ? (v.length % 2 ? v[(v.length - 1) / 2] : (v[v.length / 2 - 1] + v[v.length / 2]) / 2) : 0;
    var mos = intrinsic > 0 ? (intrinsic - harga) / intrinsic * 100.0 : 0;
    return { bvps: bvps, roe: roe, per: per, pbv: pbv, intrinsic: intrinsic, mos: mos };
```
Menjadi:
```js
    var comp = { graham: 0, roepbv: 0, growth: 0 };
    if (eps > 0) comp.graham = eps * (7 + g) * 7.8 / 11.4;          // Graham disesuaikan
    if (bvps > 0 && roe > 0) comp.roepbv = bvps * (roe / 10);        // ROE-PBV
    if (bvps > 0 && roe > 0) comp.growth = bvps * Math.pow(1 + roe / 100, 5); // Equity growth
    var v = [comp.graham, comp.roepbv, comp.growth]
      .filter(function (x) { return isFinite(x) && x > 0; }).sort(function (a, b) { return a - b; });
    var intrinsic = v.length ? (v.length % 2 ? v[(v.length - 1) / 2] : (v[v.length / 2 - 1] + v[v.length / 2]) / 2) : 0;
    var mos = intrinsic > 0 ? (intrinsic - harga) / intrinsic * 100.0 : 0;
    return { bvps: bvps, roe: roe, per: per, pbv: pbv, intrinsic: intrinsic, mos: mos, rincian: comp, nMetode: v.length };
```

- [ ] **Step 4: Jalankan uji sampai lolos**

Run: `node tests/_test-praktis.js`
Expected: PASS — "Semua uji lulus", termasuk 3 cek baru blok 11 (median fixture murah = growth: [100, 124.4, 1163.2] → tengah growth).

### Task 2: Kolom FV + rincian drawer + CSV

**Files:**
- Modify: `web/screener-praktis.html` (COLS + render body + drawer `s2` + ekspor CSV; tambah 2 cek string di `tests/_test-praktis.js`)
- Test: `tests/_test-praktis.js` + uji manual browser

**Interfaces:**
- Consumes: `val.rincian`, `val.nMetode`, `val.intrinsic` dari Task 1; pola `nf`, `row()`, badge MOS yang sudah ada
- Produces: UI selesai — tidak ada konsumen lanjutan

- [ ] **Step 1: Tambah 2 cek string HTML ke uji**

Di `tests/_test-praktis.js` blok 7, setelah baris `cek("ambang likuid 5M"...`, tambahkan:
```js
  cek("kolom FV ada", html.includes('t: "FV"'));
  cek("rincian FV drawer ada", html.includes("FV Graham") && html.includes("FV ROE-PBV") && html.includes("FV Equity growth"));
```

- [ ] **Step 2: Jalankan uji untuk pastikan 2 cek baru gagal**

Run: `node tests/_test-praktis.js`
Expected: FAIL tepat pada 2 cek baru; semua cek lama PASS.

- [ ] **Step 3: Tambah kolom FV**

Di `COLS`, setelah baris `{ k: "mos", t: "MOS %", n: true, get: function (d) { return d.val.mos; } },` tambahkan:
```js
    { k: "fv", t: "FV", n: true, get: function (d) { return d.val.intrinsic; } },
```
Di render body, setelah baris `'<td class="n">' + mos + "</td>" +` tambahkan:
```js
        '<td class="n">' + fvTxt + "</td>" +
```
Dan setelah baris `var mos = '<span class="' + ...` (definisi `mos`), tambahkan definisi:
```js
      var fvTxt = x.val.intrinsic > 0
        ? '<span class="' + (x.val.intrinsic > SP.toNum(x.r.harga) ? "neg" : "pos") + '">' + nf(x.val.intrinsic, 0) + "</span>"
        : '<span class="mut">—</span>';
```

- [ ] **Step 4: Tambah rincian di drawer langkah 2**

Setelah baris `"</div>" + row("Nilai intrinsik (median metode)", nf(v.intrinsic, 0)) +` tambahkan:
```js
      row("FV Graham", v.rincian.graham > 0 ? nf(v.rincian.graham, 0) : "—") +
      row("FV ROE-PBV", v.rincian.roepbv > 0 ? nf(v.rincian.roepbv, 0) : "—") +
      row("FV Equity growth", v.rincian.growth > 0 ? nf(v.rincian.growth, 0) : "—") +
      row("Median dari", v.nMetode + " metode valid") +
```

- [ ] **Step 5: Tambah kolom `fv` di ekspor CSV (append akhir)**

Ubah:
```js
    var head = ["kode","nama","sektor","harga","fase","asing_pct","dasing_1m","mos","skor","aksi"];
```
menjadi:
```js
    var head = ["kode","nama","sektor","harga","fase","asing_pct","dasing_1m","mos","skor","aksi","fv"];
```
Dan ubah:
```js
        x.val.mos.toFixed(1), x.skor, x.aksi].join(","));
```
menjadi:
```js
        x.val.mos.toFixed(1), x.skor, x.aksi, x.val.intrinsic.toFixed(0)].join(","));
```

- [ ] **Step 6: Jalankan uji sampai lolos**

Run: `node tests/_test-praktis.js`
Expected: PASS — "Semua uji lulus".

- [ ] **Step 7: Uji manual browser (wajib sebelum selesai)**

1. Jalankan via `Screener Saham.exe`, klik **Muat Contoh**.
2. Kolom FV terisi angka (BBCA dkk), sortable via header.
3. Buka drawer satu saham: langkah 2 menampilkan 3 baris FV + "Median dari N metode valid".
4. Ekspor CSV: kolom terakhir `fv` terisi.
