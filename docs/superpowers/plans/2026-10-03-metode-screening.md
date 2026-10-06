# Metode Screening Preset Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tambah dropdown preset metode (Sideways, Contraction/VCP, Spring, Breakout) sebagai filter tampilan di screener.

**Architecture:** Filter murni di frontend dalam satu file `web/screener-praktis.html`; fungsi murni `SP.matchMetode` diisolasi agar kelak bisa diganti skor backend tanpa ubah UI.

**Tech Stack:** Vanilla JS satu file HTML (tanpa CDN), Node smoke test `tests/_test-praktis.js`, Python backend tidak disentuh.

## Global Constraints

- Satu file offline tanpa CDN — tidak tambah dependensi eksternal.
- Jangan ubah `detectFase`, `valuasi`, `skor`, `aksi`, kalibrasi horizon 3 bulan.
- Semua akses angka via `SP.toNum()` agar CSV kosong tidak menghasilkan NaN.
- Warna naik = merah turun = hijau; bukan nasihat investasi (tidak tambah klaim janji).
- Ekspor CSV tidak diubah (tetap seluruh `S.data`).

---

### Task 1: Tambah uji gagal untuk SP.matchMetode

**Files:**
- Modify: `tests/_test-praktis.js` (tambah blok 8, setelah blok 7, sebelum `console.log(gagal ...`)
- Test: `tests/_test-praktis.js`

**Interfaces:**
- Consumes: `SP.build`, `SP.toNum`, `SP.posRange` (sudah ada di `web/screener-praktis.html:200-267`)
- Produces: kontrak yang harus dipenuhi Task 2 — `SP.METODE` (array string) dan `SP.matchMetode(x, nama)` (function → boolean), di mana `x` = record hasil `SP.build()` dengan bentuk `{ r, k, fase, pos }`

- [ ] **Step 1: Tambah blok uji yang gagal**

Di `tests/_test-praktis.js`, setelah blok `// 7) horizon ...` (sebelum baris `console.log(gagal`), sisipkan blok ini persis:

```js
// 8) preset metode screening (frontend-only filter)
{
  cek("METODE tersedia (4 preset)", Array.isArray(SP.METODE) && SP.METODE.length === 4, String(SP.METODE));
  const bSide = { kode: "SIDE", nama: "Side", r: { harga: "1000", s_sideways: "1", s_vol_ratio: "0.7", s_spring: "0", s_closeabove: "1", s_springlow: "950", s_resistance: "1050" }, k: {}, fase: "Akumulasi", pos: 0.3 };
  const bSpring = { kode: "SPR", nama: "Spr", r: { harga: "1000", s_sideways: "0", s_vol_ratio: "1.0", s_spring: "1", s_closeabove: "1", s_springlow: "950", s_resistance: "1050" }, k: {}, fase: "Spring", pos: 0.2 };
  const bBreak = { kode: "BRK", nama: "Brk", r: { harga: "1000", s_sideways: "0", s_vol_ratio: "1.4", s_spring: "0", s_closeabove: "1", s_springlow: "900", s_resistance: "1050" }, k: {}, fase: "Markup", pos: 0.8 };
  const bCont = { kode: "CTC", nama: "Ctc", r: { harga: "1000", s_sideways: "0", s_vol_ratio: "0.9", s_spring: "0", s_closeabove: "1", s_springlow: "900", s_resistance: "1050" }, k: {}, fase: "Netral", pos: 0.5 };
  cek("matchMetode ada", typeof SP.matchMetode === "function");
  cek("sideways lolos Sideways", SP.matchMetode(bSide, "Sideways Dry-Out") === true);
  cek("sideways tidak lolos Breakout", SP.matchMetode(bSide, "Breakout Markup") === false);
  cek("spring lolos Spring", SP.matchMetode(bSpring, "Spring / Shakeout") === true);
  cek("breakout lolos Breakout", SP.matchMetode(bBreak, "Breakout Markup") === true);
  cek("kontraksi lolos Contraction", SP.matchMetode(bCont, "Contraction (VCP)") === true);
  cek("Semua lolos semua", SP.matchMetode(bSide, "Semua") === true);
}
```

- [ ] **Step 2: Jalankan uji untuk pastikan gagal**

Run: `node tests/_test-praktis.js`
Expected: GAGAL pada "METODE tersedia (4 preset)" dan "matchMetode ada" (karena `SP.METODE` / `SP.matchMetode` belum ada → `undefined`), uji lama lain tetap OK.

- [ ] **Step 3: Commit uji gagal**

```bash
git add tests/_test-praktis.js
git commit -m "test: tambah uji preset metode screening (gagal dulu)"
```

