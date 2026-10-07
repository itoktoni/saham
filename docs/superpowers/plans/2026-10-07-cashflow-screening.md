# Cashflow Screening Thowilz Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tambah filter kualitas cashflow ala Thomas William (EV/CFO, EV/FCF, CFO>NI 3 tahun, Sloan accrual, badge Lolos/Watchlist/Kill) ke `fetch-data-idx.py` + ranking di `screener-saham-indonesia.html`.

**Architecture:** Fungsi murni tanpa network di `fetch-data-idx.py` (`compute_ev`, `compute_cash_quality`) diisi dari Yahoo TTM di `build_record`, ditimpa angka asli IDX XBRL di `gabung_laporan`; 5 kolom baru di-append di akhir CSV agar impor lama tetap jalan; JS menambah rank EV/CFO + penalti Kill.

**Tech Stack:** Python 3.8+ standard library only, Yahoo Finance quoteSummary + IDX XBRL xlsx, vanilla JS HTML, test via `python tests/test-*.py` tanpa pytest.

## Global Constraints

- Python 3.8+, HANYA standard library, tanpa pustaka tambahan.
- CSV backward compat: 31 kolom inti + 12 kolom tambahan tetap, 5 kolom baru WAJIB di akhir setelah `hist_laba`.
- Jeda Yahoo bawaan 1.5s (`--delay 1.5`), jangan turunkan di bawah 1.0s.
- Sektor `Keuangan` dikecualikan dari Sloan kill (flag Watchlist saja, bukan Kill).
- EV = MarketCap + TotalDebt - TotalCash, bila MarketCap <= 0 maka EV = None.
- EV/CFO dan EV/FCF hanya bila pembagi > 0, selain itu None -> CSV kosong.
- Sloan = (NI_TTM - CFO_TTM) / TotalAssets, kill bila > 0.10 sekali atau > 0.05 dua tahun beruntun (non-Keuangan).

---

### Task 1: Fungsi murni cash-quality + unit test

**Files:**
- Create: `tests/test-cash-quality.py`
- Modify: `scripts/fetch-data-idx.py:1-60` (tambah 2 fungsi murni setelah `clean()`)

**Interfaces:**
- Consumes: tidak ada (murni).
- Produces: `compute_ev(market_cap: float, total_debt: float, total_cash: float) -> float | None`; `compute_cash_quality(hist: list, total_assets: float, sektor: str) -> dict` dengan `hist` = list `(tahun:int, laba:float, cfo:float)` urut naik, return `{"cfo3": int, "sloan": float|None, "badge": str, "alasan": str}` badge salah satu `Lolos|Watchlist|Kill|-`.

- [ ] **Step 1: Write the failing test**

```python
"""Test cashflow Thowilz. Jalan tanpa pytest: python tests/test-cash-quality.py"""
import importlib.util
_spec = importlib.util.spec_from_file_location("m_idx", "scripts/fetch-data-idx.py")
m_idx = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m_idx)

def test_compute_ev():
    assert m_idx.compute_ev(100.0, 20.0, 30.0) == 90.0
    assert m_idx.compute_ev(0, 20.0, 5.0) is None
    assert m_idx.compute_ev(100.0, 0, 0) == 100.0

def test_cfo3_lolos():
    hist = [(2022, 100.0, 120.0), (2023, 110.0, 130.0), (2024, 120.0, 150.0)]
    out = m_idx.compute_cash_quality(hist, 1000.0, "Energi")
    assert out["cfo3"] == 1, out
    assert out["badge"] == "Lolos", out

def test_sloan_kill():
    hist = [(2022, 200.0, 190.0), (2023, 210.0, 50.0), (2024, 220.0, 40.0)]
    out = m_idx.compute_cash_quality(hist, 1000.0, "Energi")
    assert out["badge"] == "Kill", out
    assert out["sloan"] is not None and out["sloan"] > 0.10

def test_bank_tidak_dikill():
    hist = [(2022, 200.0, 190.0), (2023, 210.0, 50.0), (2024, 220.0, 40.0)]
    out = m_idx.compute_cash_quality(hist, 1000.0, "Keuangan")
    assert out["badge"] != "Kill", out

def test_data_kurang():
    out = m_idx.compute_cash_quality([(2024, 10.0, 12.0)], 100.0, "Energi")
    assert out["badge"] == "-", out
    assert out["cfo3"] == 0

if __name__ == "__main__":
    test_compute_ev()
    test_cfo3_lolos()
    test_sloan_kill()
    test_bank_tidak_dikill()
    test_data_kurang()
    print("cash-quality OK: 5 passed")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python tests/test-cash-quality.py`
