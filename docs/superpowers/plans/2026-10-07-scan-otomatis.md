# Scan Otomatis Isi Kas + Rekomendasi Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Klik Scan Seluruh Pasar otomatis mengisi data kas Thowilz (tanpa download manual) untuk emiten paling likuid, memakai cache 30 hari, lalu menampilkan strip rekomendasi top-5.

**Architecture:** Setelah scan selesai: overlay cache kas `localStorage sp_kas` (TTL 30 hari) → auto-fetch yang masih kosong top likuid (`AUTO_LENGKAPI = 60`, reuse endpoint `/api/lengkapi` maks 40/call = 2 call) dengan progres di tombol → simpan hasil ke cache → `rebuild()` → strip rekomendasi top-5 `thowilz` (klik → drawer live). Isi penuh 845 TIDAK dilakukan (jujur: ~30 menit + rate-limit Yahoo).

**Tech Stack:** Vanilla JS + localStorage, endpoint Python existing tanpa perubahan, test via `node tests/_test-praktis.js`.

## Global Constraints

- Jangan ubah rumus `skor`, `aksi`, `valuasi`, filter, atau `/api/lengkapi` (maks 40/kirim tetap).
- `AUTO_LENGKAPI = 60` (2 call). Jangan naikkan tanpa persetujuan (waktu + rate-limit).
- Cache key `sp_kas`, TTL 30 hari, value per kode 12 field KAS + `t` (epoch ms).
- Rekomendasi = `thowilz > 0` tertinggi, tie-break `skor` tampilan; strip hanya tampil bila ≥1 ada.
- Mode download/watchlist tak berubah perilakunya (auto hanya jalan di `S.mode === "pasar"`).

---

### Task 1: Cache kas SP + terap otomatis

**Files:**
- Modify: `web/screener-praktis.html` (dalam IIFE `SP`, dekat `twBadge`)
- Test: `tests/_test-praktis.js` (blok 26)

**Interfaces:**
- Consumes: `rows` (array objek baris mentah), `cache` (map kode → `{t, v}`).
- Produces: `SP.kasTerap(rows, cache)->number` (murni, tanpa DOM/storage); `SP.kasLoad()->object`; `SP.kasSave(map)->void`; konstanta `SP.KAS_F` (12 nama field); `SP.AUTO_LENGKAPI = 60`.

- [ ] **Step 1: Write the failing test**

```js
// 26) cache kas + terap
{
  var rowsK = [{ kode: "AA", ev_cfo: "" }, { kode: "BB", ev_cfo: 5 }];
  var cacheK = { AA: { t: Date.now(), v: { ev_cfo: 7.5, cash_badge: "Watchlist", klasifikasi: "Cyclical", thowilz: 55 } } };
  cek("kas: terap isi yang kosong", SP.kasTerap(rowsK, cacheK) === 1 && rowsK[0].ev_cfo === 7.5 && rowsK[0].thowilz === 55);
  cek("kas: tidak timpa yang ada", rowsK[1].ev_cfo === 5);
  cek("kas: kadaluarsa ditolak", SP.kasTerap([{ kode: "CC", ev_cfo: "" }], { CC: { t: Date.now() - 31 * 864e5, v: { ev_cfo: 9 } } }) === 0);
  cek("kas: konstanta", SP.AUTO_LENGKAPI === 60 && SP.KAS_F.length === 12 && SP.KAS_F.indexOf("thowilz") >= 0);
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node tests/_test-praktis.js 2>&1 | Select-String "kas: |uji GAGAL"`
Expected: FAIL/crash `SP.kasTerap is not a function` + 4 GAGAL pre-existing.

- [ ] **Step 3: Write minimal implementation**

Di IIFE SP setelah `twKas`, tambah:

```js
  var KAS_F = ["ev_cfo", "ev_fcf", "peg_cfo", "cfo_cagr", "gross_margin", "margin_stabil", "capex_inten", "cfo3", "sloan", "cash_badge", "klasifikasi", "thowilz"];
  var KAS_TTL = 30 * 864e5, AUTO_LENGKAPI = 60;
  function kasTerap(rows, cache) {
    var n = 0;
    (rows || []).forEach(function (r) {
      if (!r || r.ev_cfo != null && r.ev_cfo !== "") return;
      var e = cache && cache[String(r.kode || "").toUpperCase()];
      if (!e || !e.v || !(e.t > Date.now() - KAS_TTL)) return;
      KAS_F.forEach(function (k) { if (e.v[k] !== undefined) r[k] = e.v[k]; });
      n++;
    });
    return n;
  }
  function kasLoad() { try { return JSON.parse(localStorage.getItem("sp_kas") || "{}"); } catch (e) { return {}; } }
  function kasSave(map) { try { localStorage.setItem("sp_kas", JSON.stringify(map || {})); } catch (e) {} }
```

Kondisi `r.ev_cfo != null && !== ""` → return (sudah ada) — operator precedence: `!r || (a && b)` — tulis eksplisit:

