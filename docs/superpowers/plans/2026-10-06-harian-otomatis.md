# Harian Otomatis Seluruh Pasar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fetch otomatis Volume/Value/Frequency per emiten seluruh pasar dari IDX Stock Summary dan tampilkan di screener mode pasar.

**Architecture:** Tambah fetcher sejajar `hitung_likuiditas()` di `scripts/fetch-data-idx.py` memakai `Fetcher.get()` yang sama (urllib + fallback curl), tulis atomik `data/harian-YYYYMMDD.json`, serve via `/api/harian` di `app/app-screener.py`, merge by kode di `web/screener-praktis.html`.

**Tech Stack:** Python 3 stdlib only (urllib, json, http.cookiejar), HTML/JS vanilla di web, tanpa dependensi baru.

## Global Constraints

- Python stdlib saja, tidak tambah dependensi.
- Jangan ubah logika skor/valuasi yang sudah ada.
- Kegagalan network tidak boleh merusak file lama; tulis atomik (tmp + rename) dan log jujur.
- Format angka mengikuti konvensi training CSV (suffix B/M/K di web saja, JSON selalu angka penuh).
- Ikuti pola Cloudflare yang ada: `Fetcher.get()` dengan header Referer + X-Requested-With.

---

### Task 1: Fetcher + normalizer Stock Summary IDX

**Files:**
- Modify: `scripts/fetch-data-idx.py:631` (tambah konstanta), tambah fungsi setelah `hitung_likuiditas()` (~baris 775)
- Test: `tests/test-harian.py`

**Interfaces:**
- Consumes: `Fetcher.get(url, headers)` dari `scripts/fetch-data-idx.py:270`
- Produces: `IDX_STOCK_URL: str`, `fetch_stock_summary(f, tanggal_yyyymmdd) -> list[dict] | None`, `normalkan_baris_stock(r: dict) -> dict | None`

# Test loader (pakai di semua test Task 1-3, karena nama file ada strip):

```python
# tests/test-harian.py (atas file, sekali saja)
import importlib.util
_spec = importlib.util.spec_from_file_location("m_idx", "scripts/fetch-data-idx.py")
m_idx = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m_idx)
normalkan_baris_stock = m_idx.normalkan_baris_stock
```

- [ ] **Step 1: Write the failing test**

```python
def test_normalkan_baris_stock():
    r = {"StockCode": "GOTO", "High": "33", "Low": "30", "Close": "32",
         "Volume": "157390000", "Value": "487060000000", "Frequency": "38180"}
    out = normalkan_baris_stock(r)
    assert out == {"kode": "GOTO", "high": 33, "low": 30, "close": 32,
                   "volume": 157390000, "value": 487060000000, "freq": 38180}

def test_baris_tanpa_kode_dibuang():
    assert normalkan_baris_stock({"Volume": "1"}) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test-harian.py -v`
Expected: FAIL with "No module named 'fetch_data_idx_harian'" atau "function not defined"

- [ ] **Step 3: Write minimal implementation**

```python
IDX_STOCK_URL = "https://www.idx.co.id/primary/TradingSummary/GetStockSummary"

def _ke_int(v):
    try:
        if v is None or v == "":
            return 0
        return int(float(str(v).replace(",", "").strip()))
    except (ValueError, TypeError):
        return 0

def normalkan_baris_stock(r):
    kode = str(r.get("StockCode") or r.get("kode") or "").strip().upper()
    if not kode:
        return None
    return {
        "kode": kode,
        "high": _ke_int(r.get("High")),
        "low": _ke_int(r.get("Low")),
        "close": _ke_int(r.get("Close")),
        "volume": _ke_int(r.get("Volume")),
        "value": _ke_int(r.get("Value")),
        "freq": _ke_int(r.get("Frequency")),
    }

def fetch_stock_summary(f, tanggal_yyyymmdd):
    url = "%s?date=%s" % (IDX_STOCK_URL, tanggal_yyyymmdd)
    j = f.get(url, headers={
        "Referer": "https://www.idx.co.id/",
        "X-Requested-With": "XMLHttpRequest",
    })
    if not j:
        return None
    rows = j.get("data") if isinstance(j, dict) else j
    if not rows:
        return None
    out = []
    for r in rows:
        n = normalkan_baris_stock(r)
        if n:
            out.append(n)
    return out or None
```

