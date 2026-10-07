# Thowilz Full Scoring (Fase 2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lengkapi semua pilar scoring Thomas William yang belum ada (PEG-CFO, pricing power via stabilitas gross margin, klasifikasi 5 kategori, penalti capex-intensity, skor komposit Thowilz 0-100 + checklist 4 pilar di UI).

**Architecture:** Lima fungsi murni baru di `scripts/fetch-data-idx.py` (margin, CFO CAGR, PEG-CFO, klasifikasi, skor komposit); data margin tahunan dari modul Yahoo `incomeStatementHistory` (terbukti ada `grossProfit`+`totalRevenue` 4 tahun untuk ICBP.JK); CFO CAGR hanya dari histori IDX (Yahoo `cashflowStatementHistory` untuk IDX kosong — sudah dibuktikan live); 7 kolom CSV baru di-append; UI tambah 2 kolom + panel checklist (Thowilz TIDAK masuk rank total agar tidak mengaduk peringkat lama).

**Tech Stack:** Python 3.8+ standard library only, Yahoo Finance quoteSummary, IDX XBRL, vanilla JS, test via `python tests/test-*.py` + `node tests/_test-*.js`.

## Global Constraints

- Python 3.8+, HANYA standard library, tanpa pustaka tambahan.
- CSV backward compat: 48 kolom lama tetap, 7 kolom baru WAJIB di akhir setelah `cash_badge`, urutan: `peg_cfo,cfo_cagr,gross_margin,margin_stabil,capex_inten,klasifikasi,thowilz`.
- Jeda Yahoo bawaan 1.5s, jangan turunkan di bawah 1.0s.
- Sektor `Keuangan` dikecualikan dari Sloan kill (aturan fase 1, jangan diubah).
- `incomeStatementHistory` (tahunan) DITAMBAH ke `YAHOO_MODULES`; `cashflowStatementHistory` TERBUKTI kosong untuk IDX — jangan dipakai.
- Margin disimpan sebagai PERSEN 1 desimal di CSV; fungsi murni memakai FRAKSI.
- Klasifikasi satu label, preseden: Turnaround > AssetPlay > FastGrowing > Cyclical > Stalwart > "-".

---

### Task 1: Margin tahunan Yahoo + pricing power

**Files:**
- Modify: `scripts/fetch-data-idx.py:78-81` (`YAHOO_MODULES`), `scripts/fetch-data-idx.py:540-541` (parse `ih`), `scripts/fetch-data-idx.py:629-666` (`build_record` return)
- Test: `tests/test-cash-quality.py` (tambah test, total jadi 10)

**Interfaces:**
- Consumes: `fund["incomeStatementHistory"]["incomeStatementHistory"]` (list dict Yahoo dengan `totalRevenue`, `grossProfit`, `endDate.raw`).
- Produces: `compute_margin_quality(margins: list[float]) -> {"gross_margin": float|None, "margin_stabil": 0|1}`; `margins` = fraksi laba kotor per tahun urut naik; `rec["gross_margin"]` (persen|None), `rec["margin_stabil"]` (0/1).

- [ ] **Step 1: Write the failing test**

```python
def test_margin_stabil():
    out = m_idx.compute_margin_quality([0.44, 0.45, 0.46, 0.45])
    assert out["margin_stabil"] == 1, out
    assert out["gross_margin"] == 45.0, out

def test_margin_longor():
    out = m_idx.compute_margin_quality([0.45, 0.30, 0.15])
    assert out["margin_stabil"] == 0, out

def test_margin_kurang():
    out = m_idx.compute_margin_quality([0.45, 0.46])
    assert out["margin_stabil"] == 0 and out["gross_margin"] == 46.0, out
```

Tambahkan 3 fungsi + 3 panggilan di `__main__`, ubah pesan jadi `cash-quality OK: 10 passed`.

- [ ] **Step 2: Run test to verify it fails**

Run: `python tests/test-cash-quality.py`
Expected: FAIL with `AttributeError: module has no attribute 'compute_margin_quality'`

