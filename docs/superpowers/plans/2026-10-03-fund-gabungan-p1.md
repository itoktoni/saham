# P1 Combine Fundamental Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Gabungkan fundamental Yahoo+Sesaham+IndoPremier dengan provenance display, tanpa ubah skor.

**Architecture:** `fetch-fund-gabungan.py` (parse pair label-nilai sesaham + tabel `<tr>` arus kas + tabel kuartalan IP) → `data/fund-gabungan.json` (TTL 30 hari) → serve via Download + `/api/fund` → `SP.gabung` override tampilan drawer.

**Tech Stack:** Python stdlib (`urllib`, `html.parser`/regex), vanilla JS, Node smoke test.

## Global Constraints

- Python stdlib saja; delay 2 dtk/req; best-effort per emiten.
- JANGAN sentuh `skor()`, `aksi()`, `valuasi()`, kalibrasi.
- Konflik >25% → flag + tampil dua-duanya; gagal total → Yahoo-only.
- Angka ID: titik ribuan, koma desimal, "—" = kosong, akhiran T/M/B/Jt.
- Tanpa kolom tabel baru; tanpa rebuild `.exe`.

---

### Task 1: `scripts/fetch-fund-gabungan.py`

**Files:** Create `scripts/fetch-fund-gabungan.py`. Test: fixture offline + live BBNI.

**Interfaces:** Consumes: sesaham `/emiten/KODE`, IP `fundamental.php?code=K&quarter=5`. Produces per emiten `{nilai:{roe,eps,der,pbv,bvps}, sumber:{}, flag[], tren{roe,eps,der}, kas{ocf,fcf,dividen}, fv_graham, klasifikasi{}, sejenis[]}` + `diambil`.

- [ ] **Step 1: Tulis modul**

Parser sesaham (terverifikasi 03-Okt-2026, BBNI 222.979 byte):
```python
def pairs_sesaham(html):
    out = {}
    for a, b in re.findall(r"<span[^>]*>([^<>]{1,80})</span>\s*<span[^>]*>([^<>]{1,40})</span>", html):
        out[uncap(a)] = b.strip()
    return out
```
Label dipakai: `ROE (TTM)`, `EPS (TTM)`, `Debt to Equity Ratio (DER)`, `Current Price to Book Value`, `Book Value per Share`, `Fair Value (Graham Number)`, `Cash Flow per Share (TTM)`, `Free Cash Flow (Annual)`. Nilai persen "12,06%" → 12.06 (koma→titik, buang %); "7.685" → 7685 (buang titik); "127,56 T" → ×1e12; "—"/"-" → None.
Tabel kas: untuk setiap `<tr>...\s*<td[^>]*>(Kas dari Aktivitas Operasi|Arus Kas Bebas \(FCF\)|Dividen Dibayar)</td>((?:\s*<td[^>]*>[^<>]*</td>)+)` → sel = strip-titik-ke-int (negatif diawali `-`).
Klasifikasi: link `/sektor/X`, `/peta-industri/X`, `/peta-lini-bisnis/X`, `/peta-produk-komoditas/X` → kumpulkan teks link per grup. Sejenis: link `/emiten/XXXX` di blok "Emiten Sejenis" (ambil semua, unik, buang kode sendiri).
Parser IP: tabel `<tr>` dengan sel pertama ∈ {ROE, EPS, "Debt/Equity", ...}? Kolom: Anlz,6M,3M2026..3M2021 (8 kolom). Ambil baris `ROE`, `EPS`, `Debt/Equity`: nilai = kolom Anlz (indeks 0). Deret = 8 kolom untuk tren (parse float koma, "—"→None).
`tren seri`: "naik" bila 2 terakhir naik dan ≥5 dari 7 perubahan positif; "turun" bila simetris; else "datar"; <6 titik valid → None (fallback Yahoo).
`ambil_fund(kode)`: fetch 2 halaman → gabung dict. `main`: argv kode (default BBCA), tulis `fund-gabungan.json` di cwd, delay 2 dtk.

- [ ] **Step 2: Fixture offline**

