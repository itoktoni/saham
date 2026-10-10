# Grafik Laba-Rugi Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Drawer emiten menampilkan grafik SVG revenue + net income + margin % per kuartal/tahunan dengan tooltip nilai, bersumber Yahoo via `data/labarugi.json`.

**Architecture:** Fungsi murni `labarugi_series(fund)` di `scripts/fetch-data-idx.py` mengekstrak deret dari payload Yahoo yang sudah dibaca; alur scan mengoleksi + menyimpan + menyajikan via API; `SP.labarugiSVG()` me-render SVG inline di drawer. Skor/fundSkor tidak tersentuh.

**Tech Stack:** Python 3 (tanpa pytest — run langsung `python tests/*.py`), vanilla JS di `web/screener-praktis.html`, pola uji `tests/_test-praktis.js` (ekstrak modul SP via regex + `new Function`).

## Global Constraints

- Rumus `fundSkor()` dan bobot 30+30+10+10+20 tidak berubah.
- Angka hilang = null / slot "—", jangan nol palsu (lih. catatan gp==0 di `scripts/fetch-data-idx.py:696-700`).
- Commit hanya file yang diubah task tersebut; jangan ikutkan `data/*.json`, `*.db`, `logs/`, `screener.pid`, `__pycache__`.
- Test runner repo: `python tests/test-*.py` dan `node tests/_test-praktis.js` (bukan pytest/jest).

---

### Task 1: `labarugi_series(fund)` + uji Python

**Files:**
- Modify: `scripts/fetch-data-idx.py` (tambah fungsi setelah `build_record`, sekitar baris 880)
- Create: `tests/test-labarugi.py`

**Interfaces:**
- Consumes: payload Yahoo `fund` (`incomeStatementHistoryQuarterly.incomeStatementHistory`, `incomeStatementHistory.incomeStatementHistory`), helper `num()` (`scripts/fetch-data-idx.py:205`, `num(v, default)` mengembalikan float; `v=None` → default).
- Produces: `labarugi_series(fund)` → `{"q": [{"t": str, "rev": float|None, "ni": float|None}] (maks 4, tertua→terbaru), "y": [...] (maks 5)}`. Label `t` dari `endDate.fmt` (`"2026-06-30"`) bila ada, else `"Q?"`/`"20??"`. Entri tanpa rev DAN ni dibuang.

- [ ] **Step 1: Write the failing test**

```python
"""Test deret laba-rugi. Jalan tanpa pytest: python tests/test-labarugi.py"""
import importlib.util
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location(
    "m_idx", os.path.join(_ROOT, "scripts", "fetch-data-idx.py"))
m_idx = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m_idx)


def _fund():
    def e(dt, rev, ni):
        return {"endDate": {"raw": int(dt.replace("-", "")), "fmt": dt},
                "totalRevenue": {"raw": rev} if rev is not None else None,
                "netIncome": {"raw": ni} if ni is not None else None}
    return {
        "incomeStatementHistoryQuarterly": {"incomeStatementHistory": [
            e("2026-06-30", 10.0, 1.0), e("2026-03-31", 9.0, -0.5),
            e("2025-12-31", 8.0, 0.8), e("2025-09-30", 7.0, 0.7),
            e("2025-06-30", 6.0, 0.6)]},
        "incomeStatementHistory": {"incomeStatementHistory": [
            e("2025-12-31", 30.0, 2.0), e("2024-12-31", 28.0, 1.5)]},
    }


def test_kuartal_4_terbaru_urut():
    s = m_idx.labarugi_series(_fund())
    assert [p["t"] for p in s["q"]] == ["2025-09-30", "2025-12-31", "2026-03-31", "2026-06-30"], s
    assert s["q"][-1] == {"t": "2026-06-30", "rev": 10.0, "ni": 1.0}, s


def test_tahunan_dan_rugi_negatif():
    s = m_idx.labarugi_series(_fund())
    assert s["y"] == [{"t": "2024-12-31", "rev": 28.0, "ni": 1.5},
                      {"t": "2025-12-31", "rev": 30.0, "ni": 2.0}], s
    assert s["q"][2]["ni"] == -0.5, s


def test_kosong_aman():
    assert m_idx.labarugi_series({}) == {"q": [], "y": []}
    assert m_idx.labarugi_series(None) == {"q": [], "y": []}


if __name__ == "__main__":
    test_kuartal_4_terbaru_urut()
    test_tahunan_dan_rugi_negatif()
    test_kosong_aman()
    print("labarugi OK: 3 passed")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python tests/test-labarugi.py`