- [ ] **Step 3: Write minimal implementation**

Tempel setelah `compute_cash_quality` (sebelum header `# HTTP`):

```python
def compute_margin_quality(margins):
    """margins: fraksi laba kotor per tahun, urut bebas. Stabil bila >=3 thn,
    semua >0, dan rentang <=8pp (proksi pricing power Thowilz)."""
    ms = [float(x) for x in (margins or []) if x is not None]
    if not ms:
        return {"gross_margin": None, "margin_stabil": 0}
    stabil = 0
    if len(ms) >= 3 and min(ms) > 0 and (max(ms) - min(ms)) <= 0.08:
        stabil = 1
    return {"gross_margin": round(ms[-1] * 100.0, 1), "margin_stabil": stabil}
```

`YAHOO_MODULES`: tambah `"incomeStatementHistory"` setelah `"incomeStatementHistoryQuarterly"`.

Di `build_record`, setelah blok `iq` tambah:

```python
    ih = (((fund or {}).get("incomeStatementHistory") or {})
          .get("incomeStatementHistory") or [])
    margins = []
    for y in sorted(ih, key=lambda z: num((z.get("endDate") or {}).get("raw"), 0)):
        rev = num(y.get("totalRevenue"), None)
        gp = num(y.get("grossProfit"), None)
        if rev is not None and rev > 0 and gp is not None:
            margins.append(gp / rev)
    mq = compute_margin_quality(margins[-4:])
```

Di `return {...}` tambah: `"gross_margin": mq["gross_margin"], "margin_stabil": mq["margin_stabil"],`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python tests/test-cash-quality.py`
Expected: PASS `cash-quality OK: 10 passed`

Run: `python tests/test-harian.py`
Expected: PASS `Task3 OK: 4 passed`

- [ ] **Step 5: Commit**

```bash
git add scripts/fetch-data-idx.py tests/test-cash-quality.py
git commit -m "feat: margin tahunan Yahoo + pricing power stabil"
```

### Task 2: Fungsi murni CAGR, PEG-CFO, klasifikasi, skor komposit

**Files:**
- Modify: `scripts/fetch-data-idx.py` (5 fungsi baru setelah `compute_margin_quality`)
- Test: `tests/test-cash-quality.py` (tambah 4 test, total 14)

**Interfaces:**
- Consumes: `compute_ev`, `compute_cash_quality`, `compute_margin_quality` (Task fase 1 + Task 1).
- Produces: `compute_cfo_cagr(hist_cf) -> float|None` (fraksi); `compute_peg_cfo(ev_cfo, cagr) -> float|None`; `compute_klasifikasi(sektor, cagr_earn, dividen, der, laba_hist, net_cash_mcap) -> str`; `compute_thowilz(ev_cfo, peg_cfo, badge, margin_stabil, klasifikasi, hist_years, spring, sideways) -> {"thowilz": int, "rincian": dict}`.

- [ ] **Step 1: Write the failing test**

```python
def test_cfo_cagr():
    assert m_idx.compute_cfo_cagr([(2022, 0, 100.0), (2023, 0, 121.0), (2024, 0, 146.4)]) == 0.21
    assert m_idx.compute_cfo_cagr([(2022, 0, 100.0), (2024, 0, -5.0)]) is None
    assert m_idx.compute_cfo_cagr([(2024, 0, 10.0)]) is None

def test_peg_cfo():
    assert m_idx.compute_peg_cfo(10.0, 0.30) == 0.33
    assert m_idx.compute_peg_cfo(None, 0.30) is None
    assert m_idx.compute_peg_cfo(10.0, 0) is None