Lokasi: tempel konstanta di bawah `IDX_INDEX_URL` (baris 631), fungsi tepat setelah `hitung_likuiditas()` berakhir (sebelum `hitung_sektor`). Untuk test, import via `load_mod` atau salin fungsi ke modul test sementara — cara termudah: test import langsung dari file dengan `importlib.util.spec_from_file_location("m", "scripts/fetch-data-idx.py")`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test-harian.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add scripts/fetch-data-idx.py tests/test-harian.py
git commit -m "feat: fetcher dan normalizer Stock Summary IDX"
```

### Task 2: CLI --harian + writer atomik JSON

**Files:**
- Modify: `scripts/fetch-data-idx.py:1838-1858` (argparse), mode `--harian` dekat mode `--pasar` (~baris 1964-1974)
- Test: `tests/test-harian.py` (tambah test writer)

**Interfaces:**
- Consumes: `fetch_stock_summary(f, tanggal)` dari Task 1
- Produces: CLI flags `--harian`, `--harian-tanggal YYYYMMDD`; file `data/harian-YYYYMMDD.json` dengan skema `{dibuat, tanggal, jumlah, sumber, saham: [...]}`

- [ ] **Step 1: Write the failing test**

```python
def test_tulis_harian_atomik(tmp_path):
    tulis_harian = m_idx.tulis_harian
    tujuan = str(tmp_path / "harian-20261006.json")
    out = tulis_harian(tujuan, "20261006", [{"kode": "GOTO", "high": 33, "low": 30,
        "close": 32, "volume": 157390000, "value": 487060000000, "freq": 38180}])
    assert out == tujuan
    import json
    d = json.load(open(tujuan, encoding="utf-8"))
    assert d["tanggal"] == "20261006" and d["jumlah"] == 1
    assert d["saham"][0]["kode"] == "GOTO"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test-harian.py::test_tulis_harian_atomik -v`
Expected: FAIL with "tulis_harian not defined"

- [ ] **Step 3: Write minimal implementation**

```python
def tulis_harian(path_tujuan, tanggal, saham):
    import json, os
    from datetime import datetime
    payload = {
        "dibuat": datetime.now().astimezone().isoformat(timespec="seconds"),
        "tanggal": tanggal,
        "jumlah": len(saham),
        "sumber": "IDX Stock Summary (Volume/Value/Frequency resmi per emiten)",
        "saham": saham,
    }
    tmp = path_tujuan + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, path_tujuan)
    return path_tujuan
```

Argparse (tambah di dekat `--pasar`):

```python
ap.add_argument("--harian", action="store_true",
                help="HANYA ambil Stock Summary harian seluruh pasar (Volume/Value/Freq)")
ap.add_argument("--harian-tanggal", default=None, metavar="YYYYMMDD",
                help="Tanggal perdagangan, mis. 20261006 (bawaan: hari ini)")