Expected: FAIL with `AttributeError: module ... has no attribute 'labarugi_series'`

- [ ] **Step 3: Write minimal implementation**

```python
def _lr_label(e, awalan):
    fmt = ((e.get("endDate") or {}).get("fmt") if isinstance(e.get("endDate"), dict) else e.get("endDate"))
    if isinstance(fmt, str) and len(fmt) >= 4:
        return fmt[:10]
    return awalan


def _lr_deret(rows, batas, awalan):
    rows = [r for r in (rows or []) if isinstance(r, dict)]
    rows = sorted(rows, key=lambda z: num((z.get("endDate") or {}).get("raw"), 0))
    out = []
    for r in rows:
        rev = r.get("totalRevenue")
        ni = r.get("netIncome")
        rev = num(rev, None) if rev is not None else None
        ni = num(ni, None) if ni is not None else None
        if rev is None and ni is None:
            continue
        out.append({"t": _lr_label(r, awalan), "rev": rev, "ni": ni})
    return out[-batas:]


def labarugi_series(fund):
    """Deret revenue + net income dari payload Yahoo. Rupiah penuh, None bila tak ada."""
    fund = fund or {}
    iq = ((fund.get("incomeStatementHistoryQuarterly") or {}).get("incomeStatementHistory") or [])
    ih = ((fund.get("incomeStatementHistory") or {}).get("incomeStatementHistory") or [])
    return {"q": _lr_deret(iq, 4, "Q?"), "y": _lr_deret(ih, 5, "20??")}
```

Letakkan tepat setelah `return {...}` akhir `build_record` (`scripts/fetch-data-idx.py:879`), sebelum komentar `# Regime pasar`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python tests/test-labarugi.py`
Expected: PASS `labarugi OK: 3 passed`

- [ ] **Step 5: Commit**

```bash
git add scripts/fetch-data-idx.py tests/test-labarugi.py
git commit -m "feat: labarugi_series + uji deret revenue/NI Yahoo"
```

### Task 2: Koleksi + simpan + sajikan `labarugi.json`

**Files:**
- Modify: `app/app-screener.py` (loop scan ~baris 439-445, dict `hasil` ~baris 598-610, helper baca cache)

**Interfaces:**
- Consumes: `Task 1: labarugi_series(fund)` (import via `load_mod` pola `muat_fund`, `app/app-screener.py:363`), `_baca_json(nama)` (`app/app-screener.py:290`, baca relatif `data/` karena `os.chdir(DATA_DIR)` di baris 63).
- Produces: `data/labarugi.json` (`{"diambil": iso, "emiten": {KODE: {"q": [...], "y": [...]}}}`) + kunci `"labarugi"` di respons `/api/download` (dan `/api/scan` bila memakai `hasil` yang sama).

- [ ] **Step 1: Write the failing test**

Tambah ke `tests/test-labarugi.py`:

```python
def test_respons_memuat_labarugi():
    import json
    src = open(os.path.join(_ROOT, "app", "app-screener.py"), encoding="utf-8").read()
    assert "labarugi" in src and "labarugi.json" in src, "API belum menyajikan labarugi"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python tests/test-labarugi.py`
Expected: FAIL dengan `AssertionError: API belum menyajikan labarugi`

- [ ] **Step 3: Write minimal implementation**

Di loop scan (dekat `rec = fd.build_record(...)`, ~baris 445), kumpulkan:

```python
labarugi[kode] = fd.labarugi_series(fund)
```

Tulis berkas setelah loop (pola `muat_fund`):

```python
with open("labarugi.json", "w", encoding="utf-8") as fh:
    json.dump({"diambil": datetime.now().astimezone().isoformat(timespec="seconds"),
               "emiten": labarugi}, fh, ensure_ascii=False)
