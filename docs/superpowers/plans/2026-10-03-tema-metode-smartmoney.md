# Tema + Metode ID + Smart-Money Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Filter tema narasi + 5 preset metode Indonesia + panel perbandingan harga smart-money.

**Architecture:** Scraper `fetch-tema.py` (cache 30 hari) + serve via Download/`/api/tema` dengan merge manual; `matchMetode` 5 cabang ID; `SP.smartMoney` murni untuk panel drawer.

**Tech Stack:** Python stdlib, `app/app-screener.py`, vanilla JS satu file HTML, Node smoke test. Tanpa dependensi baru.

## Global Constraints

- Python hanya standard library; scraper 1 halaman/2 detik, timeout 30 dtk, UA sopan.
- Tanpa kolom tabel baru; tanpa ubah rumus fase/skor/aksi; skor kalibrasi aman.
- Semua angka JS via `SP.toNum()`/`nf`; absen → "—", bukan alarm palsu.
- Nilai metode lama tak dikenal → "Semua" (pola `indexOf` yang sudah ada).
- Tanpa rebuild `.exe` (launcher mode source).

---

### Task 1: Scraper tema + serve (`fetch-tema.py`, server)

**Files:**
- Create: `scripts/fetch-tema.py`
- Modify: `app/app-screener.py` (fungsi `muat_tema`, panggil di `muat_semua`, rute `/api/scope`-style `/api/tema`)
- Test: cek offline `python -c` (parser + merge, tanpa network) + live 1 halaman

**Interfaces:**
- Consumes: halaman sesaham (HTML server-rendered, baris `/emiten/KODE`)
- Produces: `data/tema.json` `{diambil, tema: [{nama, deskripsi, sumber, emiten[], wajar:{}}]}`; `muat_tema()` menggabung `data/tema-manual.json` `{deskripsi:{}, tambahan:{}}`; respons Download `"tema"`, `GET /api/tema`.

- [ ] **Step 1: Tulis `scripts/fetch-tema.py`**

