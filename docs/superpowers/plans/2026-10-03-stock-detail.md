# Detail On-Demand per Klik Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Klik saham → drawer loading → laporan segar dari semua sumber via `GET /api/stock`.

**Architecture:** Route baru reuse `ambil_emiten`/scope/fund/IP (dengan perbaikan clobber-cache) + frontend refactor `openDrawer` → `isiDrawer(x)` + `openDrawerLive(kode)`.

**Tech Stack:** Python stdlib, vanilla JS, Node smoke test.

## Global Constraints

- Tiap sumber best-effort + log; Yahoo gagal total → 502; lainnya gagal → fallback.
- Tanpa menulis cache watchlist/config; cache disk scope/fund BOLEH refresh (konsisten Download).
- Loading jujur indeterminasi; tanpa checklist/progres palsu.
- Tanpa ubah skor/fase/aturan/kalibrasi; tanpa kolom baru; tanpa rebuild `.exe`.

---

### Task 1: Backend `GET /api/stock` (+ 3 perbaikan kecil)

**Files:** Modify `app/app-screener.py`, `scripts/fetch-sahamscope.py` (flag `tulis_cache`), `scripts/fetch-fund-gabungan.py` (`ambil_semua` merge-preserving).

**Interfaces:** Consumes existing fetchers. Produces `GET /api/stock?kode=X` → `{ok, diambil, saham, k, scopeEntry, fundEntry, wajar}`.

- [ ] **Step 1: Perbaikan clobber-cache (2 edit kecil)**

(a) `fetch-sahamscope.py` `ambil_scope(kodes, log_fn=None, delay=1.0, hari=30)` → tambah param `tulis_cache=True`; bungkus tulis berkas dengan `if tulis_cache:`.
(b) `fetch-fund-gabungan.py` `ambil_semua`: sebelum tulis, baca dulu berkas cache yang ada dan gabung: `lama = json.load(...) jika ada; lama["emiten"].update(baru); tulis gabungan` (diambil = sekarang).

- [ ] **Step 2: Ekstrak helper avg IndoPremier**

Di `muat_semua`, blok loop avg-broker IndoPremier (dari `say("Menambah avg broker...")` sampai `say("Avg broker IndoPremier...")`) pindahkan ke fungsi baru `ambil_ip(kodes)` mengembalikan `{kode: {avgB, avgS, topB, topS}}` (top = list kode terurut val). `muat_semua` memanggilnya dan menempel seperti sekarang (perilaku identik). Verifikasi: `python -m py_compile` + smoke hijau (shape respons Download tak berubah).

- [ ] **Step 3: Rute `/api/stock` (setelah `/api/fund`, sebelum `/favicon.ico`)**