Catatan: repo saat ini bukan git repository; bila `git` gagal dengan "not a git repository", lewati commit dan lanjut — jangan inisialisasi repo baru.

### Task 2: Implementasi SP.METODE + SP.matchMetode

**Files:**
- Modify: `web/screener-praktis.html` (modul `SP`, sekitar `posRange` baris 263-267 dan blok `return` baris 423-429)
- Test: `tests/_test-praktis.js`

**Interfaces:**
- Consumes: `SP.toNum`, `x.r` (field `s_sideways`, `s_vol_ratio`, `s_spring`, `s_closeabove`), `x.pos` (0..1 dari `posRange`)
- Produces: `SP.METODE` (array 4 string) dan `SP.matchMetode(x, nama)` → boolean; dipakai Task 3 di `render()`

- [ ] **Step 1: Tambah konstanta dan fungsi murni setelah `detectFase`**

Buka `web/screener-praktis.html`, temukan akhir fungsi `detectFase` (baris ~285, sebelum `// ---------- valuasi sederhana`). Sisipkan persis blok ini:

```js
  // ---------- preset metode screening (filter tampilan saja) ----------
  var METODE = ["Sideways Dry-Out", "Contraction (VCP)", "Spring / Shakeout", "Breakout Markup"];

  function matchMetode(x, nama) {
    if (!nama || nama === "Semua") return true;
    var r = (x && x.r) || {};
    var pos = (x && x.pos != null) ? x.pos : posRange(r);
    var sideways = toNum(r.s_sideways) === 1;
    var spring = toNum(r.s_spring) === 1;
    var above = toNum(r.s_closeabove) === 1;
    var vr = toNum(r.s_vol_ratio) || 1.0;
    if (nama === "Sideways Dry-Out") return sideways && vr < 1.0 && !spring;
    if (nama === "Spring / Shakeout") return spring;
    if (nama === "Breakout Markup") return above && pos >= 0.50 && vr >= 1.1;
    if (nama === "Contraction (VCP)") return !sideways && above && !spring && vr < 1.1 && pos >= 0.25 && pos <= 0.70;
    return true;
  }
```

- [ ] **Step 2: Ekspor dari modul SP**

Temukan blok `return {` di akhir modul `SP` (baris ~423: `return { toNum: toNum, parseCSV...`). Ubah menjadi:

```js
  return {
    toNum: toNum, parseCSV: parseCSV, ingestKsei: ingestKsei, nf: nf, pct: pct,
    posRange: posRange, detectFase: detectFase, valuasi: valuasi,
    skor: skor, aksi: aksi, build: build,
    METODE: METODE, matchMetode: matchMetode,
    KALIBRASI: KALIBRASI, expiryKontrak: expiryKontrak, statusKontrak: statusKontrak,
    umurFase: umurFase, tanggalIndo: tanggalIndo
  };
```

Hanya dua baris berubah: tambah `METODE: METODE, matchMetode: matchMetode,`. Jangan ubah sisa return.

- [ ] **Step 3: Jalankan uji sampai lolos**

Run: `node tests/_test-praktis.js`
Expected: PASS — "Semua uji lulus", termasuk 7 cek baru blok 8.

- [ ] **Step 4: Cek sintaks HTML**

Run: `node -e "const fs=require('fs');const h=fs.readFileSync('web/screener-praktis.html','utf8');const m=[...h.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)].map(x=>x[1]).reduce((a,b)=>a.length>b.length?a:b);require('fs').writeFileSync('.tmp-check.js',m);require('child_process').execSync('node --check .tmp-check.js',{stdio:'inherit'});require('fs').unlinkSync('.tmp-check.js');console.log('syntax OK')"`
Expected: `syntax OK` tanpa error.

- [ ] **Step 5: Commit**

```bash
git add web/screener-praktis.html
git commit -m "feat: tambah SP.METODE dan matchMetode untuk preset screening"
```

Bila bukan git repo, lewati commit.

### Task 3: Dropdown UI + integrasi render + persist

**Files:**
- Modify: `web/screener-praktis.html` (toolbar baris ~141-145, state `S` baris ~436, `render()` baris ~553-567, init baris ~954)
- Test: `tests/_test-praktis.js` (tambah 3 cek string HTML) + uji manual browser

**Interfaces:**
- Consumes: `SP.METODE`, `SP.matchMetode` dari Task 2; pola persist mengikuti `sp_horizon`/`sp_kontrak` yang sudah ada
- Produces: UI selesai — tidak ada konsumen lanjutan

- [ ] **Step 1: Tambah 3 cek string HTML ke uji**

Di `tests/_test-praktis.js` blok 7 (deretan `cek("banner horizon...` dst), tambahkan 3 baris ini persis setelah baris `cek("kontrak: sp_kontrak...`:

```js
  cek("dropdown metode ada di toolbar", html.includes('id="metode"') && html.includes("Sideways Dry-Out"));
  cek("render memakai matchMetode", html.includes("S.metode") && html.includes("matchMetode"));
  cek("pilihan metode dipersist", html.includes("sp_metode"));
```

- [ ] **Step 2: Jalankan uji untuk pastikan 3 cek baru gagal**

Run: `node tests/_test-praktis.js`
Expected: FAIL tepat pada 3 cek baru di atas; semua cek lama PASS.

- [ ] **Step 3: Tambah dropdown di toolbar**

Temukan blok toolbar (baris ~141-145):

```html
    <div class="toolbar">
      <input class="search" id="q" placeholder="Cari kode / nama…">
      <div class="chips" id="chips"></div>
      <span class="cnt" id="cnt">0 saham</span>
    </div>
```

Ubah menjadi (sisipkan select sebelum search, reuse class `mini-sel` yang sudah ada di CSS baris ~99):

```html
    <div class="toolbar">
      <select class="mini-sel" id="metode" title="Preset metode screening — digabung dengan filter fase">
        <option value="Semua">Semua Metode</option>
        <option value="Sideways Dry-Out">Sideways Dry-Out</option>
        <option value="Contraction (VCP)" title="Pendekatan untuk Scan Pasar (tanpa riwayat multi-minggu)">Contraction (VCP ≈)</option>
        <option value="Spring / Shakeout">Spring / Shakeout</option>
        <option value="Breakout Markup">Breakout Markup</option>
      </select>
      <input class="search" id="q" placeholder="Cari kode / nama…">
      <div class="chips" id="chips"></div>
      <span class="cnt" id="cnt">0 saham</span>
    </div>
```

- [ ] **Step 4: Tambah state dan filter di render**

Temukan deklarasi state (baris ~436):

```js
  var S = { data: [], ksei: {}, pasar: null, sortKey: "skor", sortDir: -1, filter: "Semua", q: "" };
```

Ubah menjadi:

```js
  var S = { data: [], ksei: {}, pasar: null, sortKey: "skor", sortDir: -1, filter: "Semua", q: "", metode: "Semua" };
```

Temukan awal `function render()` (baris ~553):

```js
  function render() {
    var d = S.data.slice();
    if (S.filter !== "Semua") d = d.filter(function (x) { return x.fase === S.filter; });
```

Ubah menjadi:

```js
  function render() {
    var d = S.data.slice();
    if (S.filter !== "Semua") d = d.filter(function (x) { return x.fase === S.filter; });
    if (S.metode && S.metode !== "Semua") d = d.filter(function (x) { return SP.matchMetode(x, S.metode); });
```

Satu baris tambahan, AND dengan filter fase. Jangan ubah sort, search, atau counter.

- [ ] **Step 5: Tambah event persist dan init**

Temukan handler `$("q").oninput = ...` (baris ~913). Tepat sebelumnya, sisipkan:

```js
  try { S.metode = localStorage.getItem("sp_metode") || "Semua"; } catch (e) { S.metode = "Semua"; }
  if (SP.METODE.indexOf(S.metode) < 0) S.metode = "Semua";
  $("metode").value = S.metode;
  $("metode").onchange = function () {
    S.metode = this.value;
    try { localStorage.setItem("sp_metode", S.metode); } catch (e) {}
    render();
  };
```

Pola try/catch mengikuti `sp_horizon`/`sp_kontrak` yang sudah ada. Nilai select memakai `value` exact dari `SP.METODE` plus `"Semua"`.

- [ ] **Step 6: Jalankan uji sampai lolos**

Run: `node tests/_test-praktis.js`
Expected: PASS — "Semua uji lulus".

- [ ] **Step 7: Uji manual browser (wajib sebelum selesai)**

1. Buka via `Jalankan Screener.vbs` (atau `python app/app-screener.py`), klik **Muat Contoh**.
2. Pilih tiap opsi dropdown satu per satu; pastikan tabel menyusut/berubah dan counter `X dari N saham` update.
3. Kombinasikan Fase=Akumulasi + Metode=Sideways Dry-Out; pastikan hasil = irisan.
4. Reload halaman; pastikan pilihan dropdown awet (`sp_metode`).
5. Klik **Scan Seluruh Pasar** (bila ada internet); pastikan tidak error dan opsi Contraction tampilkan label `≈`.

- [ ] **Step 8: Commit**

```bash
git add web/screener-praktis.html tests/_test-praktis.js
git commit -m "feat: dropdown preset metode screening + filter render"
```

Bila bukan git repo, lewati commit.