```

Tambah helper baca-cache di dekat `muat_fund` (~baris 348):

```python
def muat_labarugi():
    try:
        return (_baca_json("labarugi.json") or {}).get("emiten") or {}
    except Exception:
        return {}
```

Tambah `"labarugi": muat_labarugi_atau_live,` ke dict `hasil` (~baris 607, setelah `"fund": fund,`). Saat scan live, pakai dict yang baru dikoleksi; saat baca cache, pakai `muat_labarugi()`. Jangan ubah kunci lain.

- [ ] **Step 4: Run test to verify it passes**

Run: `python tests/test-labarugi.py`
Expected: PASS (4 passed — perbarui `print` menjadi `labarugi OK: 4 passed`)

- [ ] **Step 5: Commit**

```bash
git add app/app-screener.py tests/test-labarugi.py
git commit -m "feat: sajikan labarugi.json via API"
```

### Task 3: `S.labarugi` di web + `SP.labarugiSVG()`

**Files:**
- Modify: `web/screener-praktis.html` (tambah `SP.labarugiSVG`, ekspor di `return {...}` dekat `fundSkor: fundSkor,`, isi `S.labarugi` di handler `/api/download` ~baris 2971 dan `/api/scan` ~baris 2989)
- Create: `tests/test-labarugi-display.js`

**Interfaces:**
- Consumes: `S.labarugi[KODE] = {q: [{t, rev, ni}], y: [...]}`; `SP.nf`, `SP.fmtBig` (ada di modul SP); CSS `.mut`, `.aksi` yang sudah ada.
- Produces: `SP.labarugiSVG(seri, mode)` → string `<svg ...>`; `mode` `"q"`|`"y"`. Margin dihitung sisi-display `ni/rev*100` (rev>0, else null). Bar tanpa rev+ni dilewati; seri kosong → string `"__KOSONG__"` agar drawer bisa fallback (bukan SVG kosong).

- [ ] **Step 1: Write the failing test**

```javascript
// Pakai: node tests/test-labarugi-display.js
"use strict";
const fs = require("fs");
const path = require("path");
let gagal = 0;
function cek(nama, kondisi, info) {
  if (kondisi) { console.log("  OK   " + nama); }
  else { gagal++; console.log("  GAGAL " + nama + (info ? "  -> " + info : "")); }
}
const html = fs.readFileSync(path.join(__dirname, "..", "web", "screener-praktis.html"), "utf-8");
const blocks = [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)].map(m => m[1]);
const script = blocks.reduce((a, b) => (a.length > b.length ? a : b), "");
const m = script.match(/var SP = \(function \(\) \{[\s\S]*?\n\}\)\(\);/);
cek("modul SP ditemukan", !!m);
if (!m) process.exit(1);
const SP = new Function(m[0] + "; return SP;")();
cek("SP.labarugiSVG ada", typeof SP.labarugiSVG === "function");
if (typeof SP.labarugiSVG === "function") {
  const seri = { q: [{ t: "2026-03-31", rev: 9e12, ni: -0.5e12 }, { t: "2026-06-30", rev: 10e12, ni: 1e12 }], y: [] };
  const s = SP.labarugiSVG(seri, "q");
  cek("keluaran <svg", s.indexOf("<svg") === 0, s.slice(0, 60));
  cek("tooltip <title> ada", s.indexOf("<title>") > 0);
  cek("seri kosong -> __KOSONG__", SP.labarugiSVG({ q: [], y: [] }, "q") === "__KOSONG__");
}
cek("S.labarugi dimuat dari API", html.indexOf("S.labarugi") >= 0 && html.indexOf("j.labarugi") >= 0);
if (gagal) { console.log("HASIL: " + gagal + " GAGAL"); process.exit(1); }
else { console.log("HASIL: semua lolos"); }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node tests/test-labarugi-display.js`
Expected: FAIL `GAGAL SP.labarugiSVG ada` (+ `GAGAL S.labarugi dimuat dari API`)

- [ ] **Step 3: Write minimal implementation**

Di modul SP (sebelum `return {`, dekat helper FS display-only):

```javascript
function labarugiSVG(seri, mode) {
  var arr = ((seri || {})[mode === "y" ? "y" : "q"] || []).filter(function (p) {
    return p && (p.rev != null || p.ni != null);
  });
  if (!arr.length) return "__KOSONG__";
  var W = 680, H = 240, L = 8, R = 672, T = 30, B = 200;
  var vals = [];
  arr.forEach(function (p) { if (p.rev != null) vals.push(p.rev); if (p.ni != null) vals.push(p.ni); });
  vals.push(0);
  var mx = Math.max.apply(null, vals), mn = Math.min.apply(null, vals), sp = (mx - mn) || 1;
  function Y(v) { return B - (v - mn) / sp * (B - T); }
  var y0 = Y(0), n = arr.length, slot = (R - L) / n, bw = Math.max(10, Math.min(30, slot * 0.28));
  function fm(v) { return fmtBig(v); }
  var s = '<svg class="chart" viewBox="0 0 680 240" role="img"><title>Revenue & net income</title>';
  s += '<line x1="' + L + '" y1="' + y0.toFixed(1) + '" x2="' + R + '" y2="' + y0.toFixed(1) + '" stroke="#8a8f98" stroke-width="1.2"/>';
  var d = "";
  arr.forEach(function (p, i) {
    var cx = L + slot * i + slot / 2;
    var mg = (p.rev != null && p.rev > 0 && p.ni != null) ? (p.ni / p.rev * 100) : null;
    function bar(v, dx, col, lab) {
      if (v == null) return "";
      var yv = Y(v), top = Math.min(yv, y0), h = Math.max(2, Math.abs(yv - y0));
      return '<rect x="' + (cx + dx - bw / 2).toFixed(1) + '" y="' + top.toFixed(1) + '" width="' + bw.toFixed(1) +
        '" height="' + h.toFixed(1) + '" rx="2" fill="' + col + '"><title>' + p.t + " · " + lab + ": " + fm(v) +
        (mg != null ? " · margin " + nf(mg, 1) + "%" : "") + "</title></rect>";
    }
    s += bar(p.rev, -bw * 0.55, "#1f5fd0", "rev");
    s += bar(p.ni, bw * 0.55, (p.ni != null && p.ni < 0) ? "#c62828" : "#17795e", "ni");
    var lbl = (p.ni != null ? fm(p.ni) : "—") + (mg != null ? " (" + nf(mg, 1) + "%)" : "");
    s += '<text x="' + cx.toFixed(1) + '" y="' + (B + 16) + '" font-size="10" fill="#5b6470" text-anchor="middle">' + p.t.slice(2) + "</text>";
    s += '<text x="' + cx.toFixed(1) + '" y="' + (T - 8) + '" font-size="9" fill="#3d444d" text-anchor="middle">' + lbl + "</text>";
    if (mg != null) {
      var my = B - Math.max(0, Math.min(100, mg + 20)) / 120 * (B - T);
      d += (d ? "L" : "M") + cx.toFixed(1) + " " + my.toFixed(1);
    }
  });
  if (d) s += '<path d="' + d + '" fill="none" stroke="#b26a00" stroke-width="1.6"/>';
  return s + "</svg>";
}
```

Ekspor: tambah `labarugiSVG: labarugiSVG,` di `return {...}` setelah `fsVerdict: fsVerdict,`. Muat data: di kedua handler (`/api/download` setelah `S.fund = j.fund || {};` ~baris 2971 dan `/api/scan` setelah kemunculan kedua `S.fund = j.fund` — cari string `S.fund = j.fund` dan ubah keduanya) tambah `S.labarugi = j.labarugi || {};`. Pastikan `S` literal awal memuat `labarugi: {}`.

- [ ] **Step 4: Run test to verify it passes**

Run: `node tests/test-labarugi-display.js`
Expected: PASS `HASIL: semua lolos`

- [ ] **Step 5: Commit**

```bash
git add web/screener-praktis.html tests/test-labarugi-display.js
git commit -m "feat: labarugiSVG + S.labarugi dari API"
```

### Task 4: Seksi drawer + toggle + fallback + BUILD_V

**Files:**
- Modify: `web/screener-praktis.html` (fungsi `isiDrawer`, dekat blok Step 2 / `fundBox(x)`, dan `BUILD_V`)

**Interfaces:**
- Consumes: `Task 3: SP.labarugiSVG(seri, mode)`, `S.labarugi`, `rowx()` global drawer.
- Produces: seksi "Revenue & Net Income" dengan toggle Kuartal|Tahunan (persist lokal `S._lrMode`), fallback `Data laba-rugi belum diambil — unduh ulang data.` bila `__KOSONG__`.

- [ ] **Step 1: Write the failing test**

Tambah ke `tests/test-labarugi-display.js` sebelum baris hasil akhir:

```javascript
cek("drawer panggil labarugiSVG", html.indexOf("labarugiSVG") >= 0 && html.indexOf("Revenue & Net Income") >= 0);
cek("ada toggle Kuartal/Tahunan", html.indexOf("Kuartal") >= 0 && html.indexOf("Tahunan") >= 0);
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node tests/test-labarugi-display.js`
Expected: FAIL `GAGAL drawer panggil labarugiSVG`

- [ ] **Step 3: Write minimal implementation**

Di `isiDrawer`, setelah blok Step 2 (cari `fundBox(x) + saingBox(x)`), sisipkan:

```javascript
var lrSeri = ((S.labarugi || {})[x.kode] || { q: [], y: [] });
var lrMode = S._lrMode === "y" ? "y" : "q";
var lrSvg = SP.labarugiSVG(lrSeri, lrMode);
var s2c = '<div class="step"><h3>2c · Revenue &amp; Net Income</h3>' +
  '<div class="chips"><button class="chip' + (lrMode === "q" ? " on" : "") + '" id="lrQ">Kuartal</button>' +
  '<button class="chip' + (lrMode === "y" ? " on" : "") + '" id="lrY">Tahunan</button></div>' +
  (lrSvg === "__KOSONG__" ? '<div class="mut">Data laba-rugi belum diambil — unduh ulang data.</div>' : lrSvg) +
  '<div class="mut" style="font-size:11px">Biru = revenue · hijau/merah = net income · garis kuning = margin ni/rev. Arahkan kursor ke batang untuk nilai persis.</div></div>';
```

Gabungkan `s2c` ke HTML drawer (cari tempat `s2`/`s2b` digabungkan, tambah `+ s2c`). Daftarkan klik toggle di dekat handler drawer lain:

```javascript
var bQ = document.getElementById("lrQ"), bY = document.getElementById("lrY");
if (bQ) bQ.onclick = function () { S._lrMode = "q"; isiDrawer(S._drawerRec); };
if (bY) bY.onclick = function () { S._lrMode = "y"; isiDrawer(S._drawerRec); };
```

Naikkan `BUILD_V` (cari `var BUILD_V = "v2026-10-09J`) suffix huruf satu tingkat (mis. `...J` → `...K`) + tambah `· grafik laba-rugi` agar user tahu refresh (Ctrl+F5).

- [ ] **Step 4: Run test to verify it passes**

Run: `node tests/test-labarugi-display.js` dan `node tests/_test-praktis.js`
Expected: labarugi display semua lolos; `_test-praktis.js` tanpa gagal baru (4 gagal pra-eksis: umur fase, kontrak, TF segmented, ekspor BOM)

- [ ] **Step 5: Commit**

```bash
git add web/screener-praktis.html tests/test-labarugi-display.js
git commit -m "feat: seksi drawer revenue+NI dengan toggle kuartal/tahunan"
```