def test_klasifikasi():
    assert m_idx.compute_klasifikasi("Energi", 5.0, 0, 0.5, [(2023, -10.0), (2024, 20.0)], None) == "Turnaround"
    assert m_idx.compute_klasifikasi("Energi", 25.0, 0, 0.5, [(2023, 10.0), (2024, 20.0)], None) == "FastGrowing"
    assert m_idx.compute_klasifikasi("Energi", 5.0, 0, 0.5, [(2023, 10.0), (2024, 20.0)], None) == "Cyclical"
    assert m_idx.compute_klasifikasi("Konsumer Primer", 5.0, 1, 0.5, [(2023, 10.0), (2024, 20.0)], None) == "Stalwart"
    assert m_idx.compute_klasifikasi("Konsumer Primer", 5.0, 0, 0.5, [(2023, 10.0), (2024, 20.0)], 0.5) == "AssetPlay"
    assert m_idx.compute_klasifikasi("Konsumer Primer", 5.0, 0, 2.0, [(2023, 10.0), (2024, 20.0)], None) == "-"

def test_thowilz():
    out = m_idx.compute_thowilz(8.0, 0.5, "Lolos", 1, "FastGrowing", 5, 1, 0)
    assert out["thowilz"] == 100, out
    out2 = m_idx.compute_thowilz(None, None, "Kill", 0, "-", 1, 0, 0)
    assert out2["thowilz"] < 30, out2
```

Ubah pesan jadi `cash-quality OK: 14 passed` + 4 panggilan.

- [ ] **Step 2: Run test to verify it fails**

Run: `python tests/test-cash-quality.py`
Expected: FAIL with `AttributeError: module has no attribute 'compute_cfo_cagr'`

- [ ] **Step 3: Write minimal implementation**

```python
def compute_cfo_cagr(hist_cf):
    """CAGR CFO dari [(tahun, laba, cfo)] urut bebas. None bila <2 titik atau
    titik awal/akhir tidak positif."""
    pts = sorted([(t, c) for t, _, c in (hist_cf or []) if t is not None], key=lambda p: p[0])
    if len(pts) < 2:
        return None
    awal, akhir = pts[0][1], pts[-1][1]
    tahun = pts[-1][0] - pts[0][0]
    if awal is None or akhir is None or awal <= 0 or akhir <= 0 or tahun <= 0:
        return None
    return round((akhir / awal) ** (1.0 / tahun) - 1.0, 4)


def compute_peg_cfo(ev_cfo, cagr):
    """PEG-CFO = EV/CFO dibagi pertumbuhan CFO (%). Ambang sama seperti PEG
    Thowilz: <1.0 murah, >1.5 mahal. None bila tak terhitung."""
    try:
        ev = float(ev_cfo) if ev_cfo is not None else None
        g = float(cagr) if cagr is not None else None
    except (TypeError, ValueError):
        return None
    if ev is None or g is None or ev <= 0 or g <= 0:
        return None
    return round(ev / (g * 100.0), 2)


def compute_klasifikasi(sektor, cagr_earn, dividen, der, laba_hist, net_cash_mcap):
    """Satu label Thowilz. Preseden: Turnaround > AssetPlay > FastGrowing >
    Cyclical > Stalwart > '-'. cagr_earn dalam persen (mis. 25.0)."""
    lh = sorted([(t, v) for t, v in (laba_hist or []) if t is not None], key=lambda p: p[0])
    if len(lh) >= 2 and lh[-2][1] is not None and lh[-1][1] is not None:
        if lh[-2][1] < 0 < lh[-1][1]:
            return "Turnaround"
    if net_cash_mcap is not None and net_cash_mcap > 0.3:
        return "AssetPlay"
    if cagr_earn is not None and cagr_earn > 20:
        return "FastGrowing"
    if (sektor or "") in SEKTOR_CYCLICAL:
        return "Cyclical"
    try:
        d = float(der or 0)
    except (TypeError, ValueError):
        d = 99.0
    if dividen == 1 and d < 1:
        return "Stalwart"
    return "-"


