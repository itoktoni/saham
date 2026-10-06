# Markup Wasit Broker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pisahkan Markup dari Distribusi memakai streak broker, lunakkan hukuman momentum untuk Markup terkonfirmasi, dan jadikan aksi Markup Beli bersyarat.

**Architecture:** Tambah 2 helper murni (`streakBeli`, `dominanJual`) di closure SP `web/screener-praktis.html`, threaded lewat parameter opsional baru (`detectFase(r,k,entry)`, `build(rows,ksei,fundMap,scopeMap)`), lunakkan `sMom` hanya untuk Markup+streak di `skor()` dan `skorTF()`, ubah cabang Markup di `aksi()`/`aksiTF()`.

**Tech Stack:** Vanilla JS di satu file HTML, verifikasi via node syntax check + harness node dengan stub DOM + `tests/test-harian.py` + `tests/_smoke-ui.py`.

## Global Constraints

- Tanpa data scope: perilaku lama, tidak ada yang berubah, tidak boleh throw.
- Tidak ada label aksi baru; tetap Beli/Pantau/Hindari.
- Tidak ubah bobot skor TF, valuasi, atau fase Spring/Akumulasi/Netral.
- `nval` non-numerik diperlakukan 0 via `SP.toNum` (sebenarnya `toNum` di scope SP).
- Tulis/setiap baca file HTML dengan benar sebagai UTF-8 biner (jangan lewat pipe teks PowerShell, jangan `Set-Content` tanpa `-Encoding utf8NoBOM`); hindari baris yang mengandung karakter non-ASCII pada oldString/newString.

---

### Task 1: Helper streak + cabang broker di detectFase

**Files:**
- Modify: `web/screener-praktis.html:332-347` (detectFase), tambah helper sebelum `detectFase`, tambah ke `return {...}` SP (~baris 916-923)
- Test: `tests/test-markup.js` (baru, harness node)

**Interfaces:**
- Consumes: `entry.acc = {top_buyers: [{broker, nval}], top_sellers: [{broker, nval}], series: {BROKER: [[net, ...], ...]}}` (bentuk dari `ringkas_acc` di `scripts/fetch-sahamscope.py:35-47`; `p[0]` = net harian seperti dipakai `combo()`)
- Produces: `streakBeli(entry) -> bool`, `dominanJual(entry) -> bool`, `detectFase(r, k, entry)` dengan `entry` opsional

- [ ] **Step 1: Write the failing test**

```js
// tests/test-markup.js
const fs = require("fs");
const vm = require("vm");
const html = fs.readFileSync("web/screener-praktis.html", "utf8");
const src = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)][0][1];
function elStub() {
  return new Proxy({}, {
    get: (t, p) => {
      if (p === "style") return {};
      if (p === "classList") return { add() {}, remove() {}, toggle() {} };
      if (p === "tHead" || p === "tBodies") return { innerHTML: "", rows: [] };
      return (...a) => elStub();
    },
    set: () => true
  });
}
const store = {};
const sandbox = {
  console,
  location: { protocol: "http:" },
  localStorage: {
    getItem: (k) => (k in store ? store[k] : null),
    setItem: (k, v) => { store[k] = String(v); },
    removeItem: (k) => { delete store[k]; }
  },
  document: {
    getElementById: () => elStub(),
    createElement: () => elStub(),
    querySelectorAll: () => []
  }
};
sandbox.window = sandbox;
sandbox.globalThis = sandbox;
vm.createContext(sandbox);
vm.runInContext(src + "\n;globalThis.__SP = SP;", sandbox, { timeout: 10000 });
const SP = sandbox.__SP;
function entryStreak() {
  return { acc: {
    top_buyers: [{ broker: "CC", nval: 500 }],
    top_sellers: [{ broker: "XX", nval: 100 }],
    series: { CC: [[1], [2], [-1], [3], [4]] }
  } };
}
console.log("streak:", SP.streakBeli(entryStreak()) === true ? "OK" : "FAIL");
console.log("noentry:", SP.streakBeli(null) === false ? "OK" : "FAIL");
console.log("dominan:", SP.dominanJual({ acc: {
  top_buyers: [{ broker: "A", nval: 100 }],
  top_sellers: [{ broker: "B", nval: 500 }]
} }) === true ? "OK" : "FAIL");
const r = { s_springlow: 100, s_resistance: 200, harga: 190,
  s_vol_ratio: 2.0, s_spring: 0, s_sideways: 0, s_closeabove: 1 };
const k = { dksei_asing_1m: -1.0, dksei_institusi_1m: -0.5 };
console.log("fase-streak:", SP.detectFase(r, k, entryStreak()) === "Markup" ? "OK" : "FAIL");
console.log("fase-noscope:", SP.detectFase(r, k, null) === "Distribusi" ? "OK" : "FAIL");
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node tests/test-markup.js`
Expected: FAIL with `SP.streakBeli is not a function` (atau `__SP` undefined untuk bagian itu)