```js
      if (!r) return;
      if (r.ev_cfo != null && r.ev_cfo !== "") return;
```

Ekspor di return SP: `kasTerap: kasTerap, kasLoad: kasLoad, kasSave: kasSave, KAS_F: KAS_F, AUTO_LENGKAPI: AUTO_LENGKAPI,`.

- [ ] **Step 4: Run test to verify it passes**

Run: `node tests/_test-praktis.js 2>&1 | Select-String "kas: |uji GAGAL"`
Expected: 4 `OK kas:`, total GAGAL tetap 4 pre-existing.

- [ ] **Step 5: Commit**

```bash
git add web/screener-praktis.html tests/_test-praktis.js
git commit -m "feat: cache kas 30 hari + kasTerap"
```

### Task 2: Auto-lengkapi + strip rekomendasi

**Files:**
- Modify: `web/screener-praktis.html` (HTML `rekoTw`, handler scan, fungsi `lengkapiOtomatis`, `renderReko`)
- Test: `tests/_test-praktis.js` (blok 27 marker)

**Interfaces:**
- Consumes: `SP.kasLoad/kasSave/kasTerap/KAS_F/AUTO_LENGKAPI`, `/api/lengkapi`, `openDrawerLive`.
- Produces: strip `#rekoTw` + auto-fill berjalan tiap scan selesai (mode pasar saja).

- [ ] **Step 1: Write the failing test**

```js
// 27) auto + rekomendasi
{
  cek("reko: marker ada", html.indexOf('id="rekoTw"') >= 0 && html.indexOf("Rekomendasi Thowilz") >= 0 && html.indexOf("AUTO_LENGKAPI") >= 0 && html.indexOf("lengkapiOtomatis") >= 0);
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node tests/_test-praktis.js 2>&1 | Select-String "reko: "`
Expected: FAIL `GAGAL reko: marker ada`.

- [ ] **Step 3: Write minimal implementation**

1. HTML setelah `<div id="horizonWarn" class="hzw" hidden></div>` tambah:

```html
<div id="rekoTw" class="mut" style="padding:8px 15px;border-bottom:1px solid var(--line2)" hidden></div>
```

2. Setelah handler `$("btnLengkapi").onclick = ...` (refaktor ringan): bungkus isi fetch-merge jadi fungsi bernama agar dipakai ulang:

```js
  function kirimLengkapi(kodes, label) {
    return fetch("/api/lengkapi?kodes=" + encodeURIComponent(kodes.join(","))).then(function (r) { return r.json(); }).then(function (j) {
      if (!j || !j.ok) throw new Error((j && j.error) || "gagal melengkapi");
      var map = {};
      (j.saham || []).forEach(function (s) { map[String(s.kode || "").toUpperCase()] = s; });
      var cache = SP.kasLoad(), n = 0;
      (S._csvRows || []).forEach(function (r) {
        var s = map[String(r.kode || "").toUpperCase()];
        if (!s) return;
        var v = {};
        SP.KAS_F.forEach(function (k) { if (s[k] !== undefined) { r[k] = s[k]; v[k] = s[k]; } });
        cache[String(r.kode).toUpperCase()] = { t: Date.now(), v: v };
        n++;
      });
      SP.kasSave(cache);
      return n;
    });
  }
```

Handler btnLengkapi memanggilnya per batch 40 (loop promise berantai, progres "Melengkapi i/N…"). Tulis handler manual sebagai:

```js
  $("btnLengkapi").onclick = function () { lengkapiManual(); };
  function lengkapiManual() {
    if (!APP) { toast("Buka aplikasi dulu: klik dua kali 'Jalankan Screener'"); return; }
    var b = $("btnLengkapi"), asli = b.textContent;
    var kosong = (S._csvRows || []).filter(function (r) { return r && (r.ev_cfo == null || r.ev_cfo === ""); });
    kosong.sort(function (a, c) { return SP.toNum(c.nilai_harian) - SP.toNum(a.nilai_harian); });
    var kodes = kosong.map(function (r) { return String(r.kode || "").toUpperCase(); }).filter(Boolean);
    if (!kodes.length) { toast("Semua baris sudah ada data kas."); return; }
    b.disabled = true;
    var done = 0, chain = Promise.resolve();
    for (var i = 0; i < kodes.length; i += 40) {
      (function (batch) {
        chain = chain.then(function () {
          b.textContent = "Melengkapi " + (done + 1) + "-" + Math.min(done + batch.length, kodes.length) + "/" + kodes.length + "…";
          return kirimLengkapi(batch).then(function (n) { done += n; });
        });
      })(kodes.slice(i, i + 40));
    }
    chain.then(function () { rebuild(); renderReko(); toast("Data kas dilengkapi: " + done + " emiten."); })
      .catch(function (e) { toast("Gagal: " + (e && e.message ? e.message : e)); })
      .then(function () { b.disabled = false; b.textContent = asli; });
  }
```

HAPUS handler btnLengkapi lama (ganti total — jangan dobel).

