# Download Detail Sementara Implementation Plan — DIBATALKAN

> Digantikan oleh `docs/superpowers/specs/2026-10-03-tambah-watchlist-design.md`
> (dicentang = append ke watchlist). Backend `/api/detail` yang sempat dibuat
> sudah di-revert. Dipertahankan sebagai arsip.

# Download Detail Sementara Implementation Plan (arsip)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Centang saham hasil Scan → checklist otomatis → Download Detail sementara tanpa mengubah watchlist tersimpan.

**Architecture:** `POST /api/detail` reuse `ambil_emiten`/`ambil_scope` tanpa menyentuh cache memori/disk config; frontend mode `pasar`/`detail`/`lain` mengendalikan kolom centang; state sementara di `S` saja.

**Tech Stack:** Python stdlib, vanilla JS satu file HTML, Node smoke test. Tanpa dependensi baru.

## Global Constraints

- Python hanya standard library.
- DILARANG menulis: `config.json`, `daftar-saham.txt`, cache memori `emiten`/`ksei`/`scope`, dan cache disk scope (param `tulis_cache=False`).
- Maks 30 kode; kosong → 400; GET → 404; gagal total → 502.
- Checklist hanya informasi (tidak memblokir); gagal syarat tetap bisa di-download.
- Tanpa rebuild `.exe` (launcher mode source).

---

### Task 1: Backend `POST /api/detail` (+ flag cache scope)

**Files:**
- Modify: `scripts/fetch-sahamscope.py` (`ambil_scope(..., tulis_cache=True)`), `app/app-screener.py` (`do_POST` branch `/api/detail`)
- Test: `python -m py_compile` + live HTTP ke server lokal + hash file config

**Interfaces:**
- Consumes: `ambil_emiten`, `ambil_scope`, `ambil_ksei`, `muat_tema`, `bersih_kode`, `_cache` (semua sudah ada; wrapper `ambil_scope(kodes, tulis_cache=True)` di app meneruskan flag ke modul)
- Produces: `POST /api/detail {kodes}` → `{ok, jumlah, ksei, saham, scope, tema, dibuat}`; dipakai Task 2.

- [ ] **Step 1: Tambah flag `tulis_cache` di `ambil_scope`**

Ubah signature:
```python
def ambil_scope(kodes, log_fn=None, delay=1.0, hari=30, tulis_cache=True):
```
Dan blok tulis berkas:
```python
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as fh:
            json.dump(hasil, fh, ensure_ascii=False)
    except OSError:
        pass
```
menjadi:
```python
    if tulis_cache:
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as fh:
                json.dump(hasil, fh, ensure_ascii=False)
        except OSError:
            pass
```

- [ ] **Step 2: Tambah branch `/api/detail` di `do_POST`**

Ubah:
```python
            if jalur != "/api/config":
                return self._json({"ok": False, "error": "rute tidak dikenal"}, 404)
            n = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(n) if n else b"{}"
            data = json.loads(raw.decode("utf-8-sig"))
            daftar = bersih_kode(data.get("daftar_saham"))
```
menjadi (sisipkan branch detail sebelum logika config):
```python
            if jalur != "/api/config" and jalur != "/api/detail":
                return self._json({"ok": False, "error": "rute tidak dikenal"}, 404)
            n = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(n) if n else b"{}"
            data = json.loads(raw.decode("utf-8-sig"))
            if jalur == "/api/detail":
                kodes = bersih_kode(data.get("kodes"))
                if not kodes:
                    return self._json({"ok": False, "error": "kodes kosong."}, 400)
                if len(kodes) > 30:
                    return self._json({"ok": False, "error": "maksimal 30 kode."}, 400)
                recs = ambil_emiten(kodes)
                if not recs:
                    return self._json({"ok": False, "error": "Gagal mengambil data (Yahoo)."}, 502)
                try:
                    scope = ambil_scope(kodes, tulis_cache=False)
                except Exception as e:  # noqa: BLE001
                    tulis_log("scope detail gagal: %s" % e)
                    scope = {}
                ksei = (_cache.get("ksei") or {}).get("v")
                if not ksei:
                    ksei = ambil_ksei()
                return self._json({
                    "ok": True, "jumlah": len(recs), "ksei": ksei or {}, "saham": recs,
                    "scope": scope or {}, "tema": muat_tema(),
                    "dibuat": datetime.now().astimezone().isoformat(timespec="seconds"),
                })
            daftar = bersih_kode(data.get("daftar_saham"))
```
(Catatan: `ambil_scope`/`muat_tema` adalah nama fungsi modul di file yang sama — tidak bentrok dengan variabel lokal `scope`/`tema` di branch ini.)

