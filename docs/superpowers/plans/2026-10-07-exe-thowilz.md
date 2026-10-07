# Exe Thowilz di Halaman Default Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Halaman default exe (`web/screener-praktis.html`) menampilkan analisis Thowilz (badge kas, EV/CFO, klasifikasi, skor + checklist 4 pilar di drawer) dengan data dari `/api/download` yang sudah membawa 12 kolom baru.

**Architecture:** Display-only di `SP` + `COLS` + template baris + drawer; bobot `skor` terkalibrasi JANGAN disentuh; nilai mentah dibaca dari `x.r.*` (string CSV atau number/null JSON) dengan guard null-kosong-nol; helper baru diekspos di `SP` agar bisa diuji node.

**Tech Stack:** Vanilla JS di satu file HTML, Python tak tersentuh, test via `node tests/_test-praktis.js` (pola `cek()` existing).

## Global Constraints

- Jangan ubah rumus `skor`, `aksi`, `valuasi`, `finalScore`, atau threshold filter apa pun.
- Badge pakai kelas existing: `aksi a-beli` (Lolos), `aksi a-pantau` (Watchlist), `aksi a-hindar` (Kill), `mut —` (data kosong).
- CSV 31 kolom lama dan JSON (number/null) harus tetap tampil tanpa error; kosong → `—`.
- `SAMPLE_CSV` 31 kolom tidak diubah (parser header-based, otomatis toleran).
- Sort missing numerik = -1 (sejajar pola `asing`/`upside`), sejajar ke bawah pada sort desc.

---

### Task 1: Helper SP + kolom tabel + sel baris

**Files:**
- Modify: `web/screener-praktis.html` (dalam `var SP`, `COLS`, template baris `render()`)
- Test: `tests/_test-praktis.js` (tambah 4 `cek`)

**Interfaces:**
- Consumes: `x.r.ev_cfo, x.r.ev_fcf, x.r.peg_cfo, x.r.cfo_cagr, x.r.gross_margin, x.r.margin_stabil, x.r.capex_inten, x.r.cfo3, x.r.sloan, x.r.cash_badge, x.r.klasifikasi, x.r.thowilz` (string|number|null).
- Produces: `SP.twBadge(v)->html`, `SP.twNum(v,digit)->html`, `SP.twKas(v)->html`; `COLS` baru `k:"kas"`, `k:"evcfo"`, `k:"klas"`, `k:"thowilz"`.

- [ ] **Step 1: Write the failing test**

Tambah di akhir `tests/_test-praktis.js` sebelum baris `process.exit` terakhir (cari `process.exit(gagal ? 1 : 0)` paling bawah; sisipkan di atasnya):

```js
cek("thowilz: SP.twBadge Lolos", SP.twBadge("Lolos").indexOf("a-beli") >= 0);
cek("thowilz: SP.twBadge Kill", SP.twBadge("Kill").indexOf("a-hindar") >= 0);
cek("thowilz: SP.twBadge kosong", SP.twBadge("-") === "—" && SP.twBadge("") === "—" && SP.twBadge(null) === "—");
cek("thowilz: SP.twNum", SP.twNum(null) === "—" && SP.twNum("") === "—" && SP.twNum(0) === "—" && SP.twNum(7.22, 1) !== "—");
cek("thowilz: marker kolom di HTML", html.indexOf("thowilz") >= 0 && html.indexOf("Kualitas Kas") >= 0);
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node tests/_test-praktis.js 2>&1 | Select-String "thowilz|uji GAGAL"`
Expected: FAIL 5 baris `GAGAL thowilz` (helper belum ada; marker belum ada) + 4 GAGAL pre-existing lama.

- [ ] **Step 3: Write minimal implementation**

1. Di dalam `var SP = (function () {`, dekat `toNum` (line ~255), tambah:

```js
  function twNum(v, d) {
    if (v == null || v === "") return "—";
    var n = (typeof v === "number") ? v : toNum(v);
    if (!isFinite(n) || n <= 0) return "—";
    var p = Math.pow(10, d == null ? 1 : d);
    return String(Math.round(n * p) / p).replace(".", ",");
  }
  function twBadge(v) {
    if (v === "Lolos") return '<span class="aksi a-beli">Lolos</span>';
    if (v === "Watchlist") return '<span class="aksi a-pantau">Watch</span>';
    if (v === "Kill") return '<span class="aksi a-hindar">Kill</span>';
    return "—";
  }
  function twKas(v) {
    if (v === "Lolos") return "kas sehat";
    if (v === "Watchlist") return "cek manual";
    if (v === "Kill") return "laba semu";
    return "data kurang";
  }
```

`toNum` dipakai langsung (satu closure SP; `nf` page-scope tidak dipakai agar helper tetap jalan di uji node yang hanya mengekstrak IIFE `SP`). Format desimal manual gaya Indonesia.