def compute_thowilz(ev_cfo, peg_cfo, badge, margin_stabil, klasifikasi, hist_years, spring, sideways):
    """Skor komposit 0-100. Valuasi 35 + Kualitas 35 + Tesis 15 + Timing 15.
    Timing memakai sinyal chart yang sudah ada (spring ~ SOS, sideways ~ serapan)."""
    try:
        ev = float(ev_cfo) if ev_cfo not in (None, "") else None
    except (TypeError, ValueError):
        ev = None
    v = 25 if (ev is not None and ev <= 10) else (18 if (ev is not None and ev <= 15) else (10 if (ev is not None and ev <= 20) else (4 if (ev is not None and ev > 0) else 0)))
    try:
        pg = float(peg_cfo) if peg_cfo not in (None, "") else None
    except (TypeError, ValueError):
        pg = None
    v += 10 if (pg is not None and pg < 1) else (5 if (pg is not None and pg < 1.5) else 0)
    k = {"Lolos": 28, "Watchlist": 12, "Kill": 0}.get(badge, 10) + (7 if margin_stabil else 0)
    t = (10 if klasifikasi not in (None, "", "-") else 3) + (5 if (hist_years or 0) >= 4 else 0)
    m = 15 if spring else (10 if sideways else 5)
    total = min(100, v + k + t + m)
    return {"thowilz": int(total), "rincian": {"valuasi": v, "kualitas": k, "tesis": t, "timing": m}}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python tests/test-cash-quality.py`
Expected: PASS `cash-quality OK: 14 passed`

- [ ] **Step 5: Commit**

```bash
git add scripts/fetch-data-idx.py tests/test-cash-quality.py
git commit -m "feat: fungsi murni CAGR, PEG-CFO, klasifikasi, skor Thowilz"
```

### Task 3: Wiring build_record + gabung_laporan + CSV

**Files:**
- Modify: `scripts/fetch-data-idx.py` (`build_record` EV/capex/klasifikasi/thowilz, `gabung_laporan` override IDX, `CSV_HEADER` +7)
- Test: `tests/test-cash-quality.py` (tambah 2 test integrasi, total 16)

**Interfaces:**
- Consumes: semua fungsi Task 1-2; `rec["s_sideways"]`, `rec["s_spring"]` (sinyal chart).
- Produces: `rec` dengan `peg_cfo, cfo_cagr, gross_margin, margin_stabil, capex_inten, klasifikasi, thowilz`.

- [ ] **Step 1: Write the failing test**

```python
def test_wire_yahoo_thowilz():
    fund = {
        "price": {"regularMarketPrice": {"raw": 1000}},
        "summaryDetail": {}, "assetProfile": {},
        "defaultKeyStatistics": {"sharesOutstanding": {"raw": 10}, "bookValue": {"raw": 500}, "trailingEps": {"raw": 100}, "netIncomeToCommon": {"raw": 1000}},
        "financialData": {"totalDebt": {"raw": 2000}, "totalCash": {"raw": 500}, "operatingCashflow": {"raw": 1500}, "freeCashflow": {"raw": 800}, "earningsGrowth": {"raw": 0.25}},
        "incomeStatementHistoryQuarterly": {"incomeStatementHistory": []},
        "incomeStatementHistory": {"incomeStatementHistory": [
            {"endDate": {"raw": 3}, "totalRevenue": {"raw": 1000}, "grossProfit": {"raw": 450}},
            {"endDate": {"raw": 2}, "totalRevenue": {"raw": 900}, "grossProfit": {"raw": 405}},
            {"endDate": {"raw": 1}, "totalRevenue": {"raw": 800}, "grossProfit": {"raw": 360}}]},
    }
    rec = m_idx.build_record("ZZZ", {"nama": "Z", "sektor": "Energi"}, fund, None, None)
    assert rec["margin_stabil"] == 1 and rec["gross_margin"] == 45.0, rec
    assert rec["capex_inten"] == round((1500-800)/1500, 3), rec
    assert rec["klasifikasi"] == "FastGrowing", rec
    assert rec["thowilz"] >= 50, rec

