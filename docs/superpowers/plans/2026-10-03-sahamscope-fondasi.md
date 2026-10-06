# SahamScope Fondasi Ingestion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unduh + cache data SahamScope (pulse, broker, insider) untuk watchlist dan sajikan ke frontend dengan badge kesegaran.

**Architecture:** Modul Python baru `scripts/fetch-sahamscope.py` (stdlib saja) dipanggil dari `muat_semua()` dengan cache 24 jam; kegagalan tidak menggagalkan Download; frontend membaca via respons Download dan `GET /api/scope` (dengan fallback berkas disk).

**Tech Stack:** Python stdlib (`urllib`, `json`), `app/app-screener.py`, vanilla JS satu file HTML, Node smoke test. Tanpa dependensi baru.

## Global Constraints

- Python hanya standard library (proyek tanpa requirements).
- Kegagalan scope TIDAK menggagalkan Download Data (KSEI/Yahoo tetap jalan).
- Cache 24 jam; Scan Pasar tidak memicu fetch scope (cakupan watchlist saja).
- Static files besar/basi tidak diunduh otomatis.
- Frontend: badge 3 kondisi (segar/basi+gagal/absen); drawer belum berubah.
- Tanpa kolom/skor/flag baru; tanpa rebuild `.exe` (launcher mode source).

---

### Task 1: Modul `scripts/fetch-sahamscope.py`

**Files:**
- Create: `scripts/fetch-sahamscope.py`
- Test: cek offline via `python -c` (tanpa network; hanya impor + fungsi ringkas murni)

**Interfaces:**
- Consumes: tidak ada (HTTP langsung ke `https://www.sahamscope.web.id`)
- Produces: `ambil_scope(kodes, log_fn=None)` → dict `{diambil, pulse: {tgl, top_net_buy[5: {kode,broker,nval}], highlight_insiders[10]}, emiten: {KODE: {acc: {top_buyers[5], top_sellers[5], series: {BROKER: [[nval,cum] ≤30]}}, insider: [≤10 item]}}, gagal: [...]}`; menulis `sahamscope.json` (best-effort) di cwd. Me-raise `RuntimeError` bila pulse DAN semua emiten gagal total.

- [ ] **Step 1: Tulis cek gagal**

Run:
```bash
python -c "import importlib.util; s=importlib.util.spec_from_file_location('sc','scripts/fetch-sahamscope.py'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); print('impor OK')"
```
Expected: FAIL dengan `FileNotFoundError` (berkas belum ada).

- [ ] **Step 2: Implementasi modul**