- [ ] **Step 3: Write minimal implementation**

Helper baru tepat sebelum `function detectFase` (baris 332):

```js
  function streakBeli(entry) {
    var acc = (entry && entry.acc) || {};
    var b1 = (acc.top_buyers || [])[0];
    if (!b1 || !acc.series || !acc.series[b1.broker]) return false;
    var last5 = acc.series[b1.broker].slice(-5);
    if (!last5.length) return false;
    var hit = last5.filter(function (p) { return toNum(p[0]) > 0; }).length;
    return hit >= 3;
  }
  function dominanJual(entry) {
    function tot(list) {
      return (list || []).reduce(function (a, b) { return a + toNum(b.nval); }, 0);
    }
    var acc = (entry && entry.acc) || {};
    var jb = tot(acc.top_buyers), js = tot(acc.top_sellers);
    return (jb + js) > 0 && js >= jb;
  }
```

Cabang baru di awal `detectFase`, SEBELUM cek Distribusi lama:

```js
  function detectFase(r, k, entry) {
    k = k || {};
    ...
    var pos = posRange(r);
    ...
    if (spring) return "Spring";
    if (entry && pos >= 0.72 && vol >= 1.3) {
      if (streakBeli(entry)) return "Markup";
      if (dominanJual(entry)) return "Distribusi";
    }
    if (pos >= 0.72 && vol >= 1.3 && (dA < 0 || dI < 0)) return "Distribusi";
    ...
```

Tambah ke `return {...}` SP: `detectFase: detectFase, streakBeli: streakBeli, dominanJual: dominanJual,`

- [ ] **Step 4: Run test to verify it passes**

Run: `node tests/test-markup.js`
Expected: 5 baris OK. Jika harness stub gagal total saat init (error selain streakBeli), sederhanakan stub sampai 5 cek di atas hijau; jangan ubah kode produksi untuk meloloskan harness.

Run: `node -e "const fs=require('fs'); const h=fs.readFileSync('web/screener-praktis.html','utf8'); const s=[...h.matchAll(/<script>([\s\S]*?)<\/script>/g)][0][1]; new (require('vm').Script)(s); console.log('syntax OK');"`
Expected: syntax OK

- [ ] **Step 5: Commit**

```bash
git add web/screener-praktis.html tests/test-markup.js
git commit -m "feat: wasit broker untuk Markup vs Distribusi"
```

### Task 2: Threading scope via build + lunakkan sMom Markup

**Files:**
- Modify: `web/screener-praktis.html` `build()` (~855), 3 call sites (`~1534`, `~1753`, `~1890`), `skor()` (~766-767), `skorTF()` (~827)
- Test: `tests/test-markup.js` (tambah 2 cek), `tests/test-harian.py`, `tests/_smoke-ui.py`

**Interfaces:**
- Consumes: `streakBeli(entry)` dari Task 1; `S.scope.emiten` di call sites (bentuk `{KODE: entry}`)
- Produces: `build(rows, ksei, fundMap, scopeMap)` dengan `scopeMap` opsional; record `.fase` Markup untuk runner+streak; `sMom` lunak untuk Markup+streak

- [ ] **Step 1: Write the failing test**

Tambah di `tests/test-markup.js` sebelum baris cek terakhir:

```js
const rRun = { s_springlow: 100, s_resistance: 200, harga: 190,
  s_vol_ratio: 2.0, s_spring: 0, s_sideways: 0, s_closeabove: 1,
  high_52: 200, ret20: 25, laba: 100, der: 0.5, eps_trend: "fluktuatif" };
const valMid = { mos: 10, roe: 10, intrinsic: 200 };
const built = SP.build([Object.assign({ kode: "TST", nama: "T", sektor: "S" }, rRun)],
  {}, {}, { TST: entryStreak() });
console.log("build-markup:", built[0].fase === "Markup" ? "OK" : "FAIL:" + built[0].fase);
const sc = SP.skorTF(rRun, {}, "Markup", valMid, "bulan");
console.log("smom-lunak:", sc >= 1 ? "OK-nilai-" + sc : "FAIL");
```

