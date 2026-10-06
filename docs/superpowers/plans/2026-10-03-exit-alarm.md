# Exit-Liquidity Alarm Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Peringatkan bila harga jauh di atas rata-rata jual broker distributor (atau hijau bila jauh di bawah avg buyer) via blok drawer display-only.

**Architecture:** `ringkas_acc` diperkaya avg per titik + cache berversi v2; `SP.exitLevel` murni menghitung premium vs level; `levelBox` render 3 kondisi di drawer.

**Tech Stack:** Python stdlib, vanilla JS satu file HTML, Node smoke test. `app/app-screener.py` tidak diubah.

## Global Constraints

- Python hanya standard library; TTL/fallback/cakupan watchlist tak berubah.
- Ambang simetris ±3%; level butuh ≥2 broker valid; alarm cek dulu, bargain kedua.
- Tanpa entry/avg → pesan jujur (refresh/tak cukup data), bukan alarm palsu.
- Warning-only: tanpa blokir kontrak, tanpa kolom tabel, tanpa ubah skor.
- Tanpa rebuild `.exe` (launcher mode source).

---

### Task 1: Cache v2 (`scripts/fetch-sahamscope.py`)

**Files:**
- Modify: `scripts/fetch-sahamscope.py` (`ringkas_acc` + dict `hasil` di `ambil_scope`)
- Test: cek offline via `python -c` dengan `_get` di-monkeypatch (tanpa network, tanpa merusak cache asli — kerja di tempdir)

**Interfaces:**
- Consumes: field API `bavg`/`savg` per titik (sudah ada di respons, boleh null)
- Produces: titik series `[nval, cum, bavg, savg]` (avg null lestari) + `hasil["v"] = 2`; dikonsumsi Task 2 via `S.scope`.

- [ ] **Step 1: Tulis cek gagal**

Run:
```bash
python -c "import importlib.util, tempfile, os; s=importlib.util.spec_from_file_location('sc','scripts/fetch-sahamscope.py'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); m._get=lambda p: {'trade_date':'2026-10-02','top_net_buy':[{'stock_code':'T','broker_code':'OD','nval':1}],'highlight_insiders':[]} if 'dashboard' in p else ({'top_buyers':[{'broker_code':'OD','total_nval':1}],'top_sellers':[],'series':[{'broker_code':'OD','points':[{'nval':1,'cum_nval':2,'bavg':10,'savg':None}]}]} if 'broker-acc' in p else {'items':[]}); os.chdir(tempfile.mkdtemp()); r=m.ambil_scope(['TST'],delay=0); assert r['v']==2 and r['emiten']['TST']['acc']['series']['OD']==[[1,2,10,None]], r; print('v2 OK')"
```
Expected: FAIL (`AssertionError` — titik masih 2-elemen dan tanpa kunci `v`).

- [ ] **Step 2: Implementasi minimal**

Ubah baris points di `ringkas_acc`:
```python
        out["series"][br.get("broker_code", "")] = [
            [p.get("nval") or 0, p.get("cum_nval") or 0] for p in pts[-30:]]
```
menjadi:
```python
        out["series"][br.get("broker_code", "")] = [
            [p.get("nval") or 0, p.get("cum_nval") or 0,
             p.get("bavg"), p.get("savg")] for p in pts[-30:]]
```
Dan dict `hasil` di `ambil_scope`:
```python
    hasil = {"diambil": datetime.now().astimezone().isoformat(timespec="seconds"),
             "pulse": pulse, "emiten": emiten, "gagal": gagal}
```
menjadi (tambah `"v": 2`):
```python
    hasil = {"v": 2, "diambil": datetime.now().astimezone().isoformat(timespec="seconds"),
             "pulse": pulse, "emiten": emiten, "gagal": gagal}
```

- [ ] **Step 3: Jalankan cek sampai lolos**

Run: perintah `python -c` yang sama seperti Step 1.
Expected: mencetak `v2 OK` (berkas cache uji tertulis di tempdir, cache asli aman).

### Task 2: `SP.exitLevel` + blok drawer

**Files:**
- Modify: `web/screener-praktis.html` (modul `SP`: sisip setelah `combo`, sebelum `// ---------- valuasi sederhana`; blok `return`; helper `levelBox`; langkah 3 drawer setelah `comboBox(x) +`)
- Test: `tests/_test-praktis.js` (blok 13 baru + 2 cek string) + Download ulang + manual

**Interfaces:**
- Consumes: `SP.toNum` (ada); `entry.acc` titik 4-elemen dari Task 1; `S.scope.v`
- Produces: `SP.exitLevel(x, entry, scopeV)` → `{stale:true}` bila v≠2; `null` bila tak cukup data; `{tipe:"alarm"|"bargain", premium, level, broker[]}`; dirender `levelBox`.

- [ ] **Step 1: Tambah blok uji yang gagal (blok 13)**