- [ ] **Step 3: Verifikasi sintaks**

Run:
```bash
python -m py_compile app/app-screener.py scripts/fetch-sahamscope.py
Select-String -LiteralPath "app/app-screener.py" -Pattern "/api/detail" -SimpleMatch
```
Expected: kompilasi bersih; rute ditemukan (2 lokasi: branch + tidak ada yang lain).

- [ ] **Step 4: Uji live (butuh internet)**

Jalankan server uji:
```bash
$env:SCREENER_NO_BROWSER = "1"; Start-Process pythonw "D:\saham\app\app-screener.py" -WorkingDirectory "D:\saham"; Start-Sleep 4
```
Lalu:
```bash
 CertUtil -hashfile "D:\saham\data\config.json" SHA256
 Invoke-WebRequest http://127.0.0.1:8765/api/detail -Method POST -ContentType "application/json" -Body '{}' -UseBasicParsing | Select-Object -ExpandProperty StatusCode
```
Expected: pertama 404 hanyalah bila rute belum ada — setelah implementasi harus **400**. Ulangi dengan `-Body '{"kodes":[]}'` → 400; `-Body '{"kodes":["X1","X2","X3","X4","X5","X6","X7","X8","X9","X10","X11","X12","X13","X14","X15","X16","X17","X18","X19","X20","X21","X22","X23","X24","X25","X26","X27","X28","X29","X30","X31"]}'` → 400. Terakhir `-Body '{"kodes":["BBCA","TLKM"]}'` → 200, `jumlah` 2, `scope.emiten` 2 kunci (bila kuota SahamScope tersedia; bila 429 → `scope` `{}` tapi tetap 200 — sah).
Verifikasi `CertUtil -hashfile` config.json + daftar-saham.txt IDENTIK sebelum/sesudah. Matikan server uji setelahnya (taskkill PID dari port 8765).

### Task 2: Frontend centang + checklist + tombol

**Files:**
- Modify: `web/screener-praktis.html` (state/mode, kolom centang thead+body, `#cekBar`, `#btnDetail`, `#detailBar`, handler, `renderCek`)
- Test: `tests/_test-praktis.js` (5 cek string) + manual browser

**Interfaces:**
- Consumes: `POST /api/detail` dari Task 1; `S.data` (record `build()` dengan `val.intrinsic`, `fase`, `r.nilai_harian`); pola toast/disabled tombol ada
- Produces: UI selesai. `S.mode` ("watchlist"|"pasar"|"lain"|"detail"), `S.picked` (kode→true), `S.modeDetail` bool.

- [ ] **Step 1: Tambah 5 cek string ke uji (gagal dulu)**

Di blok 7 tambah:
```js
  cek("kolom centang ada", html.includes('id="pickAll"') && html.includes("pickRow"));
  cek("tombol detail ada", html.includes('id="btnDetail"'));
  cek("cekBar ada", html.includes('id="cekBar"'));
  cek("detailBar ada", html.includes('id="detailBar"'));
  cek("endpoint detail dipakai", html.includes("/api/detail"));
```

- [ ] **Step 2: Jalankan uji untuk pastikan 5 cek baru gagal**