(Catatan: `build` butuh `valuasi(r, fund)` — record uji memakai field yang dipakai `valuasi`; jika throw karena field kurang, lengkapi field record uji dari kebutuhan `valuasi`, jangan ubah `valuasi`.)

- [ ] **Step 2: Run test to verify it fails**

Run: `node tests/test-markup.js`
Expected: FAIL pada `build-markup` (fase masih Distribusi karena scopeMap diabaikan)

- [ ] **Step 3: Write minimal implementation**

`build` terima peta scope dan teruskan entry + flag streak:

```js
  function build(rows, ksei, fundMap, scopeMap) {
    ksei = ksei || {};
    fundMap = fundMap || {};
    scopeMap = scopeMap || {};
    return rows.map(function (r) {
      var kode = String(r.kode || "").trim().toUpperCase();
      var k = ksei[kode] || {};
      var val = valuasi(r, fundMap[kode]);
      var entry = scopeMap[kode] || null;
      var fase = detectFase(r, k, entry);
      var streak = (fase === "Markup") && streakBeli(entry);
      var sc = skor(r, k, fase, val, streak);
      ...
```

`skor(r, k, fase, val, streakOk)` — lunakkan hanya bila Markup+streak:

```js
    var sMom = (r.ret20 == null || r.ret20 === "") ? 50
             : clamp(50 - toNum(r.ret20) * 4, 0, 100);
    if (fase === "Markup" && streakOk) {
      sMom = (r.ret20 == null || r.ret20 === "") ? 50
           : clamp(50 - toNum(r.ret20) * 2, 20, 100);
    }
```

Terapkan blok yang sama persis di `skorTF()` (baris ~827). Parameter `streakOk` di `skorTF(r, k, fase, val, tf, streakOk)`; pemanggil `skorTF` yang sudah ada (render/export: `SP.skorTF(x.r, x.k, x.fase, x.val, tf)`) tetap jalan karena parameter opsional (undefined = falsy = rumus lama).

3 call sites `build`: tambah argumen ke-4 `(S.scope.emiten || {})`:
- rebuild: `SP.build(S._csvRows || [], S.ksei, S.fund.emiten || {}, S.scope.emiten || {})`
- 2 call sites drawer (`SP.build([j.saham], m, ...)` dan `SP.build([o.j.saham], m, ...)`): tambah `S.scope.emiten || {}`.

- [ ] **Step 4: Run test to verify it passes**

Run: `node tests/test-markup.js`
Expected: semua cek OK termasuk build-markup dan smom

Run: `python tests/test-harian.py`
Expected: 4 passed

Run: `python tests/_smoke-ui.py`
Expected: semua OK seperti baseline

- [ ] **Step 5: Commit**

```bash
git add web/screener-praktis.html tests/test-markup.js
git commit -m "feat: sMom lunak untuk Markup terkonfirmasi broker"
```

### Task 3: Bonus likuiditas kandang bandar (500jt–3M)

**Files:**
- Modify: `web/screener-praktis.html` `skor()` (~sTiming clamp), `skorTF()` (~sTiming clamp)
- Test: `tests/test-markup.js` (tambah 1 cek)

**Interfaces:**
- Consumes: `r.nilai_harian` (estimasi value harian Rp, sudah ada di record)
- Produces: `+8 sTiming` bila 500jt ≤ nilai_harian ≤ 3M, sebelum clamp 0–100

- [ ] **Step 1: Write the failing test**

```js
const rLiquid = Object.assign({}, rRun, { nilai_harian: 1000000000 });
const rBig = Object.assign({}, rRun, { nilai_harian: 50000000000 });
const scLiq = SP.skorTF(rLiquid, {}, "Netral", valMid, "bulan");
const scBig = SP.skorTF(rBig, {}, "Netral", valMid, "bulan");
console.log("bonus-liquid:", scLiq > scBig ? "OK" : "FAIL:" + scLiq + "vs" + scBig);
```

(Syarat: `SP` mengekspos `skorTF` — tambah `skorTF: skorTF` ke `return {...}` SP bila belum ada. `rRun`/`valMid` dari Task 2 dengan `s_sideways: 0` agar bonus sideways tidak mengotori perbandingan; `ret20` sama di keduanya agar sMom identik.)

- [ ] **Step 2: Run test to verify it fails**