Di `tests/_test-praktis.js`, tepat sebelum `console.log(gagal`, sisipkan:
```js
// 13) exit-liquidity level
{
  const sv = [];
  for (let i = 0; i < 20; i++) sv.push([-1000, -1000 * (i + 1), 1000, 900 - i]);
  const sv2 = sv.map(p => [-500, p[1], 1000, p[3] - 20]);
  const bv = [];
  for (let i = 0; i < 20; i++) bv.push([1000, 1000 * (i + 1), 900 - i, 1000]);
  const scX = { acc: { top_sellers: [{ broker: "OD" }, { broker: "AK" }], top_buyers: [{ broker: "CC" }, { broker: "YU" }], series: { OD: sv, AK: sv2, CC: bv, YU: bv } } };
  const aL = SP.exitLevel({ r: { harga: "1000" }, fase: "Distribusi" }, scX, 2);
  cek("exitLevel: alarm premium + broker", aL && aL.tipe === "alarm" && aL.broker.length === 2 && aL.premium >= 3, JSON.stringify(aL));
  const bL = SP.exitLevel({ r: { harga: "800" }, fase: "Akumulasi" }, scX, 2);
  cek("exitLevel: bargain di bawah avg beli", bL && bL.tipe === "bargain", JSON.stringify(bL));
  const nL = SP.exitLevel({ r: { harga: "900" }, fase: "Netral" }, scX, 2);
  cek("exitLevel: netral tanpa alarm", nL === null, JSON.stringify(nL));
  cek("exitLevel: cache lama ditandai", SP.exitLevel({ r: { harga: "1000" }, fase: "Distribusi" }, scX, 1).stale === true);
  cek("exitLevel: tanpa savg null", SP.exitLevel({ r: { harga: "1000" }, fase: "Distribusi" }, { acc: { top_sellers: [{ broker: "OD" }], top_buyers: [], series: { OD: [[-1, -1, null, null]] } } }, 2) === null);
}
```

- [ ] **Step 2: Jalankan uji untuk pastikan gagal**

Run: `node tests/_test-praktis.js`
Expected: error `TypeError: SP.exitLevel is not a function`.

- [ ] **Step 3: Implementasi `SP.exitLevel` + ekspor**

Sisipkan setelah akhir fungsi `combo` (baris `}` tepat sebelum `// ---------- valuasi sederhana`):
```js
  // ---------- level broker exit-liquidity (display-only warning) ----------
  function exitLevel(x, entry, scopeV) {
    if (scopeV !== 2) return { stale: true };
    if (!entry) return null;
    var harga = toNum(x.r && x.r.harga);
    if (!(harga > 0)) return null;
    var acc = entry.acc || {};
    function lvlOf(list, idx) {
      var lv = [], nm = [], flow = 0;
      (list || []).slice(0, 3).forEach(function (b) {
        var pts = (acc.series && acc.series[b.broker]) || [];
        flow += pts.slice(-20).reduce(function (a, p) { return a + toNum(p[0]); }, 0);
        var av = pts.slice(-20).map(function (p) { return p[idx]; }).filter(function (v) { return v != null && v > 0; });
        if (av.length) { lv.push(av.reduce(function (a, c) { return a + c; }, 0) / av.length); nm.push(b.broker); }
      });
      if (lv.length < 2) return null;
      return { level: lv.reduce(function (a, c) { return a + c; }, 0) / lv.length, brokers: nm, flow: flow };
    }
    var s = lvlOf(acc.top_sellers, 3);
    var b = lvlOf(acc.top_buyers, 2);
    if (s && harga >= s.level * 1.03 && (x.fase === "Distribusi" || x.fase === "Markup") && s.flow < 0)
      return { tipe: "alarm", premium: (harga / s.level - 1) * 100, level: s.level, broker: s.brokers };
    if (b && harga <= b.level * 0.97)
      return { tipe: "bargain", premium: (harga / b.level - 1) * 100, level: b.level, broker: b.brokers };
    return null;
  }
```
Di blok `return` modul SP tambahkan `exitLevel: exitLevel,` (setelah `combo: combo,`).

- [ ] **Step 4: Tambah 2 cek string + helper `levelBox` + drawer**

Di blok 7 tambah:
```js
  cek("exitLevel ada", html.includes("SP.exitLevel"));
  cek("blok level drawer ada", html.includes("exit liquidity") && html.includes("rata-rata jual"));
```
Tepat sebelum `function alasanFase(x) {` (setelah `comboBox`) sisipkan:
```js
  function levelBox(x) {
    var scp = S.scope || {};
    if (scp.v !== 2) return '<div class="mut" style="margin-top:6px">Cache scope lama — klik Download Data untuk refresh level broker.</div>';
    var e = (scp.emiten || {})[x.kode];
    if (!e) return '<div class="mut" style="margin-top:6px">Kombo butuh Download Data (cache SahamScope).</div>';
    var L = SP.exitLevel(x, e, scp.v);
    if (!L) return '<div class="mut" style="margin-top:6px">Tak cukup data savg broker untuk level.</div>';
    var hj = nf(SP.toNum(x.r.harga), 0), lv = nf(L.level, 0);
    var ket = '<div class="mut" style="margin-top:2px">Indikasi — kode broker campuran banyak klien, bukan vonis.</div>';
    if (L.tipe === "alarm") return '<div class="warn">Harga ' + hj + " berada +" + nf(L.premium, 1) + "% di atas rata-rata jual " + L.broker.join(", ") + " (" + lv + "). Risiko jadi exit liquidity.</div>" + ket;
    return '<div class="note">Harga ' + hj + " berada " + nf(Math.abs(L.premium), 1) + "% di bawah rata-rata beli " + L.broker.join(", ") + " (" + lv + ").</div>" + ket;
  }
```
Di langkah 3 drawer, setelah baris `comboBox(x) +` tambahkan:
```js
      levelBox(x) +
```

- [ ] **Step 5: Jalankan uji sampai lolos**

Run: `node tests/_test-praktis.js`
Expected: PASS — "Semua uji lulus".

- [ ] **Step 6: Refresh cache + uji manual (wajib)**

1. Klik **Download Data** (menulis ulang cache v2; beberapa menit).
2. Buka drawer saham: blok level tampil (alarm/bargain/abu sesuai data).
3. Verifikasi 1 saham manual vs `data/sahamscope.json` (rata-rata savg top seller).
