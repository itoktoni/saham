# Combo Meter C0–C3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tampilkan level konfluensi smart-money C0–C3 per saham sebagai kolom tabel + bukti di drawer, display-only.

**Architecture:** `SP.combo(x, entry)` murni menghitung 3 bukti + breaker dari `S.scope.emiten`; kolom Combo dan blok drawer hanya render; skor/aksi tidak tersentuh.

**Tech Stack:** Vanilla JS satu file HTML (tanpa CDN), Node smoke test `tests/_test-praktis.js`. Python/backend tidak disentuh.

## Global Constraints

- Satu file HTML offline tanpa CDN — tidak tambah dependensi eksternal.
- Jangan ubah `valuasi`, `detectFase`, `skor`, `aksi`, `build`, kalibrasi horizon 3 bulan.
- Semua akses angka via `SP.toNum()`; tanggal insider dibanding string ISO `YYYY-MM-DD` (tanpa lib).
- Tanpa scope → "—" (bukan C0); UNKNOWN tampil "?" dan dihitung 0.
- Display-only: tidak mengubah skor; catatan eksplisit di drawer.
- Tanpa rebuild `.exe` (launcher mode source).

---

### Task 1: `SP.combo` + uji smoke

**Files:**
- Modify: `web/screener-praktis.html` (modul `SP`: sisip setelah `barAkumulasi`, sebelum `// ---------- valuasi sederhana`; dan blok `return` modul SP)
- Test: `tests/_test-praktis.js` (blok 12 baru)

**Interfaces:**
- Consumes: `SP.toNum` (sudah ada)
- Produces: `SP.combo(x, entry)` → `{level: -1..3, bukti: [{st: "Y"|"N"|"?", txt}], breaker: string|null}`; dipakai Task 2. Aturan: E1 streak (top-1 buyer, 5 titik terakhir series, YES bila ≥3 `nval>0`; tanpa series → "?"); E2 insider buy ≤60 hari (banding `t.date >= cutoff` ISO; tanggal kosong/tak valid otomatis gugur; tanpa data → "?"); E3 fase Spring/Akumulasi = YES else NO; level = jumlah YES, C3 wajib E3 YES (maks C2), breaker (Distribusi ATAU sell ≤60 hari) → maks C1; tanpa entry → level -1.

- [ ] **Step 1: Tambah blok uji yang gagal (blok 12)**

Di `tests/_test-praktis.js`, tepat sebelum `console.log(gagal`, sisipkan (tanggal dinamis agar tidak basi):
```js
// 12) kombo smart-money
{
  const d10 = new Date(Date.now() - 10 * 864e5).toISOString().slice(0, 10);
  const sc = { acc: { top_buyers: [{ broker: "OD", nval: 5 }], top_sellers: [], series: { OD: [[1, 1], [2, 3], [-1, 2], [3, 5], [4, 9]] } }, insider: [{ name: "DIR A", date: d10, action_type: "buy", changes_value: "100", badges: ["DIREKTUR"] }] };
  const c3 = SP.combo({ kode: "T", fase: "Spring" }, sc);
  cek("combo: 3 YES fase Spring = C3", c3.level === 3, JSON.stringify(c3));
  const cB = SP.combo({ kode: "T", fase: "Spring" }, { acc: sc.acc, insider: [{ name: "X", date: d10, action_type: "sell" }] });
  cek("combo: insider sell = breaker C1", cB.level === 1 && !!cB.breaker, JSON.stringify(cB));
  const c2 = SP.combo({ kode: "T", fase: "Markup" }, sc);
  cek("combo: tanpa fase = maks C2", c2.level === 2, JSON.stringify(c2));
  const cN = SP.combo({ kode: "T", fase: "Spring" }, null);
  cek("combo: tanpa scope = —", cN.level === -1);
  const cU = SP.combo({ kode: "T", fase: "Spring" }, { acc: {}, insider: [] });
  cek("combo: UNKNOWN tampil ?", cU.bukti[0].st === "?" && cU.level <= 1, JSON.stringify(cU));
}
```