def test_wire_idx_thowilz():
    rec = {"harga": 1000, "ekuitas": 1, "laba": 0, "eps": 0, "kuartal": 4, "fcf": 0, "kas": 50000.0, "utang": 50000.0, "der": 1.0, "saham": 10, "sektor": "Energi", "cyclical": 1, "cagr": 5.0, "dividen": 0, "ev_cfo": 8.0, "ev_fcf": None, "cfo3": 0, "sloan": None, "cash_badge": "-", "s_sideways": 1, "s_spring": 0, "gross_margin": None, "margin_stabil": 0, "capex_inten": None, "peg_cfo": None, "cfo_cagr": None, "klasifikasi": "-", "thowilz": 0, "_catatan": []}
    lap = [
        {"tahun": 2024, "laba": 120e9, "arus_kas_operasi": 150e9, "aset": 1000e9, "ekuitas": 500e9, "liabilitas": 500e9, "kas": 50e9, "pendapatan": 1e12, "eps": 100, "pembulatan": "Satuan", "skala": 1.0},
        {"tahun": 2023, "laba": 110e9, "arus_kas_operasi": 130e9, "aset": 900e9, "ekuitas": 450e9, "liabilitas": 450e9, "kas": 40e9, "pendapatan": 9e11, "eps": 90, "pembulatan": "Satuan", "skala": 1.0},
        {"tahun": 2022, "laba": 100e9, "arus_kas_operasi": 100e9, "aset": 800e9, "ekuitas": 400e9, "liabilitas": 400e9, "kas": 30e9, "pendapatan": 8e11, "eps": 80, "pembulatan": "Satuan", "skala": 1.0},
    ]
    out, _ = m_idx.gabung_laporan(rec, lap)
    assert out["cfo_cagr"] == round(((150e9/100e9) ** (1/2) - 1) * 100, 1), out
    assert out["peg_cfo"] is not None and out["peg_cfo"] < 1.5, out
    assert out["klasifikasi"] == "Cyclical", out
    assert out["thowilz"] >= 60, out
```

Ubah pesan jadi `cash-quality OK: 16 passed` + 2 panggilan.

- [ ] **Step 2: Run test to verify it fails**

Run: `python tests/test-cash-quality.py`
Expected: FAIL with `KeyError: 'margin_stabil'`

- [ ] **Step 3: Write minimal implementation**

1. `CSV_HEADER`: tambah setelah `"cash_badge"`: `"peg_cfo", "cfo_cagr", "gross_margin", "margin_stabil", "capex_inten", "klasifikasi", "thowilz",`.

2. `build_record`, setelah blok `ev_cfo/ev_fcf`, tambah:

```python
    capex_inten = (round((ocf - fcf_y) / ocf, 3)
                   if (ocf is not None and fcf_y is not None and ocf > 0) else None)
    net_cash_mcap = ((kas - utang) / mcap) if mcap > 0 else None
    klas = compute_klasifikasi(sektor, cagr, dividen, der, [], net_cash_mcap)
    tw = compute_thowilz(ev_cfo, None, "-", mq["margin_stabil"], klas, 0,
                         sw["s_spring"], sw["s_sideways"])
```

`cagr` = variabel growth persen yang sudah ada; bila `growth is None` maka `cagr_earn=None`:

```python
    cagr_earn = cagr if growth is not None else None
```

pakai `cagr_earn` di `compute_klasifikasi`. Di `return` tambah:

```python
        "peg_cfo": None,
        "cfo_cagr": None,
        "gross_margin": mq["gross_margin"],
        "margin_stabil": mq["margin_stabil"],
        "capex_inten": capex_inten,
        "klasifikasi": klas,
        "thowilz": tw["thowilz"],