Expected: FAIL with `AttributeError: module has no attribute 'compute_ev'`

- [ ] **Step 3: Write minimal implementation**

```python
def compute_ev(market_cap, total_debt, total_cash):
    """EV = MarketCap + TotalDebt - TotalCash. None bila MarketCap <= 0."""
    try:
        mc = float(market_cap or 0)
        db = float(total_debt or 0)
        cs = float(total_cash or 0)
    except (TypeError, ValueError):
        return None
    if mc <= 0:
        return None
    return mc + db - cs


def compute_cash_quality(hist, total_assets, sektor):
    """hist: [(tahun, laba, cfo)] urut bebas. Return cfo3/sloan/badge/alasan."""
    pts = sorted([(t, l, c) for t, l, c in (hist or []) if t is not None], key=lambda p: p[0])
    if len(pts) < 3:
        return {"cfo3": 0, "sloan": None, "badge": "-", "alasan": "riwayat <3 tahun"}
    last3 = pts[-3:]
    cfo3 = 0
    if all((c is not None and l is not None and c > 0 and c > l) for _, l, c in last3):
        cfo3 = 1
    sloan = None
    try:
        _, ni, cfo = pts[-1]
        ta = float(total_assets or 0)
        if ni is not None and cfo is not None and ta > 0:
            sloan = (float(ni) - float(cfo)) / ta
    except (TypeError, ValueError):
        sloan = None
    # streak sloan 2 tahun
    streak = 0
    for _, l, c in pts[-2:]:
        try:
            ta = float(total_assets or 0)
            s = (float(l) - float(c)) / ta if (l is not None and c is not None and ta > 0) else None
        except (TypeError, ValueError):
            s = None
        if s is not None and s > 0.05:
            streak += 1
    is_bank = (sektor or "").strip().lower() == "keuangan"
    if sloan is not None and (sloan > 0.10 or streak >= 2) and not is_bank:
        return {"cfo3": cfo3, "sloan": round(sloan, 4), "badge": "Kill", "alasan": "akrual tinggi (Sloan %.2f)" % sloan}
    if cfo3 == 0 or (sloan is not None and sloan > 0.05):
        why = "CFO tidak > laba 3thn" if cfo3 == 0 else ("akrual waspada (bank)" if is_bank else "akrual waspada")
        return {"cfo3": cfo3, "sloan": round(sloan, 4) if sloan is not None else None, "badge": "Watchlist", "alasan": why}
    return {"cfo3": cfo3, "sloan": round(sloan, 4) if sloan is not None else None, "badge": "Lolos", "alasan": "CFO selaras laba"}
```

Letak: tempel tepat setelah fungsi `clean()` di `scripts/fetch-data-idx.py`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python tests/test-cash-quality.py`
Expected: PASS `cash-quality OK: 5 passed`

- [ ] **Step 5: Commit**

```bash
git add scripts/fetch-data-idx.py tests/test-cash-quality.py
git commit -m "feat: tambah compute_ev dan compute_cash_quality + test"
```

### Task 2: Isi EV/CFO dan EV/FCF Yahoo di build_record

**Files:**
- Modify: `scripts/fetch-data-idx.py:485-617` (`build_record`)
- Test: `tests/test-cash-quality.py` (tambah 1 fungsi test)

**Interfaces:**
- Consumes: `compute_ev`, `compute_cash_quality` dari Task 1; `fd.financialData.totalDebt/totalCash/operatingCashflow/freeCashflow`, `ks.sharesOutstanding`, `harga`.
- Produces: `rec["ev_cfo"]`, `rec["ev_fcf"]`, `rec["cfo3"]`, `rec["sloan"]`, `rec["cash_badge"]` (float/int/str, None bila tak terhitung).

- [ ] **Step 1: Write the failing test**

```python
def test_build_record_ev():
    fund = {
        "price": {"regularMarketPrice": {"raw": 1000}},
        "summaryDetail": {}, "assetProfile": {},
        "defaultKeyStatistics": {"sharesOutstanding": {"raw": 10}, "bookValue": {"raw": 500}, "trailingEps": {"raw": 100}, "netIncomeToCommon": {"raw": 1000}},
        "financialData": {"totalDebt": {"raw": 2000}, "totalCash": {"raw": 500}, "operatingCashflow": {"raw": 1500}, "freeCashflow": {"raw": 800}},
        "incomeStatementHistoryQuarterly": {"incomeStatementHistory": []},
    }
    rec = m_idx.build_record("ZZZ", {"nama": "Z", "sektor": "Energi"}, fund, None, None)
    assert rec["ev_cfo"] == round((1000*10+2000-500)/1500, 2), rec
    assert rec["ev_fcf"] == round((1000*10+2000-500)/800, 2), rec
    assert rec["cash_badge"] in ("Lolos", "Watchlist", "Kill", "-")