2. Di `return` SP (line ~957 `skor: skor, aksi: aksi, build: build, ...`), tambah `twBadge: twBadge, twNum: twNum, twKas: twKas,`.

3. `COLS`: tambah setelah `{ k: "combo", ... }`:

```js
    { k: "kas", t: "Kas", n: false, get: function (d) { return d.r.cash_badge || ""; } },
    { k: "evcfo", t: "EV/CFO", n: true, get: function (d) { var v = d.r.ev_cfo; v = (v == null || v === "") ? -1 : SP.toNum(v); return v > 0 ? v : -1; } },
    { k: "klas", t: "Klas", n: false, get: function (d) { return d.r.klasifikasi || ""; } },
    { k: "thowilz", t: "Thowilz", n: true, get: function (d) { var v = SP.toNum(d.r.thowilz); return v > 0 ? v : -1; } }
```

4. Template baris: setelah `"<td>" + comboBadge(x) + "</td>" +` tambah:

```js
        "<td>" + SP.twBadge(x.r.cash_badge) + "</td>" +
        '<td class="n">' + SP.twNum(x.r.ev_cfo, 1) + "</td>" +
        '<td>' + ((x.r.klasifikasi == null || x.r.klasifikasi === "" || x.r.klasifikasi === "-") ? '<span class="mut">—</span>' : String(x.r.klasifikasi).replace(/</g, "")) + "</td>" +
        '<td class="n"><b>' + (SP.toNum(x.r.thowilz) > 0 ? SP.toNum(x.r.thowilz) : '<span class="mut">—</span>') + "</b></td>" +
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node tests/_test-praktis.js 2>&1 | Select-String "thowilz|uji GAGAL"`
Expected: 5 `OK thowilz`, total GAGAL tetap 4 (pre-existing: sp_umur, sp_kontrak, segmented, ekspor).

- [ ] **Step 5: Commit**

```bash
git add web/screener-praktis.html tests/_test-praktis.js
git commit -m "feat: kolom Kas/EV-CFO/Klas/Thowilz di halaman default exe"
```

### Task 2: Drawer langkah Kualitas Kas Thowilz

**Files:**
- Modify: `web/screener-praktis.html` (fungsi `bukaDrawer`, setelah `var s2 = ...`)
- Test: `tests/_test-praktis.js` (tambah 1 `cek` marker)

**Interfaces:**
- Consumes: `r` (raw row), helper `rowx`, `SP.twBadge`, `SP.twNum`, `SP.toNum`.
- Produces: `var s2b` disisipkan antara `s2` dan `s3` di HTML drawer.

- [ ] **Step 1: Write the failing test**

```js
cek("thowilz: drawer panel di HTML", html.indexOf("Kualitas Kas Thowilz") >= 0 && html.indexOf("Checklist Thowilz") >= 0);
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node tests/_test-praktis.js 2>&1 | Select-String "drawer panel"`
Expected: FAIL `GAGAL thowilz: drawer panel di HTML`.

- [ ] **Step 3: Write minimal implementation**

Setelah blok `var s2 = ... + fundBox(x) + saingBox(x) + "</div>";` tambah:

```js
    var twOk = function (ok) { return ok ? '<span class="aksi a-beli">OK</span>' : '<span class="aksi a-hindar">X</span>'; };
    var evcf = (r.ev_cfo == null || r.ev_cfo === "") ? null : SP.toNum(r.ev_cfo);
    var s2b = '<div class="step"><h3>2b · Kualitas Kas Thowilz</h3>' +
      rowx("Badge kas", SP.twBadge(r.cash_badge), "Lolos = CFO selaras laba 3 tahun. Kill = laba semu, hindari. " + SP.twKas(r.cash_badge) + ".") +
      rowx("EV/CFO", SP.twNum(r.ev_cfo, 1) + (evcf ? "x" : ""), "harga perusahaan vs kas operasi. ≤10 murah, ≤15 wajar.") +
      rowx("EV/FCF", SP.twNum(r.ev_fcf, 1), "kas bebas setelah belanja modal.") +
      rowx("PEG-CFO", (r.peg_cfo == null || r.peg_cfo === "" || !(SP.toNum(r.peg_cfo) > 0)) ? "—" : nf(SP.toNum(r.peg_cfo), 2), "<1 murah vs pertumbuhan kas, >1,5 mahal.") +
      rowx("CFO > laba 3 thn", SP.toNum(r.cfo3) === 1 ? "Ya" : ((r.cash_badge == null || r.cash_badge === "" || r.cash_badge === "-") ? "—" : "Tidak"), "cfo3 dari laporan.") +
      rowx("Sloan accrual", (r.sloan == null || r.sloan === "") ? "—" : nf(SP.toNum(r.sloan), 2), ">0,10 laba semu.") +
      rowx("Gross margin", (r.gross_margin == null || r.gross_margin === "") ? "—" : nf(SP.toNum(r.gross_margin), 1) + "%" + (SP.toNum(r.margin_stabil) === 1 ? " (stabil)" : " (labil)"), "proksi pricing power.") +
      rowx("Klasifikasi", (r.klasifikasi == null || r.klasifikasi === "" || r.klasifikasi === "-") ? "—" : String(r.klasifikasi).replace(/</g, ""), "Turnaround > AssetPlay > FastGrowing > Cyclical > Stalwart.") +
      rowx("Skor Thowilz", SP.toNum(r.thowilz) > 0 ? "<b>" + SP.toNum(r.thowilz) + " / 100</b>" : "—", "Valuasi 35 + Kualitas 35 + Tesis 15 + Timing 15.") +
      rowx("Checklist Thowilz", twOk(evcf && evcf <= 15) + " valuasi · " + twOk(r.cash_badge === "Lolos") + " kas · " + twOk(r.klasifikasi && r.klasifikasi !== "-") + " tesis · " + twOk(SP.toNum(r.s_spring) === 1 || SP.toNum(r.s_sideways) === 1) + " timing", "4 pilar dari doc Thomas William.") +
      "</div>";
```