```

3. `gabung_laporan`, setelah blok kualitas kas IDX (setelah hitung ulang `ev_cfo`), tambah:

```python
    cagr_cf = compute_cfo_cagr(hist_cf) if len(hist_cf) >= 2 else None
    rec["cfo_cagr"] = round(cagr_cf * 100.0, 1) if cagr_cf is not None else None
    rec["peg_cfo"] = compute_peg_cfo(rec.get("ev_cfo"), cagr_cf)
    laba_hist = [(x["tahun"], x.get("laba")) for x in lap_tahun if x.get("laba") is not None]
    try:
        mcap2 = float(rec.get("harga") or 0) * float(rec.get("saham") or 0)
    except (TypeError, ValueError):
        mcap2 = 0
    ncm = ((float(rec.get("kas") or 0) - float(rec.get("utang") or 0)) / mcap2) if mcap2 > 0 else None
    rec["klasifikasi"] = compute_klasifikasi(rec.get("sektor") or "", rec.get("cagr") if rec.get("cagr") else None,
                                             rec.get("dividen") or 0, rec.get("der") or 0, laba_hist, ncm)
    tw2 = compute_thowilz(rec.get("ev_cfo"), rec.get("peg_cfo"), rec.get("cash_badge") or "-",
                          rec.get("margin_stabil") or 0, rec.get("klasifikasi"), len(lap_tahun),
                          rec.get("s_spring") or 0, rec.get("s_sideways") or 0)
    rec["thowilz"] = tw2["thowilz"]
```

`hist_cf` sudah didefinisikan di blok kualitas kas (Task fase 1) — pakai ulang, jangan definisi ganda.

- [ ] **Step 4: Run test to verify it passes**

Run: `python tests/test-cash-quality.py`
Expected: PASS `cash-quality OK: 16 passed`

Run: `python tests/test-harian.py`
Expected: PASS `Task3 OK: 4 passed`

- [ ] **Step 5: Commit**

```bash
git add scripts/fetch-data-idx.py tests/test-cash-quality.py
git commit -m "feat: wiring PEG-CFO, klasifikasi, skor Thowilz + 7 kolom CSV"
```

### Task 4: UI — kolom, checklist 4 pilar, ekspor

**Files:**
- Modify: `web/screener-saham-indonesia.html` (CSV_HEADER JS, `mapStock`, `renderScreen` cols+baris, `panelTambahan` atau panel baru `panelThowilz`, `toRow`, `dashVal`)
- Test: `tests/_test-cash-ui.js` (tambah 7 kunci + panel)

**Interfaces:**
- Consumes: CSV/JSON dengan 7 kolom baru.
- Produces: kolom `Klasifikasi` + `Thowilz`, panel checklist 4 pilar, ekspor round-trip. Thowilz SENGAJA tidak masuk rank total (keputusan desain, hindari churn peringkat).

- [ ] **Step 1: Write the failing test**

Tambah ke `tests/_test-cash-ui.js` sebelum `console.log`:

```js
for (const k of ["peg_cfo", "cfo_cagr", "gross_margin", "margin_stabil", "capex_inten", "klasifikasi", "thowilz"]) {
  if (!html.includes(k)) throw new Error("kolom hilang: " + k);
}
if (!html.includes("thowilz") && !html.includes("Thowilz")) throw new Error("panel Thowilz hilang");
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node tests/_test-cash-ui.js`
Expected: FAIL `kolom hilang: peg_cfo`

- [ ] **Step 3: Write minimal implementation**

1. `CSV_HEADER` JS: tambah `"peg_cfo", "cfo_cagr", "gross_margin", "margin_stabil", "capex_inten", "klasifikasi", "thowilz"` setelah `"cash_badge"`.

2. `mapStock`: tambah sebelum `histLaba: histLaba,`:

```js
    pegCfo: s("peg_cfo") === "" ? null : n("peg_cfo"), cfoCagr: s("cfo_cagr") === "" ? null : n("cfo_cagr"),
    grossMargin: s("gross_margin") === "" ? null : n("gross_margin"), marginStabil: b("margin_stabil"),
    capexInten: s("capex_inten") === "" ? null : n("capex_inten"), klasifikasi: s("klasifikasi") || "-",
    thowilz: n("thowilz"),