Konten persis:
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fetch-tema.py: peta tema dari sesaham.com (scrape sopan + cache lama)."""
import json
import time
import urllib.request
from datetime import datetime
from html.parser import HTMLParser

BASE = "https://sesaham.com"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
CACHE_FILE = "tema.json"

HALAMAN = [
    ("Oil & Coal", ["peta-produk-komoditas/coal", "peta-produk-komoditas/crude-oil",
                    "peta-produk-komoditas/lignite", "peta-industri/minyak-gas"],
     "Energi fosil: batu bara, minyak, gas."),
    ("Gold", ["peta-produk-komoditas/gold", "peta-produk-komoditas/gold-ore"],
     "Emas dan bijih emas."),
    ("Nickel", ["peta-produk-komoditas/nickel-ore", "peta-produk-komoditas/nickel-matte"],
     "Nikel dan turunannya untuk baterai/EV."),
    ("Data Center & AI", ["peta-produk-komoditas/data-center",
                           "peta-industri/aplikasi-jasa-internet"],
     "Infrastruktur digital: data center, layanan internet/TI."),
]


class _Tabel(HTMLParser):
    def __init__(self):
        super().__init__()
        self.baris, self._td, self._href, self._tr = [], [], None, False

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._tr, self._td, self._href = True, [], None
        if tag == "td" and self._tr:
            self._td.append("")
        if tag == "a" and self._tr:
            for k, v in attrs:
                if k == "href" and v.startswith("/emiten/"):
                    self._href = v.split("/")[-1].strip().upper()

    def handle_data(self, data):
        if self._tr and self._td:
            self._td[-1] += data

    def handle_endtag(self, tag):
        if tag == "tr" and self._tr:
            if self._href and self._td:
                self.baris.append((self._href, [t.strip() for t in self._td]))
            self._tr = False


def parse_id(s):
    s = (s or "").strip()
    if not s or s in ("—", "-", "--"):
        return 0
    s = s.replace(".", "").replace(",", ".")
    try:
        return int(float(s))
    except ValueError:
        return 0


def _unduh(slug, timeout=30):
    req = urllib.request.Request(BASE + "/" + slug, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def ambil_tema(log_fn=None, delay=2.0):
    log = log_fn or (lambda m: None)
    gab, gagal = {}, []
    for nama, slugs, desk in HALAMAN:
        emiten, wajar = [], {}
        for slug in slugs:
            try:
                t = _Tabel()
                t.feed(_unduh(slug))
                for kode, sel in t.baris:
                    if kode not in emiten:
                        emiten.append(kode)
                    w = parse_id(sel[-1]) if sel else 0
                    if w > 0:
                        wajar[kode] = w
                log("%s: %d baris" % (slug, len(t.baris)))
            except Exception as e:  # noqa: BLE001
                gagal.append("%s: %s" % (slug, str(e)[:80]))
            time.sleep(delay)
        gab[nama] = {"nama": nama, "deskripsi": desk, "sumber": slugs,
                     "emiten": emiten, "wajar": wajar}
    hasil = {"diambil": datetime.now().astimezone().isoformat(timespec="seconds"),
             "tema": list(gab.values()), "gagal": gagal}
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as fh:
            json.dump(hasil, fh, ensure_ascii=False)
    except OSError:
        pass
    return hasil


if __name__ == "__main__":
    out = ambil_tema()
    print("tema: %d, gagal: %d" % (len(out["tema"]), len(out["gagal"])))
```

- [ ] **Step 2: Uji offline parser + angka (tanpa network)**

Run:
```bash
python -c "import importlib.util; s=importlib.util.spec_from_file_location('t','scripts/fetch-tema.py'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); assert m.parse_id('18.263')==18263 and m.parse_id('—')==0 and m.parse_id('450,16 M')==0; t=m._Tabel(); t.feed('<table><tr><td>1</td><td><a href=\"/emiten/ADRO\">ADRO</a></td><td>2.500</td><td>4.356</td></tr></table>'); assert t.baris[0][0]=='ADRO' and m.parse_id(t.baris[0][1][-1])==4356; print('parser OK')"
```
Expected: mencetak `parser OK`.
(Catatan: `parse_id('450,16 M')` → mengandung huruf → 0; kolom Wajar selalu integer ribuan jadi aman.)

- [ ] **Step 3: Uji live 1 halaman via fungsi (bukan main penuh)**

Run:
```bash
python -c "import importlib.util; s=importlib.util.spec_from_file_location('t','scripts/fetch-tema.py'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); t=m._Tabel(); t.feed(m._unduh('peta-produk-komoditas/coal')); k=[k for k,_ in t.baris]; assert 'ADRO' in k and 'PTBA' in k and len(k)>=20, len(k); print('coal OK:',len(k))"
```
Expected: `coal OK: 25` (bila situs berubah jumlah, assert longgar `>=20` tetap lolos; kegagalan network = blokir, lapor).

- [ ] **Step 4: Wiring server (baca + refresh + merge manual + rute)**

Di `app/app-screener.py`, setelah fungsi `ambil_scope` tambahkan:
```python
TEMA_TTL_HARI = 30


def _baca_json(nama):
    try:
        with open(nama, "r", encoding="utf-8") as fh:
            return json.load(fh) or {}
    except (OSError, json.JSONDecodeError):
        return {}


def muat_tema():
    base = _baca_json("tema.json")
    segar = False
    if base and base.get("diambil"):
        try:
            selisih = datetime.now().astimezone() - datetime.fromisoformat(base["diambil"])
            segar = selisih.days < TEMA_TTL_HARI
        except ValueError:
            segar = False
    if not segar:
        try:
            ft = load_mod("fetch_tema", "fetch-tema.py")
            base = ft.ambil_tema(log_fn=lambda m: tulis_log("tema " + m.strip() if m else ""))
        except Exception as e:  # noqa: BLE001
            tulis_log("tema gagal: %s" % e)
            base = base or {}
    man = _baca_json("tema-manual.json")
    if man and base.get("tema"):
        for t in base["tema"]:
            des = (man.get("deskripsi") or {}).get(t["nama"])
            if des:
                t["deskripsi"] = des
            for k in (man.get("tambahan") or {}).get(t["nama"], []):
                kk = str(k).strip().upper()
                if kk and kk not in t["emiten"]:
                    t["emiten"].append(kk)
    return base or {}
```
Di `muat_semua()`, sebelum `say("Selesai...")` tambahkan:
```python
    say("Memuat peta tema...")
    tema = muat_tema()
```
Dan di dict `hasil` tambahkan `"tema": tema,` setelah `"scope": scope or {},`.
Setelah blok rute `/api/scope` (sebelum `/favicon.ico`) tambahkan:
```python
            if jalur == "/api/tema":
                tm = muat_tema()
                if not tm or not tm.get("tema"):
                    return self._json({"ok": False, "error": "belum ada data tema."}, 404)
                return self._json({"ok": True, "tema": tm})
```

- [ ] **Step 5: Verifikasi sintaks**

Run:
```bash
python -m py_compile app/app-screener.py scripts/fetch-tema.py
Select-String -LiteralPath "app/app-screener.py" -Pattern "/api/tema" -SimpleMatch
```
Expected: kompilasi bersih; rute ditemukan.

### Task 2: Lima preset metode ID

**Files:**
- Modify: `web/screener-praktis.html` (METODE + `matchMetode` + `<option>` + blok 8 test)
- Test: `tests/_test-praktis.js`

**Interfaces:**
- Consumes: field `s_*`/`pos` yang sudah ada (aturan Jelang/Lolos di bawah)
- Produces: nilai preset baru; `S.metode` lama tak dikenal → "Semua" (kode `indexOf` yang sudah ada, tanpa ubah).

- [ ] **Step 1: Perbarui blok 8 test ke nama baru + 2 aturan baru**

Ganti seluruh isi blok `// 8) preset metode screening` menjadi:
```js
// 8) preset metode screening (label Indonesia)
{
  cek("METODE tersedia (5 preset)", Array.isArray(SP.METODE) && SP.METODE.length === 5, String(SP.METODE));
  const bSide = { kode: "SIDE", nama: "Side", r: { harga: "1000", s_sideways: "1", s_vol_ratio: "0.7", s_spring: "0", s_closeabove: "1", s_springlow: "950", s_resistance: "1050" }, k: {}, fase: "Akumulasi", pos: 0.3 };
  const bSpring = { kode: "SPR", nama: "Spr", r: { harga: "1000", s_sideways: "0", s_vol_ratio: "1.0", s_spring: "1", s_closeabove: "1", s_springlow: "950", s_resistance: "1050" }, k: {}, fase: "Spring", pos: 0.2 };
  const bBreak = { kode: "BRK", nama: "Brk", r: { harga: "1000", s_sideways: "0", s_vol_ratio: "1.4", s_spring: "0", s_closeabove: "1", s_springlow: "900", s_resistance: "1050" }, k: {}, fase: "Markup", pos: 0.8 };
  const bCont = { kode: "CTC", nama: "Ctc", r: { harga: "1000", s_sideways: "0", s_vol_ratio: "0.9", s_spring: "0", s_closeabove: "1", s_springlow: "900", s_resistance: "1050" }, k: {}, fase: "Netral", pos: 0.5 };
  const bJelang = { kode: "JEL", nama: "Jel", r: { harga: "1000", s_sideways: "0", s_vol_ratio: "1.2", s_spring: "0", s_closeabove: "1", s_springlow: "900", s_resistance: "1050" }, k: {}, fase: "Netral", pos: 0.65 };
  cek("matchMetode ada", typeof SP.matchMetode === "function");
  cek("barang kering lolos", SP.matchMetode(bSide, "Barang Kering") === true);
  cek("barang kering bukan lolos-resistance", SP.matchMetode(bSide, "Lolos Resistance") === false);
  cek("kocokan = spring", SP.matchMetode(bSpring, "Kocokan Terakhir") === true);
  cek("lolos butuh pos tinggi", SP.matchMetode(bBreak, "Lolos Resistance") === true);
  cek("jelang di tengah range", SP.matchMetode(bJelang, "Jelang Breakout") === true);
  cek("jelang bukan barang kering", SP.matchMetode(bJelang, "Barang Kering") === false);
  cek("kontraksi tetap", SP.matchMetode(bCont, "Kontraksi VCP") === true);
  cek("Semua lolos semua", SP.matchMetode(bSide, "Semua") === true);
}
```

- [ ] **Step 2: Jalankan uji untuk pastikan gagal**

Run: `node tests/_test-praktis.js`
Expected: FAIL pada cek nama baru (fungsi masih label lama).

- [ ] **Step 3: Implementasi METODE + cabang baru**

Ganti:
```js
  var METODE = ["Sideways Dry-Out", "Contraction (VCP)", "Spring / Shakeout", "Breakout Markup"];
```
menjadi:
```js
  var METODE = ["Jelang Breakout", "Barang Kering", "Kontraksi VCP", "Lolos Resistance", "Kocokan Terakhir"];
```
Ganti 4 cabang `if (nama === ...)` di `matchMetode` menjadi:
```js
    if (nama === "Barang Kering") return sideways && vr < 1.0 && !spring;
    if (nama === "Kocokan Terakhir") return spring;
    if (nama === "Lolos Resistance") return above && pos >= 0.75 && vr >= 1.3;
    if (nama === "Jelang Breakout") return above && !spring && pos >= 0.55 && pos <= 0.75 && vr >= 1.0 && vr <= 1.5;
    if (nama === "Kontraksi VCP") return !sideways && above && !spring && vr < 1.1 && pos >= 0.25 && pos <= 0.70;
```
Ganti 4 `<option>` metode di toolbar menjadi:
```html
        <option value="Semua">Semua Metode</option>
        <option value="Jelang Breakout" title="Before breakout: menempel di bawah resistance (pos 55-75%), volume mulai naik">Jelang Breakout</option>
        <option value="Barang Kering" title="Sideways dry-out: range sempit + volume kering, float habis diserap">Barang Kering</option>
        <option value="Kontraksi VCP" title="Volatility contraction: range + volume menyempit bertahap">Kontraksi VCP</option>
        <option value="Lolos Resistance" title="Sudah breakout: di atas resistance + volume besar">Lolos Resistance</option>
        <option value="Kocokan Terakhir" title="Spring/shakeout: tembus support lalu close kembali di atasnya">Kocokan Terakhir</option>
```
(Jaga `value="Semua"` pertama; opsi Contraction lama yang ber-title dihapus.)

- [ ] **Step 4: Jalankan uji + cek string lama hilang**

Run:
```bash
node tests/_test-praktis.js
Select-String -LiteralPath "web/screener-praktis.html" -Pattern "Sideways Dry-Out" -SimpleMatch
```
Expected: "Semua uji lulus"; Select-String tanpa hasil (label lama habis).

### Task 3: `SP.smartMoney` + Tema UI + drawer

**Files:**
- Modify: `web/screener-praktis.html` (SP.smartMoney + ekspor; state/filter/narasi Tema; blok drawer; cek string test)
- Test: `tests/_test-praktis.js` + manual

**Interfaces:**
- Consumes: `x.asing_avg`, `entry.acc` (bavg idx 2), `entry.insider` (`price_formatted` "1,000"), `x.val.intrinsic`, peta wajar tema; pola badge/drawer ada
- Produces: UI selesai. `smartMoney(x, entry, wajar)` → `{rows: [{sumber, avg, pnl, extra}], terbaik, jarakPct, upsidePct, wajar}`; pembanding = avg valid terendah; absen → baris "—"/vonis absen.

- [ ] **Step 1: Tambah blok uji + 3 cek string (gagal dulu)**

Blok 14 sebelum `console.log(gagal`:
```js
// 14) smart money vs harga kita
{
  const ex = { kode: "T", fase: "Akumulasi", r: { harga: "900" }, asing_avg: 1000, val: { intrinsic: 1200 } };
  const en = { acc: { top_buyers: [{ broker: "OD" }], series: { OD: [[10, 10, 800, 810]] } }, insider: [{ name: "DIR A", date: "2026-09-20", action_type: "buy", price_formatted: "1,100" }] };
  const sm = SP.smartMoney(ex, en, 0);
  cek("smartMoney: 3 baris + terbaik = broker termurah", sm.rows.length === 3 && sm.terbaik.sumber === "Broker OD", JSON.stringify(sm));
  cek("smartMoney: jarak +12,5% di atas avg broker", Math.abs(sm.jarakPct - 12.5) < 0.01, String(sm.jarakPct));
  cek("smartMoney: upside +33,3%", Math.abs(sm.upsidePct - 33.33) < 0.1, String(sm.upsidePct));
  const sm0 = SP.smartMoney({ kode: "T", fase: "X", r: { harga: "900" }, val: {} }, null, 0);
  cek("smartMoney: tanpa data aman", sm0.terbaik === null);
}
```
Dan di blok 7 tambah:
```js
  cek("dropdown Tema ada", html.includes('id="tema"'));
  cek("smartMoney ada", html.includes("SP.smartMoney"));
  cek("blok smart money drawer ada", html.includes("Smart money vs harga kita"));
  cek("aturan terlalu-jauh ada", html.includes("Terlalu jauh di atas harga smart money"));
```

- [ ] **Step 2: Jalankan uji untuk pastikan gagal**

Run: `node tests/_test-praktis.js`
Expected: error `TypeError: SP.smartMoney is not a function` (+ 4 cek string FAIL bila sampai sana).

- [ ] **Step 3: Implementasi `SP.smartMoney` + ekspor**

Sisipkan setelah akhir fungsi `exitLevel` (sebelum `// ---------- valuasi sederhana`):
```js
  // ---------- smart money vs harga kita ----------
  function smartMoney(x, entry, wajar) {
    var harga = toNum(x.r && x.r.harga);
    var rows = [];
    var av = (x.asing_avg != null && x.asing_avg > 0) ? x.asing_avg : 0;
    if (av > 0 && harga > 0) rows.push({ sumber: "Asing", avg: av, pnl: (harga / av - 1) * 100, extra: "" });
    var acc = entry && entry.acc;
    var tb = acc && (acc.top_buyers || [])[0];
    if (tb && acc.series && acc.series[tb.broker]) {
      var bv = acc.series[tb.broker].map(function (p) { return p[2]; }).filter(function (v) { return v != null && v > 0; });
      if (bv.length) {
        var ba = bv.reduce(function (a, c) { return a + c; }, 0) / bv.length;
        rows.push({ sumber: "Broker " + tb.broker, avg: ba, pnl: (harga / ba - 1) * 100, extra: "" });
      }
    }
    var buys = ((entry && entry.insider) || []).filter(function (t) { return t && t.action_type === "buy" && t.date && t.price_formatted; });
    buys.sort(function (a, b) { return a.date < b.date ? 1 : -1; });
    if (buys.length) {
      var pr = toNum(String(buys[0].price_formatted).replace(/,/g, ""));
      if (pr > 0 && harga > 0) rows.push({ sumber: "Insider " + buys[0].name.split(" ").slice(0, 2).join(" "), avg: pr, pnl: (harga / pr - 1) * 100, extra: buys[0].date });
    }
    var valid = rows.filter(function (r) { return r.avg > 0; });
    if (!valid.length || !(harga > 0)) return { rows: rows, terbaik: null, jarakPct: null, upsidePct: null, wajar: wajar || null };
    var best = valid.slice().sort(function (a, b) { return a.avg - b.avg; })[0];
    var intr = (x.val && x.val.intrinsic > 0) ? x.val.intrinsic : 0;
    return { rows: rows, terbaik: best, jarakPct: (harga / best.avg - 1) * 100,
             upsidePct: intr > 0 ? (intr - harga) / harga * 100 : null, wajar: wajar || null };
  }
```
Ekspor: tambahkan `smartMoney: smartMoney,` setelah `exitLevel: exitLevel,`.
(Verifikasi hitung test: broker avg 800 → jarak (900/800-1)=12,5% ✓; upside (1200-900)/900=33,33% ✓; terbaik = Broker OD 800 < Asing 1000 < Insider 1100 ✓.)

- [ ] **Step 4: Tema state + dropdown + narasi + filter**

State: `scope: {},` → `scope: {}, tema: {},` (di deklarasi `var S`).
Handler Download: setelah `S.scope = j.scope || {};` tambah `S.tema = j.tema || {};`.
Init (setelah blok fetch `/api/scope`): tambah:
```js
  fetch("/api/tema").then(function (r) { return r.json(); }).then(function (j) {
    if (j && j.ok && j.tema) { S.tema = j.tema; renderTema(); render(); }
  }).catch(function () {});
```
Toolbar: setelah `</select>` metode (sebelum `<input class="search"`), tambah:
```html
      <select class="mini-sel" id="tema" title="Filter tema narasi">
        <option value="Semua">Semua Tema</option>
      </select>
```
Tepat setelah `</div>` penutup toolbar (sebelum `<div id="horizonWarn"`), tambah:
```html
    <div id="temaNarasi" class="mut" style="padding:8px 15px;border-bottom:1px solid var(--line2)" hidden></div>
```
Sebelum `function renderChips()` tambahkan:
```js
  function renderTema() {
    var sel = $("tema");
    var cur = S.temaNama || "Semua";
    var names = ((S.tema && S.tema.tema) || []).map(function (t) { return t.nama; });
    sel.innerHTML = '<option value="Semua">Semua Tema</option>' + names.map(function (n) {
      return '<option value="' + n + '"' + (n === cur ? " selected" : "") + ">" + n + "</option>";
    }).join("");
    if (names.indexOf(cur) < 0) { cur = "Semua"; sel.value = "Semua"; }
    S.temaNama = cur;
    S._temaMap = {};
    ((S.tema && S.tema.tema) || []).forEach(function (t) {
      (t.emiten || []).forEach(function (k) { if (!S._temaMap[k]) S._temaMap[k] = t.nama; });
    });
    var nar = $("temaNarasi");
    var cur_t = ((S.tema && S.tema.tema) || []).filter(function (t) { return t.nama === cur; })[0];
    if (!cur_t) { nar.hidden = true; return; }
    var d = S.data.filter(function (x) { return (S._temaMap[x.kode] || "") === cur; });
    var berWajar = d.filter(function (x) { return ((cur_t.wajar || {})[x.kode] || 0) > 0; });
    var diAtas = berWajar.filter(function (x) { return SP.toNum(x.r.harga) > (cur_t.wajar[x.kode] || 0); }).length;
    nar.textContent = (cur_t.deskripsi || "") + " (" + d.length + " saham termuat" +
      (berWajar.length ? ", " + diAtas + "/" + berWajar.length + " di atas FV Sesaham" : "") + ")";
    nar.hidden = d.length === 0;
  }
  $("tema").onchange = function () { S.temaNama = this.value; renderTema(); render(); };
```
Catatan: `$("tema").onchange` di top-level IIFE aman karena skrip di akhir body.
Di `render()`, setelah baris filter metode tambahkan:
```js
    if (S.temaNama && S.temaNama !== "Semua") d = d.filter(function (x) { return (S._temaMap || {})[x.kode] === S.temaNama; });
```
Di `rebuild()`, ubah urutan menjadi `updateUmur(); renderTema(); render(); ...`
(renderTema dulu agar peta tema segar sebelum render memfilter).
Inisialisasi: `S.temaNama = "Semua";` — tambahkan ke deklarasi `var S` sebagai `temaNama: "Semua"`.

- [ ] **Step 5: Blok drawer smart-money**

Tepat sebelum `function alasanFase(x) {` (setelah `levelBox`) sisipkan:
```js
  function smBox(x) {
    var e = (S.scope.emiten || {})[x.kode];
    var wj = null;
    ((S.tema && S.tema.tema) || []).forEach(function (t) { if ((t.wajar || {})[x.kode]) wj = t.wajar[x.kode]; });
    var m = SP.smartMoney(x, e, wj);
    if (!m.terbaik) return '<div class="mut" style="margin-top:6px">Belum ada harga smart-money pembanding.</div>';
    var rows = m.rows.map(function (r) {
      return row(r.sumber + " (avg " + nf(r.avg, 0) + ")", '<span class="' + (r.pnl > 0 ? "neg" : "pos") + '">' + (r.pnl > 0 ? "+" : "") + nf(r.pnl, 1) + "%</span>" + (r.extra ? ' <span class="mut">' + r.extra + "</span>" : ""));
    }).join("");
    var vonis = m.jarakPct <= 0
      ? "Harga kita " + nf(Math.abs(m.jarakPct), 1) + "% di bawah avg " + m.terbaik.sumber + "."
      : "Harga kita " + nf(m.jarakPct, 1) + "% di atas avg " + m.terbaik.sumber + ".";
    if (m.upsidePct != null) vonis += " Mereka sudah " + nf((SP.toNum(x.r.harga) / m.terbaik.avg - 1) * 100, 1) + "% · upside tersisa " + nf(m.upsidePct, 1) + "% ke FV.";
    if (m.wajar) vonis += " FV Sesaham: " + nf(m.wajar, 0) + ".";
    var jauh = m.jarakPct > 10;
    if (jauh && x.fase === "Distribusi") vonis += " Fase distribusi terdeteksi.";
    return '<div style="margin-top:8px"><b>Smart money vs harga kita</b>' + rows +
      '<div class="' + (jauh ? "warn" : "note") + '" style="margin-top:6px">' + (jauh ? "Terlalu jauh di atas harga smart money — rawan distribusi, jangan chase; tunggu pullback ke dekat avg mereka. " : "") + vonis + "</div></div>";
  }
```
Di langkah 3 drawer, setelah baris `levelBox(x) +` tambahkan:
```js
      smBox(x) +
```
(Catatan vonis: "Mereka sudah +x%" = PNL sumber termurah = (`harga/avg-1`) — sama dengan jarakPct bila positif; bila jarak negatif (kita di bawah avg mereka) maka mereka rugi → tampilkan juga apa adanya. Rumus di atas memakai harga vs avg terbaik — konsisten.)

- [ ] **Step 6: Jalankan uji sampai lolos**

Run: `node tests/_test-praktis.js`
Expected: PASS — "Semua uji lulus".

- [ ] **Step 7: Uji manual browser (wajib)**

1. Server: Download Data → `data/tema.json` tertulis (bila network ke sesaham OK; bila gagal, siapkan manual: salin contoh 2 tema ke `data/tema-manual.json`? TIDAK — fallback: dropdown hidden, tidak error).
2. Toolbar: dropdown Tema + pilih tema → tabel tersaring + narasi tampil.
3. Dropdown Metode: 5 label ID + tooltip; nilai lama (bila ada) jatuh ke Semua.
4. Drawer: blok smart-money cocok vs KSEI/scope; tanpa scope → pesan butuh Download.