Lalu gabungkan ke drawer: cari baris yang menggabungkan `s1 + s2 + s3` (mis. `$("dwBody").innerHTML = s1 + s2 + s3 ...`), ubah menjadi `s1 + s2 + s2b + s3 ...`. Baca baris itu dulu sebelum edit (grep `dwBody`).

- [ ] **Step 4: Run test to verify it passes**

Run: `node tests/_test-praktis.js 2>&1 | Select-String "thowilz|uji GAGAL"`
Expected: 6 `OK thowilz`, total GAGAL tetap 4 pre-existing.

- [ ] **Step 5: Commit**

```bash
git add web/screener-praktis.html tests/_test-praktis.js
git commit -m "feat: drawer Kualitas Kas + checklist Thowilz di exe"
```

### Task 3: Verifikasi akhir

- [ ] **Step 1: Suite penuh**

```bash
python tests/test-cash-quality.py
python tests/test-harian.py
node tests/_test-cash-ui.js
node tests/_test-praktis.js
```

Harap: 17 passed, 4 passed, cash-ui OK, praktis GAGAL hanya 4 pre-existing yang sama.

- [ ] **Step 2: Simulasi data download**

```bash
python -c "import importlib.util; spec=importlib.util.spec_from_file_location('m','scripts/fetch-data-idx.py'); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); f={'price':{'regularMarketPrice':{'raw':1000}},'summaryDetail':{},'assetProfile':{},'defaultKeyStatistics':{'sharesOutstanding':{'raw':10},'bookValue':{'raw':500},'trailingEps':{'raw':100},'netIncomeToCommon':{'raw':1000}},'financialData':{'totalDebt':{'raw':2000},'totalCash':{'raw':500},'operatingCashflow':{'raw':1500},'freeCashflow':{'raw':800},'earningsGrowth':{'raw':0.25}},'incomeStatementHistoryQuarterly':{'incomeStatementHistory':[]},'incomeStatementHistory':{'incomeStatementHistory':[]}}; r=m.build_record('ZZZ',{'nama':'Z','sektor':'Energi'},f,None,None); print(sorted([k for k in r if k in ('ev_cfo','cash_badge','klasifikasi','thowilz')])); print('kas:'+str(r['cash_badge'])+' klas:'+str(r['klasifikasi'])+' skor:'+str(r['thowilz']))"
```

Harap: 4 kunci ada, badge/klas/skor terisi — bukti `/api/download` membawa data yang dibaca drawer baru.

- [ ] **Step 3: Commit bila ada perbaikan**

```bash
git add -A
git commit -m "fix: selarasan akhir Thowilz exe" || echo "tidak ada perubahan"
```

## Self-Review

- Spec coverage: exe default page menampilkan badge/kolom/skor/checklist ✓; skor kalibrasi tak tersentuh ✓; CSV lama + JSON null aman (guard di setiap sel) ✓.
- Placeholder scan: semua langkah ada kode + run + expected; satu-satunya baca-dulu (`dwBody`) adalah lokasi satu baris yang sudah diidentifikasi via grep.
- Type consistency: `twNum` kembalikan string `—` atau angka format manual koma-desimal; `COLS.get` kembalikan number/(-1)/string konsisten dengan pola kolom existing; `SP.twBadge(null)` → `—` (perbandingan ketat, null hanya cocok ke return akhir ✓).