```python
            if jalur == "/api/stock":
                q = parse_qs(u.query)
                kk = bersih_kode([q.get("kode", [""])[0]])
                if not kk:
                    return self._json({"ok": False, "error": "kode kosong."}, 400)
                kode = kk[0]
                recs = ambil_emiten([kode])
                if not recs:
                    return self._json({"ok": False, "error": "Gagal mengambil data %s." % kode}, 502)
                kmap = ((_cache.get("ksei") or {}).get("v") or {}).get("emiten", {}) or (_baca_json("ksei.json").get("emiten") or {})
                try:
                    sc = ambil_scope([kode], tulis_cache=False)
                    scopeEntry = (sc.get("emiten") or {}).get(kode, {})
                except Exception as e:
                    tulis_log("scope stock gagal: %s" % e); scopeEntry = {}
                fundEntry = {}
                try:
                    base = _baca_json("fund-gabungan.json")
                    if kode not in (base.get("emiten") or {}):
                        ff = load_mod("fetch_fund", "fetch-fund-gabungan.py")
                        base = ff.ambil_semua([kode], log_fn=lambda m: tulis_log("fund " + m.strip() if m else ""))
                    fundEntry = (base.get("emiten") or {}).get(kode, {})
                except Exception as e:
                    tulis_log("fund stock gagal: %s" % e)
                ipmap = {}
                try:
                    ipmap = ambil_ip([kode]).get(kode, {})
                except Exception as e:
                    tulis_log("ip stock gagal: %s" % e)
                if ipmap:
                    scopeEntry = dict(scopeEntry)
                    acc = dict(scopeEntry.get("acc") or {})
                    acc.update({"avgB": ipmap.get("avgB", {}), "avgS": ipmap.get("avgS", {}), "sumber": "IP"})
                    if not acc.get("top_buyers") and ipmap.get("topB"):
                        acc["top_buyers"] = [{"broker": b, "nval": 0} for b in ipmap["topB"]]
                    if not acc.get("top_sellers") and ipmap.get("topS"):
                        acc["top_sellers"] = [{"broker": b, "nval": 0} for b in ipmap["topS"]]
                    scopeEntry["acc"] = acc
                wajar = None
                try:
                    for t in (muat_tema().get("tema") or []):
                        if kode in (t.get("emiten") or {}) and (t.get("wajar") or {}).get(kode):
                            wajar = t["wajar"][kode]; break
                except Exception: pass
                return self._json({
                    "ok": True, "dibuat": datetime.now().astimezone().isoformat(timespec="seconds"),
                    "saham": recs[0], "k": kmap.get(kode, {}), "scopeEntry": scopeEntry,
                    "fundEntry": fundEntry, "wajar": wajar,
                })
```
(Catatan: `ambil_scope` wrapper app perlu teruskan `tulis_cache` — ubah signature wrapper menjadi `ambil_scope(kodes, tulis_cache=True)`. `muat_tema()` di rute bisa memicu scrape 10 halaman bila cache basi — terima (best-effort dalam try? `muat_tema` sudah best-effort internal kecuali scrape gagal total → `{}`; bungkus try juga — sudah di atas via try/except? Tambahkan try di sekitar loop wajar: sudah ada `try/except: pass` — baik.)

- [ ] **Step 4: Verifikasi**

`python -m py_compile`; server uji → `/api/stock` tanpa kode → 400; `?kode=!!!` → 400 (bersih_kode kosong); `?kode=BBCA` → 200 + kunci lengkap (butuh internet + kuota; parsial sah selama `saham`+`k` ada).

### Task 2: Frontend drawer live

**Files:** Modify `web/screener-praktis.html` (CSS `.loadbar`, refactor `isiDrawer`, `openDrawerLive`, umurSatu). Test: smoke + manual.

**Interfaces:** Consumes Task 1. Produces drawer segar per klik; tabel tak berubah.

- [ ] **Step 1: 3 cek string (gagal dulu)**

Blok 7 tambah:
```js
  cek("endpoint stock dipakai", html.includes("/api/stock"));
  cek("drawer live ada", html.includes("Mengambil laporan segar") && html.includes("muat ulang"));
  cek("loadbar ada", html.includes("loadbar"));
```

- [ ] **Step 2: Refactor `openDrawer` → `isiDrawer(x)` + `umurSatu`**

(a) CSS (dekat `.bar`): tambah `.loadbar{height:6px;background:#eef1f4;border-radius:99px;overflow:hidden;margin:12px 0}.loadbar>i{display:block;height:100%;width:40%;background:var(--accent);border-radius:99px;animation:lb 1s infinite alternate}@keyframes lb{from{margin-left:0}to{margin-left:60%}}`.
(b) Ekstrak helper umur (ganti isi `updateUmur` loop-body — perilaku identik):
```js
  function umurSatu(x, today) {
    var umur = {};
    try { umur = JSON.parse(localStorage.getItem("sp_umur") || "{}"); } catch (e) { umur = {}; }
    var rec = umur[x.kode];
    x.umurBaru = !rec || rec.f !== x.fase;
    if (x.umurBaru) umur[x.kode] = { f: x.fase, s: today };
    x.umurSejak = umur[x.kode].s;
    x.umurHari = SP.umurFase(x.umurSejak, today);
    try { localStorage.setItem("sp_umur", JSON.stringify(umur)); } catch (e) {}
  }
  function updateUmur() {
    var today = hariIni();
    S.data.forEach(function (x) { umurSatu(x, today); });
  }
```
(c) Ganti `function openDrawer(kode) {` + 2 baris lookup (`var x = ...filter...; if (!x) return;`) menjadi `function isiDrawer(x) {`, dan di akhir fungsi (sebelum penutup, setelah wiring kontrak) tambah:
```js
  function openDrawer(kode) {
    var x = S.data.filter(function (d) { return d.kode === kode; })[0];
    if (!x) return;
    isiDrawer(x);
    $("drawer").className = "drawer on";
  }
```
(Pindahkan baris `$("drawer").className = "drawer on";` dari badan lama ke openDrawer baru; badan lama jadi isiDrawer tanpa show.)
(d) Tambah setelah `openDrawer`:
```js
  function openDrawerLive(kode) {
    var lama = S.data.filter(function (d) { return d.kode === kode; })[0];
    $("dwTitle").textContent = kode + (lama ? " — " + lama.nama : "");
    $("dwSub").innerHTML = "";
    $("dwBody").innerHTML = '<div class="loadbar"><i></i></div><p class="mut">Mengambil laporan segar…</p>';
    $("drawer").className = "drawer on";
    fetch("/api/stock?kode=" + encodeURIComponent(kode)).then(function (r) {
      return r.json().then(function (j) { return { s: r.status, j: j }; });
    }).then(function (o) {
      if (!o.j || !o.j.ok) throw new Error((o.j && o.j.error) || "gagal");
      var j = o.j;
      S.ksei[kode] = j.k || {};
      S.scope.emiten = S.scope.emiten || {};
      if (j.scopeEntry && Object.keys(j.scopeEntry).length) S.scope.emiten[kode] = j.scopeEntry;
      S.fund.emiten = (S.fund.emiten || {});
      if (j.fundEntry && Object.keys(j.fundEntry).length) S.fund.emiten[kode] = j.fundEntry;
      var b = SP.build([j.saham], (function () { var m = {}; m[kode] = j.k || {}; return m; })())[0];
      if (!b) throw new Error("gagal membangun record");
      umurSatu(b, hariIni());
      var wj = j.wajar || null;
      var wjAsli = S.tema;
      if (wj) S._wajarOnce = S._wajarOnce || {}, S._wajarOnce[kode] = wj;
      isiDrawer(b);
      var hhmm = String(j.dibuat || "").slice(11, 16);
      $("dwSub").innerHTML += ' · <span class="mut">segar ' + hhmm + '</span> <button class="hzw-min" id="dwSegar">muat ulang</button>';
      var seg = $("dwSegar");
      if (seg) seg.onclick = function () { openDrawerLive(kode); };
    }).catch(function (e) {
      $("dwBody").innerHTML = '<div class="warn">Gagal mengambil laporan segar: ' + (e && e.message ? e.message : e) + '.</div><div class="ktl-aksi"><button class="btn pri" id="dwCoba">Coba lagi</button></div>';
      var cb = $("dwCoba");
      if (cb) cb.onclick = function () { openDrawerLive(kode); };
    });
  }
```
(Catatan `smBox` baca wajar dari `S.tema`: agar wajar sekali-pakai terbaca, ubah `smBox` 1 baris: `var wj = null;` → `var wj = (S._wajarOnce || {})[x.kode] || null;` lalu loop tema seperti sekarang bila masih null. Tambahkan di langkah ini.)
(e) Ganti pemanggil klik baris: `$("tbl").tBodies[0].onclick` memanggil `openDrawer(` → ganti `openDrawerLive(`. (Drawer contoh/impor tanpa server? Bila `!APP`, fetch gagal → error + coba lagi; lipat: di awal openDrawerLive, `if (!APP) { openDrawer(kode); return; }` — fallback cache.)

- [ ] **Step 3: Uji**

Smoke PASS (termasuk 3 baru). Manual: klik saham → loading → laporan + badge jam + muat ulang; offline → error + coba lagi; tabel tak berubah.