3. Auto setelah scan: di `.then` scan-complete (setelah `rebuild()` pertama), sisipkan SEBELUM toast akhir:

```js
        var cache0 = SP.kasLoad();
        var dariCache = SP.kasTerap(S._csvRows, cache0);
        rebuild();
        renderReko();
```

lalu jika `S.mode === "pasar"`, panggil auto top-60:

```js
        if (S.mode === "pasar") {
          var kosong2 = (S._csvRows || []).filter(function (r) { return r && (r.ev_cfo == null || r.ev_cfo === ""); });
          kosong2.sort(function (a, c) { return SP.toNum(c.nilai_harian) - SP.toNum(a.nilai_harian); });
          var auto = kosong2.slice(0, SP.AUTO_LENGKAPI).map(function (r) { return String(r.kode || "").toUpperCase(); }).filter(Boolean);
          if (auto.length) {
            toast("Melengkapi kas " + auto.length + " emiten terlikuid…");
            var c2 = Promise.resolve(), dd = 0;
            for (var ii = 0; ii < auto.length; ii += 40) {
              (function (bt) { c2 = c2.then(function () { return kirimLengkapi(bt).then(function (n) { dd += n; }); }); })(auto.slice(ii, ii + 40));
            }
            c2.then(function () { rebuild(); renderReko(); toast("Kas terisi: " + dd + " emiten (cache 30 hari)."); })
              .catch(function (e) { toast("Lengkapi terhenti: " + (e && e.message ? e.message : e)); });
          }
        }
```

4. Strip rekomendasi:

```js
  function renderReko() {
    var el = $("rekoTw");
    if (!el) return;
    var ada = (S.data || []).filter(function (x) { return SP.toNum(x.r.thowilz) > 0; });
    if (!ada.length) { el.hidden = true; el.innerHTML = ""; return; }
    ada.sort(function (a, b) { return SP.toNum(b.r.thowilz) - SP.toNum(a.r.thowilz) || ((b._scD != null ? b._scD : b.skor) - (a._scD != null ? a._scD : a.skor)); });
    var top = ada.slice(0, 5);
    el.innerHTML = "<b>Rekomendasi Thowilz:</b> " + top.map(function (x, i) {
      return '<button class="btn sm" data-reko="' + x.kode + '" title="skor ' + SP.toNum(x.r.thowilz) + "/100 · " + SP.twKas(x.r.cash_badge) + '">' + (i + 1) + ". " + x.kode + " (" + SP.toNum(x.r.thowilz) + ")</button>";
    }).join(" ");
    el.hidden = false;
  }
```

Delegasi klik (tambah di dekat `tbl.tBodies[0].onclick`):

```js
  $("rekoTw").onclick = function (e) {
    var b = e.target.closest("[data-reko]"); if (!b) return;
    openDrawerLive(b.getAttribute("data-reko"));
  };
```

Panggil `renderReko()` di akhir `render()` agar strip selaras filter (tambah satu baris sebelum `renderCek();`).

- [ ] **Step 4: Run test to verify it passes**

Run: `node tests/_test-praktis.js 2>&1 | Select-String "reko: |kas: |uji GAGAL"`
Expected: semua OK baru, total GAGAL tetap 4 pre-existing. Plus `node --check` via pola existing (test sudah mencakup sintaks).

- [ ] **Step 5: Commit**

```bash
git add web/screener-praktis.html tests/_test-praktis.js
git commit -m "feat: scan otomatis isi kas + rekomendasi top-5"
```

### Task 3: Verifikasi

- [ ] **Step 1: Suite penuh** (`test-cash-quality`, `test-harian`, `_test-cash-ui`, `_test-praktis`) — harap hijau kecuali 4 pre-existing.
- [ ] **Step 2: Simulasi cache offline (node satu baris, tanpa browser):**

```bash
node -e "var fs=require('fs');var h=fs.readFileSync('web/screener-praktis.html','utf8');var m=h.match(/var SP = \(function \(\) \{[\s\S]*?\n\}\)\(\);/);var SP=new Function(m[0]+'; return SP;')();var rows=[{kode:'AA',ev_cfo:''}];var n=SP.kasTerap(rows,{AA:{t:Date.now(),v:{ev_cfo:7.5,cash_badge:'Watchlist',klasifikasi:'Cyclical',thowilz:55}}});console.log('terisi:'+n+' ev:'+rows[0].ev_cfo+' skor:'+rows[0].thowilz)"
```

Harap: `terisi:1 ev:7.5 skor:55`.

## Self-Review

- Spec coverage: auto-isi tanpa download ✓ (top likuid + cache); rekomendasi terbaik ✓ (strip top-5 + drawer); batas jujur 845 didokumentasikan di plan + banner (bukan janji palsu).
- Placeholder scan: semua kode aktual; tidak ada TBD.
- Type consistency: `kasTerap` murni (rows, cache) — handler storage terpisah; `AUTO_LENGKAPI`/`KAS_F` di SP dan dipakai handler via `SP.`; `renderReko` baca `x.r.thowilz` konsisten dengan kolom.