- [ ] **Step 2: Jalankan uji untuk pastikan gagal**

Run: `node tests/_test-praktis.js`
Expected: error `TypeError: SP.combo is not a function`.

- [ ] **Step 3: Implementasi minimal**

Sisipkan setelah akhir fungsi `barAkumulasi` (baris `}` tepat sebelum `// ---------- valuasi sederhana`):
```js
  // ---------- kombo smart-money C0-C3 (display-only) ----------
  function combo(x, entry) {
    if (!entry) return { level: -1, bukti: [], breaker: null };
    var acc = entry.acc || {};
    var b1 = (acc.top_buyers || [])[0];
    var e1 = { st: "?", txt: "tanpa data series" };
    if (b1 && acc.series && acc.series[b1.broker] && acc.series[b1.broker].length) {
      var last5 = acc.series[b1.broker].slice(-5);
      var hit = last5.filter(function (p) { return toNum(p[0]) > 0; }).length;
      e1 = { st: hit >= 3 ? "Y" : "N", txt: b1.broker + " " + hit + "/5 hari net-buy" };
    }
    var cutoff = "";
    try { cutoff = new Date(Date.now() - 60 * 864e5).toISOString().slice(0, 10); } catch (e) {}
    var items = entry.insider || [];
    var segar = function (t) { return t && t.date && t.date >= cutoff; };
    var buys = items.filter(function (t) { return t.action_type === "buy" && segar(t); });
    var sells = items.filter(function (t) { return t.action_type === "sell" && segar(t); });
    var e2 = items.length
      ? (buys.length ? null : { st: "N", txt: "tanpa insider buy ≤60 hari" })
      : { st: "?", txt: "tanpa data insider" };
    if (e2 === null) {
      var jb = (buys[0].badges || []).join(",");
      e2 = { st: "Y", txt: buys[0].name + " +" + (buys[0].changes_value || "?") + " (" + buys[0].date + ")" + (jb ? " [" + jb + "]" : " (tanpa info jabatan)") };
    }
    var e3 = (x.fase === "Spring" || x.fase === "Akumulasi")
      ? { st: "Y", txt: "fase " + x.fase }
      : { st: "N", txt: "fase " + x.fase };
    var breaker = null;
    if (x.fase === "Distribusi") breaker = "fase Distribusi";
    if (sells.length) breaker = "insider sell " + sells[0].name + " (" + sells[0].date + ")";
    var lvl = [e1, e2, e3].filter(function (e) { return e.st === "Y"; }).length;
    if (e3.st !== "Y") lvl = Math.min(lvl, 2);
    if (breaker) lvl = Math.min(lvl, 1);
    return { level: lvl, bukti: [e1, e2, e3], breaker: breaker };
  }
```
Dan di blok `return` modul SP, tambahkan `combo: combo,` sehingga baris ekspor menjadi:
```js
    METODE: METODE, matchMetode: matchMetode, agregatSektor: agregatSektor, narasiSektor: narasiSektor, barAkumulasi: barAkumulasi, combo: combo,
```

- [ ] **Step 4: Jalankan uji sampai lolos**

Run: `node tests/_test-praktis.js`
Expected: PASS — "Semua uji lulus", termasuk 5 cek baru blok 12.

### Task 2: Kolom Combo + blok drawer

**Files:**
- Modify: `web/screener-praktis.html` (helper `comboLvl`/`comboBadge`/`comboBox`, COLS, render body, drawer langkah 3; tambah 3 cek string di `tests/_test-praktis.js`)
- Test: `tests/_test-praktis.js` + uji manual browser

**Interfaces:**
- Consumes: `SP.combo` dari Task 1; `(S.scope.emiten || {})[kode]` sebagai entry; pola badge/chip yang sudah ada
- Produces: UI selesai — tidak ada konsumen lanjutan