Run: `node tests/_test-praktis.js`
Expected: FAIL tepat pada 5 cek baru; semua cek lama PASS.

- [ ] **Step 3: State + mode di handler yang ada**

Deklarasi `var S`: tambahkan `mode: "watchlist", picked: {}, modeDetail: false` setelah `scope: {},` (tepatnya `ksei: {}, scope: {}, tema: {}, temaNama: "Semua",` → tambah di belakangnya).
Handler Download sukses: setelah `S.tema = j.tema || {};` tambah `S.mode = "watchlist"; S.modeDetail = false; S.picked = {};`.
Handler Scan sukses (setelah `SP.ingestKsei(j.ksei || {}, S.ksei);` milik Scan — yang toast-nya "Seluruh pasar dimuat"): tambah `S.mode = "pasar"; S.modeDetail = false; S.picked = {};`.
Handler Contoh (`S._csvRows = SP.parseCSV(SAMPLE_CSV);`): tambah `S.mode = "impor"; S.modeDetail = false; S.picked = {};`.
`fileIn.onchange`: di awal fungsi tambah `S.mode = "impor"; S.modeDetail = false; S.picked = {};`.

- [ ] **Step 4: HTML tombol + bar**

Di `.acts` header setelah tombol Scan (`<button class="btn" id="btnScanPasar">`), tidak — tombol Detail lebih dekat tabel: letakkan di toolbar sebelum search:
```html
      <button class="btn pri" id="btnDetail" hidden>Download Detail</button>
```
Tepat setelah `<div class="toolbar">` → sisipkan sebagai anak pertama. Dan setelah `</div>` penutup toolbar (sebelum `<div id="temaNarasi"`), tambah:
```html
    <div id="cekBar" class="mut" style="padding:8px 15px;border-bottom:1px solid var(--line2)" hidden></div>
    <div id="detailBar" class="hzw" hidden><span id="detailTxt"></span><button class="hzw-min" id="btnKembali">kembali ke watchlist</button></div>
```

- [ ] **Step 5: Kolom centang thead + body + guard klik**

Ubah pembangunan thead:
```js
    var thead = "<tr>" + COLS.map(function (c) {
```
menjadi:
```js
    var thead = (S.mode === "pasar" ? '<tr><th><input type="checkbox" id="pickAll" title="Pilih semua"></th>' : "<tr>") + COLS.map(function (c) {
```
Ubah colspan kosong:
```js
    $("tbl").tBodies[0].innerHTML = body || '<tr><td colspan="' + COLS.length + '" class="mut" style="text-align:center;padding:26px">Tidak ada saham cocok dengan filter.</td></tr>';
```
menjadi `COLS.length + (S.mode === "pasar" ? 1 : 0)`.
Ubah awal return baris:
```js
      return "<tr data-kode='" + x.kode + "'>" +
```
menjadi:
```js
      return "<tr data-kode='" + x.kode + "'>" +
        (S.mode === "pasar" ? '<td><input type="checkbox" class="pickRow" data-kode="' + x.kode + '"' + (S.picked[x.kode] ? " checked" : "") + "></td>" : "") +
```
Guard drawer di `$("tbl").tBodies[0].onclick` (baris `var tr = e.target.closest("tr[data-kode]")`), tambahkan baris sebelumnya:
```js
    if (e.target.closest("input")) return;
```
Tambahkan handler change (setelah blok onclick tersebut):
```js
  $("tbl").tBodies[0].onchange = function (e) {
    var c = e.target.closest("input.pickRow"); if (!c) return;
    var k = c.getAttribute("data-kode");
    if (c.checked) S.picked[k] = true; else delete S.picked[k];
    renderCek();
  };
```
Tambahkan handler pickAll di `$("tbl").tHead.onclick` paling awal:
```js
    if (e.target.id === "pickAll") {
      var on = e.target.checked;
      Array.prototype.forEach.call($("tbl").tBodies[0].querySelectorAll("input.pickRow"), function (c) {
        var k = c.getAttribute("data-kode");
        c.checked = on;
        if (on) S.picked[k] = true; else delete S.picked[k];
      });
      renderCek(); return;
    }
```