```

Tambahkan ke `tests/test-cash-quality.py` + panggil di `__main__`, hitung jadi 6 passed.

- [ ] **Step 2: Run test to verify it fails**

Run: `python tests/test-cash-quality.py`
Expected: FAIL `KeyError: 'ev_cfo'`

- [ ] **Step 3: Write minimal implementation**

Di `build_record`, setelah blok `der = ...` tambah:

```python
    mcap = harga * shares if (harga > 0 and shares > 0) else 0.0
    ev = compute_ev(mcap, utang, kas)
    ocf = num(fd.get("operatingCashflow"), None)
    fcf_y = num(fd.get("freeCashflow"), None)
    ev_cfo = round(ev / ocf, 2) if (ev is not None and ocf is not None and ocf > 0) else None
    ev_fcf = round(ev / fcf_y, 2) if (ev is not None and fcf_y is not None and fcf_y > 0) else None
```

Di `return {...}` tambah 5 kunci:

```python
        "ev_cfo": ev_cfo,
        "ev_fcf": ev_fcf,
        "cfo3": 0,
        "sloan": None,
        "cash_badge": "-",
```

Catatan: `cfo3/sloan/badge` Yahoo-only dibiarkan `-` bila tanpa histori; diisi penuh oleh Task 3 dari IDX.

- [ ] **Step 4: Run test to verify it passes**

Run: `python tests/test-cash-quality.py`
Expected: PASS `6 passed`

- [ ] **Step 5: Commit**

```bash
git add scripts/fetch-data-idx.py tests/test-cash-quality.py
git commit -m "feat: isi EV/CFO dan EV/FCF Yahoo di build_record"
```

### Task 3: Override IDX asli + extend CSV_HEADER

**Files:**
- Modify: `scripts/fetch-data-idx.py:88-99` (`CSV_HEADER`), `scripts/fetch-data-idx.py:1769-1855` (`gabung_laporan`)
- Test: `tests/test-cash-quality.py` (tambah test gabung_laporan)

**Interfaces:**
- Consumes: `lap_tahun: list[dict]` dengan kunci `tahun, laba, arus_kas_operasi, aset`; `rec` dari Task 2.
- Produces: `rec` ter-update + `rec["hist_cfo"]` tidak perlu (tetap 5 kolom baru); CSV kolom baru `ev_cfo,ev_fcf,cfo3,sloan,cash_badge`.

- [ ] **Step 1: Write the failing test**

```python
def test_gabung_laporan_cash():
    rec = {"ekuitas": 1, "laba": 0, "eps": 0, "kuartal": 4, "fcf": 0, "kas": 0, "utang": 0, "der": 0, "sektor": "Energi", "cyclical": 0, "ev_cfo": None, "ev_fcf": None, "cfo3": 0, "sloan": None, "cash_badge": "-", "_catatan": []}
    lap = [
        {"tahun": 2024, "laba": 120e9, "arus_kas_operasi": 150e9, "aset": 1000e9, "ekuitas": 500e9, "liabilitas": 500e9, "kas": 50e9, "pendapatan": 1e12, "eps": 100, "pembulatan": "Satuan", "skala": 1.0},
        {"tahun": 2023, "laba": 110e9, "arus_kas_operasi": 130e9, "aset": 900e9, "ekuitas": 450e9, "liabilitas": 450e9, "kas": 40e9, "pendapatan": 9e11, "eps": 90, "pembulatan": "Satuan", "skala": 1.0},
        {"tahun": 2022, "laba": 100e9, "arus_kas_operasi": 120e9, "aset": 800e9, "ekuitas": 400e9, "liabilitas": 400e9, "kas": 30e9, "pendapatan": 8e11, "eps": 80, "pembulatan": "Satuan", "skala": 1.0},
    ]
    out, _ = m_idx.gabung_laporan(rec, lap)
    assert out["cfo3"] == 1, out
    assert out["cash_badge"] == "Lolos", out
    assert "ev_cfo" in out and "ev_fcf" in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python tests/test-cash-quality.py`
Expected: FAIL `AssertionError` (cfo3 masih 0)

- [ ] **Step 3: Write minimal implementation**

1. `CSV_HEADER`: tambah di akhir list setelah `"hist_laba"`:

```python
    "piotroski", "rs_rating", "altman_z", "interest_cov", "current_ratio",
    "quick_ratio", "roic", "roce", "ev_ebitda", "peg", "div_yield", "hist_laba",
    "ev_cfo", "ev_fcf", "cfo3", "sloan", "cash_badge",
]
```

2. Di `gabung_laporan`, sebelum `rec["sumber"] = ...` tambah:

```python
    hist_cf = [(x["tahun"], x.get("laba"), x.get("arus_kas_operasi"))
               for x in lap_tahun if x.get("laba") is not None and x.get("arus_kas_operasi") is not None]
    if len(hist_cf) >= 3:
        aset_ttm = kini.get("aset") or 0
        q = compute_cash_quality(hist_cf, aset_ttm, rec.get("sektor") or "")
        rec["cfo3"] = q["cfo3"]
        rec["sloan"] = q["sloan"]
        rec["cash_badge"] = q["badge"]
        if q["badge"] == "Kill":
            catatan.append("kas: %s" % q["alasan"])
    # hitung ulang EV/CFO dengan CFO IDX bila EV Yahoo ada
    try:
        mcap_now = float(rec.get("harga") or 0) * float(rec.get("saham") or 0)
    except (TypeError, ValueError):
        mcap_now = 0
    ev_now = compute_ev(mcap_now, rec.get("utang") or 0, rec.get("kas") or 0)
    cfo_now = kini.get("arus_kas_operasi")
    if ev_now is not None and cfo_now is not None and cfo_now > 0:
        rec["ev_cfo"] = round(ev_now / float(cfo_now), 2)