- [ ] **Step 1: Tambah 3 cek string HTML ke uji**

Di `tests/_test-praktis.js` blok 7, setelah baris `cek("badge Scope di makro"...`, tambahkan:
```js
  cek("kolom Combo ada", html.includes('t: "Combo"'));
  cek("blok kombo drawer ada", html.includes("Kombo smart-money") && html.includes("SP.combo"));
  cek("helper combo ada", html.includes("comboLvl"));
```

- [ ] **Step 2: Jalankan uji untuk pastikan 3 cek baru gagal**

Run: `node tests/_test-praktis.js`
Expected: FAIL tepat pada 3 cek baru; semua cek lama PASS.

- [ ] **Step 3: Tambah helper + kolom Combo**

Tepat sebelum `function likuidBadge(x) {` sisipkan:
```js
  function comboLvl(x) { var e = (S.scope.emiten || {})[x.kode]; return e ? SP.combo(x, e).level : -1; }
  function comboBadge(x) {
    var e = (S.scope.emiten || {})[x.kode];
    if (!e) return '<span class="mut">—</span>';
    var c = SP.combo(x, e);
    var cls = ["badge b-netral", "aksi a-pantau", "badge b-spring", "aksi a-beli"][c.level];
    var tip = c.bukti.map(function (b) { return b.txt; }).join(" · ") + (c.breaker ? " · BREAKER: " + c.breaker : "");
    return '<span class="' + cls + '" title="' + tip.replace(/"/g, "") + '">C' + c.level + "</span>";
  }
```
Di `COLS`, setelah baris `{ k: "likuid", ... }` tambahkan:
```js
    { k: "combo", t: "Combo", n: false, get: function (d) { return comboLvl(d); } },
```
Di render body, setelah baris `"<td>" + likuidBadge(x) + "</td>" +` tambahkan:
```js
        "<td>" + comboBadge(x) + "</td>" +
```

- [ ] **Step 4: Tambah blok drawer langkah 3**

Tepat sebelum `function alasanFase(x) {` (setelah `akumulasiBox`) sisipkan:
```js
  function comboBox(x) {
    var e = (S.scope.emiten || {})[x.kode];
    if (!e) return '<div class="mut" style="margin-top:6px">Kombo butuh Download Data (cache SahamScope).</div>';
    var c = SP.combo(x, e);
    var W = { Y: "#17795e", N: "#c62828", "?": "#8a8f98" };
    var nm = ["Streak", "Insider", "Fase"];
    var chips = c.bukti.map(function (b, i) {
      return '<span class="aksi" style="background:' + W[b.st] + ";border-color:" + W[b.st] + ';color:#fff;margin-right:4px">' + nm[i] + ": " + b.txt + "</span>";
    }).join("");
    return '<div style="margin-top:8px"><b>Kombo smart-money: C' + c.level + "</b><div style='margin-top:4px'>" + chips + "</div>" +
      (c.breaker ? '<div class="warn">Breaker: ' + c.breaker + " — maks C1.</div>" : "") +
      '<div class="mut" style="margin-top:2px">Display-only, tidak mengubah skor.</div></div>';
  }
```
Dan di langkah 3 drawer, setelah baris `akumulasiBox(r) +` tambahkan:
```js
      comboBox(x) +
```

- [ ] **Step 5: Jalankan uji sampai lolos**

Run: `node tests/_test-praktis.js`
Expected: PASS — "Semua uji lulus".

- [ ] **Step 6: Uji manual browser (wajib sebelum selesai)**

1. Jalankan via `Screener Saham.exe`, klik **Download Data**.
2. Kolom Combo terisi (C0–C3/—); cocokkan 1 saham (misal BBCA) dengan `data/sahamscope.json` (top buyer + series + insider).
3. Buka drawer: blok kombo menampilkan 3 chip + breaker bila ada.
4. Klik **Scan Seluruh Pasar**: kolom Combo "—" dan drawer menampilkan pesan butuh Download (tanpa error console).