```

Mode handler (taro tepat sebelum `if args.pasar:`):

```python
if args.harian:
    from datetime import datetime as _dt
    tgl = args.harian_tanggal or _dt.now().strftime("%Y%m%d")
    data = fetch_stock_summary(f, tgl)
    if not data:
        log("[!] Stock Summary %s kosong/gagal (IDX 403 atau libur). File lama tidak diubah." % tgl)
        return 2
    path = "harian-%s.json" % tgl
    tulis_harian(path, tgl, data)
    log("Harian tersimpan: %s (%d emiten)" % (os.path.abspath(path), len(data)))
    return 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test-harian.py -v`
Expected: PASS (3 passed)

Run manual kering (tanpa network, cek help): `python scripts/fetch-data-idx.py --help | findstr harian`
Expected: tampil `--harian` dan `--harian-tanggal`

- [ ] **Step 5: Commit**

```bash
git add scripts/fetch-data-idx.py tests/test-harian.py
git commit -m "feat: CLI --harian dan writer atomik harian JSON"
```

### Task 3: Endpoint /api/harian di app-screener

**Files:**
- Modify: `app/app-screener.py:480-490` (tambah handler setelah `/api/scan`)
- Test: `tests/test-harian.py` (tambah test loader) atau `tests/_smoke-ui.py` bila ada pola

**Interfaces:**
- Consumes: file `data/harian-YYYYMMDD.json` dari Task 2
- Produces: helper `baca_harian_terbaru(data_dir, tanggal=None)` di `app/app-screener.py`
  + `GET /api/harian?tanggal=YYYYMMDD -> {ok, tanggal, jumlah, saham}`; default tanggal = file terbaru

- [ ] **Step 1: Write the failing test**

```python
def test_baca_harian_terbaru(tmp_path):
    import json, importlib.util
    p = tmp_path / "harian-20261006.json"
    p.write_text(json.dumps({"tanggal": "20261006", "jumlah": 1,
        "saham": [{"kode": "GOTO", "close": 32, "volume": 1, "value": 2, "freq": 3}]}),
        encoding="utf-8")
    spec = importlib.util.spec_from_file_location("m_app", "app/app-screener.py")
    m_app = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m_app)
    d = m_app.baca_harian_terbaru(str(tmp_path))
    assert d["tanggal"] == "20261006" and d["jumlah"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test-harian.py::test_baca_harian_terbaru -v`
Expected: FAIL with "baca_harian_terbaru not defined"

- [ ] **Step 3: Write minimal implementation**

```python
def baca_harian_terbaru(data_dir, tanggal=None):
    import json, os, glob
    if tanggal:
        path = os.path.join(data_dir, "harian-%s.json" % tanggal)
        if not os.path.exists(path):
            return None
    else:
        files = sorted(glob.glob(os.path.join(data_dir, "harian-*.json")))
        if not files:
            return None
        path = files[-1]
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None
```

Handler di `app/app-screener.py` setelah blok `/api/scan` (setelah baris 490):

```python
if jalur == "/api/harian":
    q = parse_qs(u.query)
    tgl = (q.get("tanggal", [""])[0] or "").strip()
    d = baca_harian_terbaru(DATA_DIR, tgl or None)
    if not d:
        return self._json({"ok": False, "error": "belum ada data harian."}, 404)
    return self._json({"ok": True, "tanggal": d.get("tanggal"),
                       "jumlah": d.get("jumlah", len(d.get("saham", []))),
                       "saham": d.get("saham", [])})
```

Catatan: `DATA_DIR`, `parse_qs`, `self._json` sudah ada di file itu; letakkan helper `baca_harian_terbaru` di dekat `muat_tema()`/`_baca_json()`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test-harian.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add app/app-screener.py tests/test-harian.py
git commit -m "feat: endpoint /api/harian untuk data Stock Summary"
```

### Task 4: Kolom Freq + Value di screener mode pasar

**Files:**
- Modify: `web/screener-praktis.html` (tabel mode pasar: header + render row + merge by kode dari `/api/harian`)
- Test: manual browser (tidak ada test JS otomatis untuk kolom ini)

**Interfaces:**
- Consumes: `/api/harian` dari Task 3, `S._csvRows` / `rebuild()` yang sudah ada (~baris 1950-1956)
- Produces: kolom `Freq` dan `Value (Rp)` tampil di mode pasar dengan format suffix B/M/K

- [ ] **Step 1: Write the failing check (manual)**

Buka `web/screener-praktis.html` via app, klik scan pasar. Catat: kolom Freq/Value belum ada.

- [ ] **Step 2: Implement minimal**

1. Setelah `fetch("/api/scan")` sukses di `$("btnScanPasar").onclick` (~baris 1950), tambah fetch `/api/harian`, bangun `map = {KODE: {freq, value, volume}}`, tempel ke tiap row `saham` sebagai `x._freq`, `x._hvalue`.
2. Tambah 2 header kolom di render tabel pasar: `Freq`, `Value`.
3. Format helper (taro dekat helper angka yang ada):

```js
function fmtBig(v) {
  v = Number(v || 0);
  if (v >= 1e9) return (v / 1e9).toFixed(2) + "B";
  if (v >= 1e6) return (v / 1e6).toFixed(2) + "M";
  if (v >= 1e3) return (v / 1e3).toFixed(2) + "K";
  return String(Math.round(v));
}
```

Jika data harian 404 (belum fetch), kolom tampil "-" dan tidak error.

- [ ] **Step 3: Verify passes**

1. Jalankan app, klik scan pasar tanpa file harian → kolom tampil "-".
2. Taruh contoh `data/harian-20261006.json` 2 baris (GOTO + PPRI), refresh, klik scan → nilai Freq/Value muncul dan cocok dengan JSON.

- [ ] **Step 4: Commit**

```bash
git add web/screener-praktis.html
git commit -m "feat: kolom Freq dan Value di screener mode pasar"
```