Run: `node tests/test-markup.js`
Expected: FAIL pada bonus-liquid (skor sama)

- [ ] **Step 3: Write minimal implementation**

Di `skor()` dan `skorTF()`, tepat sebelum `sTiming = clamp(sTiming, 0, 100);`:

```js
    var nh = toNum(r.nilai_harian);
    if (nh >= 500000000 && nh <= 3000000000) sTiming += 8;
```

Dua lokasi (fungsi `skor` ~baris 759 dan `skorTF` ~baris 823). Tidak ada perubahan lain.

- [ ] **Step 4: Run test to verify it passes**

Run: `node tests/test-markup.js`
Expected: semua cek OK

Run: `python tests/test-harian.py` dan `python tests/_smoke-ui.py`
Expected: hijau seperti baseline

- [ ] **Step 5: Commit**

```bash
git add web/screener-praktis.html tests/test-markup.js
git commit -m "feat: bonus timing untuk likuiditas kandang bandar"
```

### Task 4: Aksi Markup Beli bersyarat + verifikasi akhir

**Files:**
- Modify: `web/screener-praktis.html` `aksi()` (~783), `aksiTF()` cabang kilat (~838-841)
- Test: `tests/test-markup.js` (tambah 3 cek), verifikasi manual browser

**Interfaces:**
- Consumes: `fase === "Markup"`, `sc`, `val.mos` — tidak ada input baru
- Produces: aksi "Beli" untuk Markup bila `sc >= 60 && val.mos > -15`, selain itu "Pantau"

- [ ] **Step 1: Write the failing test**

```js
console.log("aksi-markup-beli:", SP.aksiTF("Markup", 65, { mos: 10 }, 0.8, null, "bulan", {}) === "Beli" ? "OK" : "FAIL");
console.log("aksi-markup-mahal:", SP.aksiTF("Markup", 65, { mos: -20 }, 0.8, null, "bulan", {}) === "Pantau" ? "OK" : "FAIL");
console.log("aksi-markup-rendah:", SP.aksiTF("Markup", 55, { mos: 10 }, 0.8, null, "bulan", {}) === "Pantau" ? "OK" : "FAIL");
```

(Cek dulu `SP` mengekspos `aksiTF`; jika belum, tambah `aksiTF: aksiTF` (dan `aksi: aksi`, `skorTF: skorTF` bila perlu) ke `return {...}` SP — itu bagian implementasi yang sah.)

- [ ] **Step 2: Run test to verify it fails**

Run: `node tests/test-markup.js`
Expected: FAIL pada aksi-markup-beli (aturan lama butuh pos < 0.55)

- [ ] **Step 3: Write minimal implementation**

Di `aksi()` ganti syarat Markup lama menjadi:

```js
    if (fase === "Markup") return (sc >= 60 && val.mos > -15) ? "Beli" : "Pantau";
```

Cabang `bulan`/`minggu` di `aksiTF()` jatuh ke `aksi()` generik (baris 843), jadi otomatis ikut tanpa perubahan. Di `aksiTF()` cabang kilat selaraskan batas kemahalan:

```js
    if (tf === "kilat") {
      if (extra.isLockH0) return "Pantau";
      if (fase !== "Markup") return "Pantau";
      return sc >= 60 ? "Beli" : "Pantau";
```

menjadi versi yang juga menghormati batas kemahalan:

```js
    if (tf === "kilat") {
      if (extra.isLockH0) return "Pantau";
      if (fase !== "Markup") return "Pantau";
      return (sc >= 60 && val.mos > -15) ? "Beli" : "Pantau";
```

(Cabang `bulan`/`minggu` di `aksiTF` memanggil `aksi()` generik di baris 843, jadi otomatis ikut tanpa perubahan. Satu sumber logika, tanpa duplikasi.)

- [ ] **Step 4: Run test to verify it passes**

Run: `node tests/test-markup.js`
Expected: semua cek OK

Run: `python tests/test-harian.py` dan `python tests/_smoke-ui.py`
Expected: hijau seperti baseline

Manual (wajib): Reload app → Download Data → cari runner (ret20 tinggi + streak broker) → pastikan fase Markup dan aksi Beli bila syarat terpenuhi; tanpa scope, fase sama seperti sebelum perubahan.

- [ ] **Step 5: Commit**

```bash
git add web/screener-praktis.html tests/test-markup.js
git commit -m "feat: aksi Markup Beli bersyarat skor>=60 mos>-15"
```