Simpan 2 cuplikan HTML asli (sesaham BBNI secukupnya: 3 pair + 1 baris kas; IP BUMI: 2 baris rasio) ke `tests/fixture-fund-ss.html`, `tests/fixture-fund-ip.html` (salin dari respons live, potong minimal tapi valid). Cek via skrip temp: parse tepat (ROE 12.06, FV 7685, OCF TTM 19678040000000, IP ROE Anlz benar).

- [ ] **Step 3: Live 1 emiten**

Run: `python scripts/fetch-fund-gabungan.py BBNI` (dari `data/` agar cache benar).
Expected: JSON berisi nilai + kas + fv_graham 7685 + tren + klasifikasi; `sumber` terisi.

### Task 2: Server wiring

**Files:** Modify `app/app-screener.py` (`muat_fund`, hasil, rute `/api/fund`). Test: compile + live.

- [ ] **Step 1: Tambah setelah fungsi `muat_tema`:**
```python
FUND_TTL_HARI = 30


def muat_fund(kodes):
    try:
        with open("fund-gabungan.json", "r", encoding="utf-8") as fh:
            base = json.load(fh) or {}
    except (OSError, json.JSONDecodeError):
        base = {}
    perlu = [k for k in (kodes or []) if k not in (base.get("emiten") or {})]
    segar = False
    if base.get("diambil"):
        try:
            segar = (datetime.now().astimezone() - datetime.fromisoformat(base["diambil"])).days < FUND_TTL_HARI
        except ValueError:
            segar = False
    if perlu and not segar:
        try:
            ff = load_mod("fetch_fund", "fetch-fund-gabungan.py")
            base = ff.ambil_semua(perlu, log_fn=lambda m: tulis_log("fund " + m.strip() if m else ""))
        except Exception as e:  # noqa: BLE001
            tulis_log("fund gagal: %s" % e)
    return base if isinstance(base, dict) else {}
```
(`ambil_semua(kodes, log_fn)` di modul: loop `ambil_fund` + delay + tulis cache + return dict. Tambahkan di Task 1 sebagai bagian modul.)
- [ ] **Step 2: `muat_semua`**: setelah `tema = muat_tema()` tambah `say("Memuat fundamental gabungan..."); fund = muat_fund(kodes)` dan `"fund": fund,` di hasil. Rute `/api/fund` pola tema (baca `fund-gabungan.json`, 404 bila kosong).
- [ ] **Step 3:** `python -m py_compile`; live: server uji → `/api/fund` 200 setelah Download (atau 404 sebelum ada cache — sah).

### Task 3: Frontend gabung + drawer

**Files:** Modify `web/screener-praktis.html` (`S.fund`, `SP.gabung`, drawer s2, cek string). Test: smoke + manual.

**Interfaces:** Consumes Task 1-2. Produces tampilan; `skor()` tidak tersentuh.

- [ ] **Step 1: `SP.gabung(r, f)` + ekspor (gagal dulu)**