```

3. `renderScreen` cols: tambah `"Klas"` + `"Thowilz"` setelah `"Kas"`; tambah `"Klas","Thowilz"` ke daftar bukan-`n` (biarkan tanpa class `n` kecuali Thowilz — tambah `"Thowilz"` ke array class `n`). Baris: setelah sel badge kas tambah:

```js
      "<td>" + esc(s.klasifikasi || "-") + "</td>" +
      '<td class="n"><b>' + (nz(s.thowilz) ? nz(s.thowilz) : "—") + "</b></td>" +
```

4. Panel checklist — tambah fungsi baru sebelum `panelTambahan`, panggil di awal `panelTambahan` (atau di pemanggil panel; pilih: prepend `h = panelThowilz(s) + h` tepat setelah `let h = ...` di `panelTambahan`):

```js
/* Checklist 4 pilar Thowilz. Ambang sama dengan compute_thowilz() Python. */
function panelThowilz(s) {
  const vOk = (s.evCfo != null && s.evCfo > 0 && s.evCfo <= 15) && (s.pegCfo == null || s.pegCfo < 1.5);
  const kOk = s.cashBadge === "Lolos" && !!s.marginStabil;
  const tOk = (s.klasifikasi || "-") !== "-";
  const mOk = !!(s.sSpring || s.sSideways);
  const baris = [
    ["1. Valuasi", vOk, "EV/CFO " + (s.evCfo != null && s.evCfo > 0 ? fmt(s.evCfo, 1) + "x" : "—") + " · PEG-CFO " + (s.pegCfo != null ? fmt(s.pegCfo, 2) : "—")],
    ["2. Kesehatan kas", kOk, (s.cashBadge || "—") + " · margin " + (s.marginStabil ? "stabil" : "labil")],
    ["3. Tesis", tOk, esc(s.klasifikasi || "-")],
    ["4. Timing", mOk, s.sSpring ? "spring" : s.sSideways ? "sideways" : "netral"]
  ];
  let h = '<div class="sep"></div><h3 style="font-size:13.5px;margin-bottom:8px">Checklist Thowilz · skor ' + (nz(s.thowilz) ? nz(s.thowilz) + " / 100" : "—") + "</h3>";
  h += '<div class="tw"><table class="tbl"><thead><tr><th>Pilar</th><th>Status</th><th>Bukti</th></tr></thead><tbody>';
  baris.forEach(r => {
    h += "<tr><td>" + r[0] + '</td><td>' + (r[1] ? '<span class="badge b-ok">OK</span>' : '<span class="badge b-no">X</span>') + "</td><td>" + r[2] + "</td></tr>";
  });
  return h + "</tbody></table></div>";
}
```

`esc()` dan `fmt()` sudah ada (dipakai di file yang sama).

5. `toRow`: tambah setelah 5 nilai fase-1:

```js
    (s.pegCfo != null ? s.pegCfo : ""), (s.cfoCagr != null ? s.cfoCagr : ""), (s.grossMargin != null ? s.grossMargin : ""), (s.marginStabil ? 1 : 0),
    (s.capexInten != null ? s.capexInten : ""), (s.klasifikasi && s.klasifikasi !== "-" ? s.klasifikasi : ""), (nz(s.thowilz) ? s.thowilz : "")];