- [ ] **Step 6: `renderCek()` + panggil di akhir `render()` + wiring tombol**

Sebelum `function renderChips()` sisipkan:
```js
  function renderCek() {
    var keys = Object.keys(S.picked);
    var show = S.mode === "pasar";
    var bd = $("btnDetail");
    bd.hidden = !show || !keys.length;
    bd.textContent = "Download Detail (" + keys.length + ")";
    var bar = $("cekBar"), byKode = {};
    S.data.forEach(function (x) { byKode[x.kode] = x; });
    if (!show || !keys.length) { bar.hidden = true; }
    else {
      bar.innerHTML = keys.map(function (k) {
        var x = byKode[k]; if (!x) return "";
        function lamp(ok, t) { return '<span style="color:' + (ok ? "#17795e" : "#c62828") + '" title="' + t + '">' + (ok ? "✓" : "✗") + "</span>"; }
        return '<span style="margin-right:10px"><b>' + k + "</b> " + lamp(SP.toNum(x.r.nilai_harian) >= 5000000000, "Likuid ≥Rp5M/hari") + lamp(x.fase !== "Distribusi", "Bukan distribusi") + lamp(x.val.intrinsic > 0, "MOS terhitung") + "</span>";
      }).join("") + '<span class="mut">Likuid · Bukan distribusi · MOS terhitung</span>';
      bar.hidden = false;
    }
    var dbr = $("detailBar");
    if (S.modeDetail) { $("detailTxt").textContent = "Detail sementara " + S.data.length + " saham — watchlist tersimpan tidak berubah. "; dbr.hidden = false; }
    else dbr.hidden = true;
  }
```
Di akhir `render()` (setelah `$("tw").hidden = ...;`) tambah `renderCek();`.
Wiring tombol (dekat wiring lain, misal setelah `$("btnEkspor").onclick...` blok): 
```js
  $("btnDetail").onclick = function () {
    var b = this;
    var keys = Object.keys(S.picked);
    if (!keys.length) return;
    b.disabled = true; b.textContent = "Mengunduh detail…";
    fetch("/api/detail", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ kodes: keys }) }).then(function (r) {
      return r.json().then(function (j) { return { s: r.status, j: j }; });
    }).then(function (o) {
      if (!o.j || !o.j.ok) throw new Error((o.j && o.j.error) || "gagal");
      S._csvRows = o.j.saham || [];
      SP.ingestKsei(o.j.ksei || {}, S.ksei);
      S.scope = o.j.scope || {}; S.tema = o.j.tema || {};
      S.picked = {}; S.modeDetail = true; S.mode = "detail";
      rebuild();
      toast("Detail dimuat: " + (o.j.jumlah || S.data.length) + " saham (sementara)");
    }).catch(function (e) { toast("Gagal: " + (e && e.message ? e.message : e)); })
      .then(function () { b.disabled = false; b.textContent = "Download Detail"; });
  };
  $("btnKembali").onclick = function () { S.modeDetail = false; $("btnDownload").click(); };
```
(Catatan: `rebuild()` → `render()` → `renderCek()` menutup cekBar otomatis karena picked dikosongkan; `btnKembali` memicu Download normal yang me-reset mode.)

- [ ] **Step 7: Jalankan uji sampai lolos**

Run: `node tests/_test-praktis.js`
Expected: PASS — "Semua uji lulus".

- [ ] **Step 8: Uji manual browser (wajib)**

1. Server + Scan Seluruh Pasar → kolom centang tampil; centang 3 (satu illiquid bila ada) → cekBar `✓/✗` benar.
2. Download Detail → drawer penuh (bar akumulasi + kombo + level; scope ikut bila kuota tersedia) → banner kuning + Kembali → watchlist lama tampil.
3. Mode Download: centang tidak tampil.