```

`tulis_csv` tidak diubah (loop `CSV_HEADER` otomatis menulis kolom baru; `bidang_csv(None)` jadi string kosong).

- [ ] **Step 4: Run test to verify it passes**

Run: `python tests/test-cash-quality.py`
Expected: PASS `7 passed`

Run regresi: `python tests/test-harian.py`
Expected: PASS `Task3 OK: 4 passed`

- [ ] **Step 5: Commit**

```bash
git add scripts/fetch-data-idx.py tests/test-cash-quality.py
git commit -m "feat: override cash-quality IDX + 5 kolom CSV baru"
```

### Task 4: Ranking + badge di screener-saham-indonesia.html

**Files:**
- Modify: `web/screener-saham-indonesia.html:2263-2268` (`CSV_HEADER`), `~2391-2399` (parser `n/b`), `~743-761` (rank + total), `~1569-1598` (panel detail), `~1634` (kolom tabel)

**Interfaces:**
- Consumes: CSV/JSON dengan `ev_cfo,ev_fcf,cfo3,sloan,cash_badge`.
- Produces: `r.rank.evcfo`, `r.rank.cashkill`, `r.total` termasuk keduanya; badge di tabel + panel.

- [ ] **Step 1: Write the failing test**

Buat `tests/_test-cash-ui.js`, run `node tests/_test-cash-ui.js`:

```js
const fs = require("fs");
const html = fs.readFileSync("web/screener-saham-indonesia.html", "utf8");
for (const k of ["ev_cfo", "ev_fcf", "cfo3", "sloan", "cash_badge"]) {
  if (!html.includes(k)) throw new Error("kolom hilang: " + k);
}
if (!html.includes("evcfo") && !html.includes("ev_cfo")) throw new Error("rank evcfo hilang");
console.log("cash-ui OK");
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node tests/_test-cash-ui.js`
Expected: FAIL `kolom hilang: ev_cfo`

- [ ] **Step 3: Write minimal implementation**

1. `CSV_HEADER` JS tambah 5 nama sama persis di akhir setelah `"hist_laba"`.
2. Parser (dekat `fcf: n("fcf")`): tambah `evCfo: n("ev_cfo"), evFcf: n("ev_fcf"), cfo3: n("cfo3"), sloan: n("sloan"), cashBadge: s("cash_badge")` dengan helper `s = (k) => (row[k] != null ? String(row[k]) : "")` bila belum ada; bila parser memakai indeks, ikuti pola `n()`/`b()` yang ada.
3. Ranking (dekat `rankBy`): `const rV = rankBy(r => (r.F.evCfo > 0 ? r.F.evCfo : 1e9), 1)` kecil terbaik; `cashkill = (r.F.cashBadge === "Kill" ? 1000 : r.F.cashBadge === "Watchlist" ? 200 : 1)`; tambah ke `r.total = ... + rV.get + cashkill`. Basis peringkat tetap emiten lolos filter (ikuti komentar `Hanya emiten yang lolos filter`).
4. Tabel + panel: tambah kolom `EV/CFO` (`fmt(s.evCfo,1)` atau `—`) dan badge `Kas` (`Lolos hijau / Watchlist kuning / Kill merah / — abu`); panel detail tambah baris `EV/CFO`, `EV/FCF`, `CFO>NI 3thn (Ya/Tidak)`, `Sloan`, `Badge kas`.

- [ ] **Step 4: Run test to verify it passes**

Run: `node tests/_test-cash-ui.js`
Expected: PASS `cash-ui OK`

Run impor manual: buka `web/screener-saham-indonesia.html`, impor `data/data-idx.csv` lama (31+12 kolom) — harus tetap jalan, kolom baru tampil `—`.

- [ ] **Step 5: Commit**

```bash
git add web/screener-saham-indonesia.html tests/_test-cash-ui.js
git commit -m "feat: ranking EV/CFO + badge kas di UI"
```

### Task 5: Verifikasi E2E fixture + regresi

**Files:**
- Modify: tidak ada (verifikasi saja); bila perlu betulkan ambang di `scripts/fetch-data-idx.py`.
- Test: `python tests/test-cash-quality.py`, `python tests/test-harian.py`, `node tests/_test-praktis.js`, `node tests/_test-cash-ui.js`

**Interfaces:**
- Consumes: semua Task 1-4.
- Produces: CSV baru terisi + tidak ada regresi impor lama.

- [ ] **Step 1: Tarik 3 ticker uji**

```bash
python scripts/fetch-data-idx.py --tickers BBCA,ANTM,ICBP --laporan --laporan-tahun 2022-2024 --no-pasar --ringkas
```

Harap: kolom `ev_cfo,ev_fcf,cfo3,sloan,cash_badge` terisi di `data/data-idx.csv`; BBCA (Keuangan) tidak pernah `Kill`.

- [ ] **Step 2: Cek CSV manual**

```bash
python -c "import csv; r=list(csv.DictReader(open('data/data-idx.csv',encoding='utf-8-sig'))); print([(x['kode'],x['ev_cfo'],x['cfo3'],x['sloan'],x['cash_badge']) for x in r])"
```

Harap: tiap baris punya 5 kolom baru (boleh kosong bila data kurang, tapi header ada).

- [ ] **Step 3: Run semua regresi**

```bash
python tests/test-cash-quality.py
python tests/test-harian.py
node tests/_test-praktis.js
node tests/_test-cash-ui.js
```

Harap: semua PASS. Bila `test-praktis.js` butuh browser, cukup pastikan tidak error impor CSV.

- [ ] **Step 4: Commit (bila ada perbaikan ambang)**

```bash
git add -A
git commit -m "fix: selaraskan ambang cash-quality E2E" || echo "tidak ada perubahan"
```

## Self-Review

- Spec coverage: EV/CFO -> Task 2+3; EV/FCF -> Task 2; CFO vs laba 3thn -> Task 1+3; Sloan -> Task 1+3; pricing power/margin & PEG tidak diwajibkan di пригод ini (sudah ada `peg`, margin via existing) — sengaja di luar scope terkecil.
- Placeholder scan: tidak ada TBD/TODO; semua langkah punya kode + perintah run + expected.
- Type consistency: `compute_ev -> float|None`, `compute_cash_quality -> dict{cfo3:int,sloan:float|None,badge:str}` dipakai sama di Task 2-3; JS `evCfo/cashBadge` konsisten dengan CSV `ev_cfo/cash_badge`.