Blok 18 sebelum `console.log(gagal`:
```js
// 18) gabung fundamental
{
  const rr = { harga: "1000", eps: "10", roe: "", der: "", pbv: "", ekuitas: "", saham: "" };
  const ff = { nilai: { roe: 20, eps: 12 }, sumber: { roe: "IP", eps: "IP" }, flag: [], tren: { roe: "naik" }, kas: { ocf: 5, fcf: 4 }, fv_graham: 1500 };
  const g = SP.gabung(rr, ff);
  cek("gabung: prioritas IP", g.tampil.roe.v === 20 && g.tampil.roe.s === "IP");
  cek("gabung: fallback Yahoo", SP.gabung({ harga: "1", eps: "7" }, null).tampil.eps.v === 7);
  const g2 = SP.gabung({ harga: "1", eps: "10", roe: "", ekuitas: "100", saham: "10", laba: "5" }, { nilai: { roe: 30 }, sumber: { roe: "SS" }, flag: [], tren: {}, kas: {} });
  cek("gabung: konflik >25% flag", g2.flag.length > 0 && g2.tampil.roe.v === 30, JSON.stringify(g2));
}
```
(roe Yahoo dari ekuitas/saham/laba: laba 5/ekuitas 100 = 5% vs SS 30% → selisih >25% → flag, tampil SS.) Run → `TypeError: SP.gabung is not a function`.
Implementasi (sisip sebelum `// ---------- skor tunggal`, ekspor di return):
```js
  function gabung(r, f) {
    r = r || {}; f = f || {};
    var nv = (f.nilai || {}), sb = (f.sumber || {}), out = { tampil: {}, flag: (f.flag || []).slice() };
    function yahooROE() {
      var e = toNum(r.ekuitas), s = toNum(r.saham), l = toNum(r.laba);
      if (e > 0 && s > 0) return l / e * 100;
      return toNum(r.roe);
    }
    var yh = { roe: yahooROE(), eps: toNum(r.eps), der: toNum(r.der), pbv: toNum(r.pbv), bvps: toNum(r.ekuitas) / (toNum(r.saham) || 1) };
    ["roe", "eps", "der", "pbv", "bvps"].forEach(function (k) {
      var g = nv[k];
      if (g != null && isFinite(g) && g !== 0) {
        if (yh[k] && Math.abs(g - yh[k]) / Math.abs(yh[k]) > 0.25) out.flag.push(k + ": gabungan " + g + " vs Yahoo " + Math.round(yh[k] * 100) / 100);
        out.tampil[k] = { v: g, s: sb[k] || "?" };
      } else out.tampil[k] = { v: yh[k], s: "YH" };
    });
    out.tren = f.tren || {}; out.kas = f.kas || {}; out.fvGraham = f.fv_graham || 0;
    out.klasifikasi = f.klasifikasi || {}; out.sejenis = f.sejenis || [];
    return out;
  }
```
Run → PASS.
(Catatan: konflik dihitung vs Yahoo hanya bila Yahoo nonzero — bila Yahoo 0/kosong langsung pakai gabungan tanpa flag.)

- [ ] **Step 2: Drawer + state + cek string**

State/init/Download pola tema (`S.fund`, `j.fund`, `/api/fund`).
Drawer langkah 2, setelah baris MOS/Upside (anchor `row("Ruang ke puncak 52mg"`): tambah via helper `fundBox(x)` sebelum `"</div>"` penutup s2:
```js
  function fundBox(x) {
    if (!S.fund.diambil) return "";
    var g = SP.gabung(x.r, (S.fund.emiten || {})[x.kode]);
    if (!S.fund.diambil) return "";
    var b = function (lbl, t) { return row(lbl + ' <span class="mut">[' + t.s + "]</span>", t.v ? nf(t.v, lbl === "ROE" ? 1 : 2) : "—"); };
    var h = b("ROE gab", g.tampil.roe) + b("EPS gab", g.tampil.eps);
    h += row("Tren ROE/EPS/DER", (g.tren.roe || "?") + " / " + (g.tren.eps || "?") + " / " + (g.tren.der || "?"));
    h += row("Arus kas OCF/FCF", (g.kas.ocf != null ? nf(g.kas.ocf / 1e9, 1) + "M" : "—") + " / " + (g.kas.fcf != null ? nf(g.kas.fcf / 1e9, 1) + "M" : "—")) +
      (g.kas.ocf > 0 && g.kas.fcf > 0 ? '<div class="note">Laci terisi: kas operasi + bebas positif.</div>' : '<div class="warn">Laci waspada: kas tidak keduanya positif.</div>');
    if (g.fvGraham > 0) h += row("FV Graham SS", nf(g.fvGraham, 0));
    g.flag.forEach(function (m) { h += '<div class="warn">' + m + "</div>"; });
    return h;
  }
```
Blok 7 tambah: `cek("fundBox ada", html.includes("Arus kas OCF/FCF") && html.includes("SP.gabung"));`
Run → PASS. Manual: Download → drawer BBCA/BBNI cocok vs situs; matikan network → fallback Yahoo (tanpa badge fund).