```

6. `dashVal`: tambah `case "thowilz": return nz(x.s.thowilz);` setelah `case "total"`.

- [ ] **Step 4: Run test to verify it passes**

Run: `node tests/_test-cash-ui.js`
Expected: PASS `cash-ui OK`

Run syntax: ekstraksi `<script>` terakhir + `node --check` (cara sama seperti fase 1)
Expected: `syntax OK`

Impor manual CSV lama 43 kolom: kolom baru tampil `—`, tidak error.

- [ ] **Step 5: Commit**

```bash
git add web/screener-saham-indonesia.html tests/_test-cash-ui.js
git commit -m "feat: UI kolom Klasifikasi+Thowilz dan checklist 4 pilar"
```

### Task 5: Verifikasi E2E + regresi penuh

**Files:** tidak ada (verifikasi saja).

- [ ] **Step 1: Round-trip CSV offline**

```bash
python -c "import importlib.util,csv; spec=importlib.util.spec_from_file_location('m','scripts/fetch-data-idx.py'); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); assert m.CSV_HEADER[-7:]==['peg_cfo','cfo_cagr','gross_margin','margin_stabil','capex_inten','klasifikasi','thowilz']; assert len(m.CSV_HEADER)==55; print('header OK: 55 kolom')"
```

Harap: `header OK: 55 kolom`.

- [ ] **Step 2: Live Yahoo ICBP (margin tahunan)**

```bash
python scripts/fetch-data-idx.py --tickers ICBP --no-pasar --ringkas --out C:\Users\itokt\AppData\Local\Temp\opencode\live-thowilz
python -c "import csv; r=list(csv.DictReader(open('C:\\Users\\itokt\\AppData\\Local\\Temp\\opencode\\live-thowilz.csv',encoding='utf-8-sig')))[0]; print(r['kode'], r['gross_margin'], r['margin_stabil'], r['klasifikasi'], r['thowilz'])"
```

Harap: `gross_margin` terisi bila Yahoo memberi `grossProfit` valid. TEMUAN LIVE (ICBP, 2026-10-07): Yahoo mengembalikan `grossProfit.raw = 0` dengan revenue 74T — celah data, BUKAN margin nol. Aturan yang diimplementasikan: titik tahun dengan `gp == 0 & rev > 0` dilewati (rugi kotor beneran `gp < 0` tetap dihitung); bila semua titik nol → `gross_margin` kosong + `margin_stabil = 0` (test `test_margin_nol_dilewati`, total suite 17 passed). Implikasi jujur: untuk kebanyakan emiten IDX, `margin_stabil` hanya terisi bila Yahoo punya grossProfit valid; sumber ideal tetap laporan IDX (belum mengekstrak laba kotor — kandidat fase 3).

- [ ] **Step 3: Regresi penuh**

```bash
python tests/test-cash-quality.py
python tests/test-harian.py
node tests/_test-cash-ui.js
node tests/_test-praktis.js
```

Harap: 16 passed, 4 passed, cash-ui OK, `_test-praktis.js` tetap 4 gagal pre-existing yang sama (sp_umur, sp_kontrak, segmented control, ekspor BOM) — bukan regresi.

- [ ] **Step 4: Commit bila ada perbaikan**

```bash
git add -A
git commit -m "fix: selaraskan ambang Thowilz E2E" || echo "tidak ada perubahan"
```

## Self-Review

- Spec coverage: EV/CFO+EV/FCF (fase 1) ✓; PEG (Task 2-3, paralel PEG-CFO) ✓; pricing power via margin stabil (Task 1+3) ✓; klasifikasi 5 kategori (Task 2-3) ✓; red flag laba semu (fase 1 Sloan) ✓; alokasi modal via capex_inten + penalti di skor (Task 3, degradasi jujur bila Yahoo tak beri FCF) ✓; VSA timing (pre-existing s_spring/s_sideways dipakai di skor, tidak diubah) ✓; checklist 4 pilar + exit strategy — exit strategy TIDAK diotomatiskan (keputusan jual manual, di luar scope screener; panel hanya menampilkan bukti).
- Placeholder scan: semua langkah berisi kode aktual + perintah run + expected konkret.
- Type consistency: SUDAH DIPERBAIKI — fungsi murni selalu fraksi (`compute_margin_quality` input fraksi, `compute_cfo_cagr` output fraksi, `compute_peg_cfo` input fraksi); CSV selalu persen (`gross_margin` % 1 desimal, `cfo_cagr` % 1 desimal sejajar kolom `cagr` existing); konversi di wiring Task 3 (`round(cagr_cf*100,1)`); `compute_peg_cfo` menerima fraksi langsung (bukan nilai CSV); JS `cfoCagr` parse persen.