Tulis `scripts/fetch-sahamscope.py` persis:
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fetch-sahamscope.py: broker/insider SahamScope (gratis, tanpa kunci)."""
import json
import time
import urllib.request
from datetime import datetime, timedelta

BASE = "https://www.sahamscope.web.id"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
CACHE_FILE = "sahamscope.json"


def _get(path, timeout=30):
    req = urllib.request.Request(BASE + path, headers={
        "User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def ringkas_pulse(d):
    d = d or {}
    return {
        "tgl": d.get("trade_date", ""),
        "top_net_buy": [{"kode": b.get("stock_code", ""), "broker": b.get("broker_code", ""),
                         "nval": b.get("nval") or 0}
                        for b in (d.get("top_net_buy") or [])[:5]],
        "highlight_insiders": [{"kode": b.get("stock_code", ""), "nama": b.get("name", ""),
                                "tgl": b.get("date", ""), "aksi": b.get("action_type", "")}
                               for b in (d.get("highlight_insiders") or [])[:10]],
    }


def ringkas_acc(acc):
    acc = acc or {}
    out = {"top_buyers": [], "top_sellers": [], "series": {}}
    for b in (acc.get("top_buyers") or [])[:5]:
        out["top_buyers"].append({"broker": b.get("broker_code", ""), "nval": b.get("total_nval") or 0})
    for b in (acc.get("top_sellers") or [])[:5]:
        out["top_sellers"].append({"broker": b.get("broker_code", ""), "nval": b.get("total_nval") or 0})
    for br in (acc.get("series") or []):
        pts = br.get("points") or []
        out["series"][br.get("broker_code", "")] = [
            [p.get("nval") or 0, p.get("cum_nval") or 0] for p in pts[-30:]]
    return out


def ambil_scope(kodes, log_fn=None, delay=1.0, hari=30):
    log = log_fn or (lambda m: None)
    mulai = (datetime.now() - timedelta(days=hari)).strftime("%Y-%m-%d")
    gagal, emiten = [], {}
    try:
        pulse = ringkas_pulse(_get("/api/market/dashboard-summary"))
    except Exception as e:  # noqa: BLE001
        pulse = {"tgl": "", "top_net_buy": [], "highlight_insiders": []}
        gagal.append("pulse: %s" % str(e)[:80])
    for kode in (kodes or []):
        try:
            acc = ringkas_acc(_get("/api/broker-accumulation/%s?top=5&start_date=%s" % (kode, mulai)))
            time.sleep(delay)
            ins = _get("/api/insiders/%s?page_size=10" % kode)
            emiten[kode] = {"acc": acc, "insider": (ins or {}).get("items", [])[:10]}
            log("%s ok" % kode)
        except Exception as e:  # noqa: BLE001
            gagal.append("%s: %s" % (kode, str(e)[:80]))
    if not pulse["top_net_buy"] and not emiten:
        raise RuntimeError("SahamScope gagal total (%s)" % ("; ".join(gagal)[:160]))
    hasil = {"diambil": datetime.now().astimezone().isoformat(timespec="seconds"),
             "pulse": pulse, "emiten": emiten, "gagal": gagal}
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as fh:
            json.dump(hasil, fh, ensure_ascii=False)
    except OSError:
        pass
    return hasil


if __name__ == "__main__":
    import sys
    out = ambil_scope([a.upper() for a in sys.argv[1:]] or ["BBCA"])
    print("emiten: %d, gagal: %d" % (len(out["emiten"]), len(out["gagal"])))
```

- [ ] **Step 3: Uji offline fungsi ringkas (tanpa network)**

Run:
```bash
python -c "import importlib.util; s=importlib.util.spec_from_file_location('sc','scripts/fetch-sahamscope.py'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); p=m.ringkas_pulse({'trade_date':'2026-10-02','top_net_buy':[{'stock_code':'GOTO','broker_code':'MG','nval':1}],'highlight_insiders':[]}); assert p['tgl']=='2026-10-02' and p['top_net_buy'][0]['broker']=='MG'; a=m.ringkas_acc({'top_buyers':[{'broker_code':'OD','total_nval':5}],'top_sellers':[],'series':[{'broker_code':'OD','points':[{'nval':1,'cum_nval':2}]}]}); assert a['series']['OD']==[[1,2]]; print('ringkas OK')"
```
Expected: mencetak `ringkas OK`.

- [ ] **Step 4: Uji live sekali (butuh internet)**

Run: `python scripts/fetch-sahamscope.py BBCA TLKM`
Expected: mencetak `emiten: 2, gagal: 0` dan berkas `sahamscope.json` tertulis (di folder kerja saat itu; hapus berkas uji bila di luar `data/`).

### Task 2: Wiring server (`app/app-screener.py`)

**Files:**
- Modify: `app/app-screener.py` (loader modul, `CACHE_SCOPE`, `ambil_scope`, `muat_semua`, rute `/api/scope`)
- Test: `python -m py_compile` + cek string rute + uji live via server lokal

**Interfaces:**
- Consumes: `scripts/fetch-sahamscope.py` dari Task 1; pola `cache_ambil`/`tulis_log`/`_cache` yang ada
- Produces: respons Download berisi `"scope": {...}`; `GET /api/scope` → cache memori/disk; dipakai Task 3.

- [ ] **Step 1: Tambah loader + konstanta + fungsi ambil**

Setelah blok `_fd = None` / `_ksei = None` (baris ~105-106) tambahkan `_scope = None  # fetch-sahamscope`. Setelah fungsi `modul()` tambahkan:
```python
CACHE_SCOPE = 24 * 3600   # 24 jam


def modul_scope():
    global _scope
    if _scope is None:
        _scope = load_mod("fetch_scope", "fetch-sahamscope.py")
    return _scope


def ambil_scope(kodes):
    sc = modul_scope()
    return sc.ambil_scope(kodes, log_fn=lambda m: tulis_log("scope " + m.strip() if m else ""))
```
Letak `CACHE_SCOPE` boleh di dekat `CACHE_EMITEN` (baris ~84); yang penting satu konstanta bernama itu ada.

- [ ] **Step 2: Panggil di `muat_semua()` (tidak menggagalkan)**

Setelah blok emiten (setelah cek `if not saham:` yang me-return error, sebelum `say("Selesai...")`) sisipkan:
```python
    say("Mengunduh broker & insider (SahamScope, watchlist)...")
    try:
        scope = cache_ambil("scope", CACHE_SCOPE, lambda: ambil_scope(kodes), log_fn=say)
    except Exception as e:  # noqa: BLE001
        tulis_log("scope gagal: %s" % e)
        say("SahamScope gagal — memakai cache lama bila ada.")
        scope = (_cache.get("scope") or {}).get("v")
```
Dan di dict `hasil` tambahkan `"scope": scope or {},` setelah `"saham": saham,`.

- [ ] **Step 3: Tambah rute `/api/scope` (dengan fallback disk)**

Setelah blok `if jalur == "/api/scan": ...` (sebelum `if jalur == "/favicon.ico":`) sisipkan:
```python
            if jalur == "/api/scope":
                sc = (_cache.get("scope") or {}).get("v")
                if not sc:
                    try:
                        with open("sahamscope.json", "r", encoding="utf-8") as fh:
                            sc = json.load(fh)
                        _cache["scope"] = {"t": time.time(), "v": sc}
                    except (OSError, json.JSONDecodeError):
                        sc = None
                if not sc:
                    return self._json({"ok": False, "error": "belum ada cache scope — klik Download Data dulu."}, 404)
                return self._json({"ok": True, "scope": sc})
```
(Catatan: server `os.chdir(DATA_DIR)` saat start, jadi `"sahamscope.json"` relatif = folder `data/`.)

- [ ] **Step 4: Verifikasi sintaks + rute**

Run:
```bash
python -m py_compile app/app-screener.py scripts/fetch-sahamscope.py
Select-String -LiteralPath "app/app-screener.py" -Pattern "/api/scope" -SimpleMatch
Select-String -LiteralPath "app/app-screener.py" -Pattern '"scope": scope' -SimpleMatch
```
Expected: kompilasi tanpa error; rute `/api/scope` dan hasil `"scope"` ditemukan.

- [ ] **Step 5: Uji live server lokal**

Run: `python app/app-screener.py` (tanpa `SCREENER_NO_BROWSER`, biarkan browser terbuka atau set `SCREENER_NO_BROWSER=1`), lalu di PowerShell lain:
```bash
Invoke-WebRequest http://127.0.0.1:8765/api/scope -UseBasicParsing | Select-Object -ExpandProperty Content
```
Expected: 404 "belum ada cache scope" sebelum Download; setelah klik Download Data: 200 berisi `diambil` + `pulse` + `emiten`. Matikan server setelah uji.

### Task 3: Frontend badge + state (`web/screener-praktis.html`)

**Files:**
- Modify: `web/screener-praktis.html` (state `S`, handler Download, init `/api/scope`, `renderMacro`)
- Test: `tests/_test-praktis.js` (3 cek string) + uji manual browser

**Interfaces:**
- Consumes: respons Download `"scope"` dan `GET /api/scope` dari Task 2
- Produces: UI selesai — badge makro 3 kondisi; dikonsumsi sub-proyek 1–3 via `S.scope`.

- [ ] **Step 1: Tambah 3 cek string HTML ke uji**

Di `tests/_test-praktis.js` blok 7, setelah baris `cek("rincian FV drawer ada"...`, tambahkan:
```js
  cek("state scope ada", html.includes("scope: {}"));
  cek("endpoint scope dipakai", html.includes("/api/scope"));
  cek("badge Scope di makro", html.includes("Scope:</span>"));
```

- [ ] **Step 2: Jalankan uji untuk pastikan 3 cek baru gagal**

Run: `node tests/_test-praktis.js`
Expected: FAIL tepat pada 3 cek baru; semua cek lama PASS.

- [ ] **Step 3: Tambah state + isi dari Download**

Ubah deklarasi `var S = { data: [], ksei: {}, ...}` menjadi berisi `scope: {}` tepat setelah `ksei: {},`:
```js
  var S = { data: [], ksei: {}, scope: {}, pasar: null, sortKey: "skor", sortDir: -1, filter: "Semua", q: "", metode: "Semua" };
```
Di handler `$("btnDownload").onclick`, setelah baris `SP.ingestKsei(j.ksei || {}, S.ksei);` tambahkan:
```js
      S.scope = j.scope || {};
```

- [ ] **Step 4: Muat cache saat init**

Temukan baris init `renderChips(); renderAdv(); muatKontrak(); render(); renderHorizon();` dan tepat sebelumnya sisipkan:
```js
  fetch("/api/scope").then(function (r) { return r.json(); }).then(function (j) {
    if (j && j.ok && j.scope) { S.scope = j.scope; renderMacro(); }
  }).catch(function () {});
```

- [ ] **Step 5: Badge di `renderMacro()` (3 kondisi)**

Di awal `renderMacro()`, tepat setelah `var p = S.pasar;` sisipkan:
```js
    var scopeItem = "";
    var scp = S.scope || {};
    if (scp.diambil) {
      var segar = false;
      try { segar = (Date.now() - Date.parse(scp.diambil)) < 24 * 3600 * 1000; } catch (e) {}
      var tglSc = String(scp.diambil).slice(0, 10);
      var gagalSc = scp.gagal && scp.gagal.length;
      var txtSc = (!segar ? "basi " : "") + (gagalSc ? "gagal · " : "") + tglSc;
      scopeItem = '<div class="m"><span>Scope:</span><b class="' + ((!segar || gagalSc) ? "kuning" : "") + '" title="' +
        (gagalSc ? scp.gagal.slice(0, 3).join("; ") : "Pulse T-1 + broker/insider watchlist") + '">' + txtSc + "</b></div>";
    }
```
Ubah dua penempatan innerHTML: cabang tanpa regime `$("macro").innerHTML = sekItem;` → `$("macro").innerHTML = sekItem + scopeItem;`, dan cabang regime `+ sekItem;` → `+ sekItem + scopeItem;`.

- [ ] **Step 6: Jalankan uji sampai lolos**

Run: `node tests/_test-praktis.js`
Expected: PASS — "Semua uji lulus".

- [ ] **Step 7: Uji manual browser (wajib sebelum selesai)**

1. Jalankan via `Screener Saham.exe`, klik **Download Data**: badge "Scope {tgl}" muncul di makro; `data/sahamscope.json` tertulis.
2. Refresh halaman tanpa Download: badge tetap muncul (fallback `/api/scope` dari disk).
3. Simulasi gagal: hentikan internet → Download ulang → badge kuning + data lama tetap tampil, Download tidak error.
