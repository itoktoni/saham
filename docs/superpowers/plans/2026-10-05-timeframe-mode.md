# Timeframe Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 4 mode timeframe (Scalping max 1 day / Kilat max 2–3 day / Mingguan max 1 week / Bulanan max 1 month) yang mengubah bobot skor, filter, aksi, dan menampilkan chip countdown SISA/KDL.

**Architecture:** Fungsi murni baru `SP.skorTF / SP.aksiTF / SP.sisaTF` + tabel config `SP.TF` di modul SP; fungsi lama `skor/aksi/build` TAK tersentuh (Bulanan = perilaku lama, semua uji lama tetap hijau). UI menghitung nilai display per-baris dari `S.tf` tanpa rebuild data.

**Tech Stack:** Vanilla JS satu file HTML tanpa CDN (`web/screener-praktis.html`), smoke test Node (`tests/_test-praktis.js`, run: `node tests/_test-praktis.js` dari folder repo).

## Global Constraints

- Satu file HTML offline tanpa CDN — tidak tambah dependensi eksternal.
- Fungsi `skor`, `aksi`, `build`, `detectFase`, `suspen`, `bounty`, `combo`, `exitLevel` yang ada tidak boleh berubah perilakunya (uji lama 1–21 tetap hijau).
- Semua mode: fase Distribusi → Hindari, tanpa kecuali.
- Bobot Scalping/Kilat/Mingguan adalah tebakan beralasan TANPA backtest — banner wajib menampilkan "belum terkalibrasi".
- Tanpa rebuild `.exe` (launcher mode source).
- Workspace ini BUKAN git repo — tidak ada commit; langkah terakhir tiap task adalah verifikasi, bukan `git commit`.

## File Map

- Modify `web/screener-praktis.html`:
  - Modul SP: sisipkan `TF`, `skorTF`, `aksiTF`, `sisaTF` setelah fungsi `aksi` (baris ~752), export di `return` SP (baris ~819, pola `suspen: suspen`).
  - UI: segmented control di `.toolbar` setelah `<select id="metode">` (baris ~164); chip SISA digabung ke sel aksi di `render()` (cari `aksiBadge(x.aksi)`); `renderHorizon()` + drawer `dwHorizon` migrasi ke `sp_tf`.
- Modify `tests/_test-praktis.js`: blok `// 22) timeframe` sebelum baris rekap `console.log(gagal` (baris ~387).

---

### Task 1: `SP.TF` + `skorTF` + `aksiTF` + `sisaTF` + uji

**Files:**
- Modify: `web/screener-praktis.html` (modul SP, setelah fungsi `aksi`, sebelum `function build`)
- Test: `tests/_test-praktis.js` (blok `// 22) timeframe` sebelum rekap)

**Interfaces:**
- Consumes: `toNum`, `clamp` (sudah ada di modul SP); `SP.aksi`, `SP.statusKontrak`, `SP._hari` (pola baca: `_hari` privat — `sisaTF` implementasi sendiri dari `Date.parse`, tidak memakai yang privat).
- Produces: `SP.TF` (object config), `SP.skorTF(r,k,fase,val,tf)` → integer 0..100, `SP.aksiTF(fase,sc,val,pos,mosBandar,tf,extra)` → string aksi, `SP.sisaTF(bukaISO,nowISO,tf)` → `{sisa, lewat, label}`.

- [ ] **Step 1: Tambah blok uji yang gagal**

Di `tests/_test-praktis.js`, tepat sebelum baris `console.log(gagal ? ("\n" + gagal` (baris ~387), sisipkan:
```js
// 22) timeframe mode
{
  const r = { harga: "1000", eps: "100", ekuitas: "50000", saham: "1000", laba: "10000", cagr: "10", der: "0.5", eps_trend: "up", nilai_harian: "9000000000", s_vol_ratio: "1.5", s_freqspike: "0", s_sideways: "0", ret20: "0.05" };
  const val = SP.valuasi(r, {});
  const k = { dksei_asing_1m: 1.0, dksei_institusi_1m: 0.5 };
  cek("tf: config 4 mode ada", ["scalp", "kilat", "minggu", "bulan"].every(t => !!(SP.TF && SP.TF[t])), JSON.stringify(SP.TF && Object.keys(SP.TF)));
  const sScalp = SP.skorTF(r, k, "Markup", val, "scalp");
  const sBulan = SP.skorTF(r, k, "Markup", val, "bulan");
  cek("tf: skor integer 0..100 semua mode", ["scalp", "kilat", "minggu", "bulan"].every(t => { const s = SP.skorTF(r, k, "Markup", val, t); return Number.isInteger(s) && s >= 0 && s <= 100; }));
  const rMurah = Object.assign({}, r, { harga: "100" });
  const rMahal = Object.assign({}, r, { harga: "5000" });
  cek("tf: scalping abaikan MOS (murah==mahal)", SP.skorTF(rMurah, k, "Markup", SP.valuasi(rMurah, {}), "scalp") === SP.skorTF(rMahal, k, "Markup", SP.valuasi(rMahal, {}), "scalp"));
  cek("tf: bulanan bedakan murah vs mahal", SP.skorTF(rMurah, k, "Markup", SP.valuasi(rMurah, {}), "bulan") !== SP.skorTF(rMahal, k, "Markup", SP.valuasi(rMahal, {}), "bulan"));
  cek("tf: distribusi selalu Hindari", ["scalp", "kilat", "minggu", "bulan"].every(t => SP.aksiTF("Distribusi", 95, val, 0.9, null, t, {}) === "Hindari"));
  cek("tf: scalp lock H+0 bukan Beli", SP.aksiTF("Markup", 90, val, 0.6, null, "kilat", { isLockH0: true }) !== "Beli");
  const sisa = SP.sisaTF("2026-10-01", "2026-10-05", "kilat");
  cek("tf: sisa kilat H+3 KDL", sisa.lewat === true && sisa.label === "KDL", JSON.stringify(sisa));
  const sisa2 = SP.sisaTF("2026-10-04", "2026-10-05", "minggu");
  cek("tf: sisa minggu H+1", sisa2.lewat === false && sisa2.label === "H+1", JSON.stringify(sisa2));
  cek("tf: mode tak dikenal jatuh ke bulan", SP.skorTF(r, k, "Markup", val, "ngaco") === SP.skorTF(r, k, "Markup", val, "bulan"));
}
```

- [ ] **Step 2: Jalankan uji untuk pastikan gagal**

Run: `node tests/_test-praktis.js`
Expected: FAIL pada 10 cek baru (`SP.TF` undefined / `SP.skorTF is not a function`); semua cek 1–21 PASS.

- [ ] **Step 3: Implementasi minimal**

Sisipkan SETELAH akhir fungsi `aksi` (baris `}` penutup `aksi`, tepat sebelum `function build`), di dalam modul SP:
```js
  // ---------- mode timeframe (display + filter, skor tak sentuh rumus lama) ----------
  var TF = {
    scalp: { label: "Scalping · max 1 day", maxHold: 1, w: { nilai: 0, kualitas: 0.10, timing: 0.30, aliran: 0.30, mom: 0.30 }, minLiq: 5000000000, hideDist: true, kalibrasi: false },
    kilat: { label: "Kilat · max 2–3 day", maxHold: 3, w: { nilai: 0.10, kualitas: 0.20, timing: 0.30, aliran: 0.15, mom: 0.25 }, minLiq: 1000000000, hideDist: true, kalibrasi: false },
    minggu: { label: "Mingguan · max 1 week", maxHold: 7, w: { nilai: 0.15, kualitas: 0.25, timing: 0.20, aliran: 0.10, mom: 0.30 }, minLiq: 500000000, hideDist: false, kalibrasi: false },
    bulan: { label: "Bulanan · max 1 month", maxHold: 30, w: { nilai: 0.15, kualitas: 0.30, timing: 0.15, aliran: 0.10, mom: 0.30 }, minLiq: 500000000, hideDist: false, kalibrasi: true }
  };
  function tfCfg(tf) { return TF[tf] || TF.bulan; }
  function skorTF(r, k, fase, val, tf) {
    var c = tfCfg(tf), w = c.w;
    var sNilai;
    if (w.nilai <= 0) { sNilai = 50; }
    else {
      sNilai = clamp((val.mos + 20) / 70 * 100, 0, val.mos > 50 ? 65 : 100);
      var h52 = toNum(r.high_52), harga = toNum(r.harga);
      var draw = (h52 > 0 && harga > 0) ? Math.max(0, (h52 - harga) / h52) : 0;
      sNilai = sNilai * clamp(1 - draw / 0.6, 0.35, 1);
      if (k.asing_avg_price && harga > 0) {
        var mosBandar = (k.asing_avg_price - harga) / k.asing_avg_price * 100;
        sNilai = w.nilai >= 0.15
          ? 0.6 * sNilai + 0.4 * clamp((mosBandar + 20) / 70 * 100, 0, 100)
          : clamp((mosBandar + 20) / 70 * 100, 0, 100);
      }
    }
    var sKualitas = 50;
    if (val.roe >= 15) sKualitas += 20; else if (val.roe >= 8) sKualitas += 10;
    if (toNum(r.der) > 1.5) sKualitas -= 20;
    if (r.eps_trend === "up") sKualitas += 10; else if (r.eps_trend === "down") sKualitas -= 15;
    if (toNum(r.laba) > 0 || val.roe > 0) sKualitas += 10; else sKualitas -= 20;
    sKualitas = clamp(sKualitas, 0, 100);
    var sTiming = { "Spring": 90, "Akumulasi": 78, "Markup": 68, "Netral": 50, "Distribusi": 15 }[fase];
    if (sTiming == null) sTiming = 50;
    if (toNum(r.s_freqspike) === 1) sTiming += 5;
    if (toNum(r.s_vol_ratio) >= 1.3) sTiming += 5;
    if (fase === "Netral" && toNum(r.s_sideways) === 1) sTiming += 8;
    sTiming = clamp(sTiming, 0, 100);
    var dA = k.dksei_asing_1m == null ? 0 : k.dksei_asing_1m;
    var dI = k.dksei_institusi_1m == null ? 0 : k.dksei_institusi_1m;
    var sAliran = clamp(50 + Math.max(dA, dI) * 8, 0, 100);
    var sMom = (r.ret20 == null || r.ret20 === "") ? 50 : clamp(50 - toNum(r.ret20) * 4, 0, 100);
    return Math.round(w.nilai * sNilai + w.kualitas * sKualitas + w.timing * sTiming + w.aliran * sAliran + w.mom * sMom);
  }
  function aksiTF(fase, sc, val, pos, mosBandar, tf, extra) {
    extra = extra || {};
    if (fase === "Distribusi") return "Hindari";
    if (extra.lewatHold) return (val.mos > 0 && (fase === "Akumulasi" || fase === "Spring")) ? "Pantau" : "Hindari";
    if (tf === "scalp") {
      if (!(fase === "Markup" || fase === "Spring")) return "Hindari";
      return sc >= 60 ? "Beli" : "Pantau";
    }
    if (tf === "kilat") {
      if (extra.isLockH0) return "Pantau";
      if (fase !== "Markup") return fase === "Distribusi" ? "Hindari" : "Pantau";
      return sc >= 60 ? "Beli" : "Pantau";
    }
    if (tf === "minggu") return aksi(fase, sc, val, pos, mosBandar);
    return aksi(fase, sc, val, pos, mosBandar);
  }
  function sisaTF(bukaISO, nowISO, tf) {
    var c = tfCfg(tf);
    var a = Date.parse(String(bukaISO) + "T00:00:00"), b = Date.parse(String(nowISO) + "T00:00:00");
    if (!isFinite(a) || !isFinite(b)) return { sisa: 0, lewat: true, label: "KDL" };
    var hari = Math.max(0, Math.floor((b - a) / 86400000));
    var sisa = c.maxHold - hari;
    if (sisa < 0) return { sisa: sisa, lewat: true, label: "KDL" };
    return { sisa: sisa, lewat: false, label: "H+" + hari };
  }
```

Di blok `return` modul SP, ubah baris yang memuat `skor: skor, aksi: aksi,` menjadi juga mengekspor `TF: TF, tfCfg: tfCfg, skorTF: skorTF, aksiTF: aksiTF, sisaTF: sisaTF,` (sisipkan setelah `aksi: aksi,`).

- [ ] **Step 4: Jalankan uji sampai lolos**

Run: `node tests/_test-praktis.js`
Expected: PASS — "Semua uji lulus", termasuk 10 cek blok 22; cek 1–21 tetap hijau (fungsi lama tak tersentuh).

- [ ] **Step 5: Verifikasi akhir Task 1 (tanpa commit — bukan git repo)**

Run ulang penuh + cek tidak ada perubahan perilaku lama:
Run: `node tests/_test-praktis.js`
Expected: PASS penuh. Lanjut Task 2.

---

### Task 2: Segmented control + chip SISA + banner + migrasi

**Files:**
- Modify: `web/screener-praktis.html` (CSS 2 baris, toolbar, `render()`, `renderHorizon()`, drawer `dwHorizon`)
- Test: `tests/_test-praktis.js` (cek string di blok 22)

**Interfaces:**
- Consumes: `SP.TF`, `SP.skorTF`, `SP.aksiTF`, `SP.sisaTF` dari Task 1; `S.data` (record `build()`), `S.tf` (state baru, default `"bulan"`), `hariIni()`, `aksiBadge()`, `renderHorizon()`.
- Produces: UI selesai. Tidak ada API baru. `S.data` tidak di-rebuild saat ganti mode (skor/aksi display dihitung di `render()`).

- [ ] **Step 1: Tambah cek string ke uji (gagal dulu)**

Di akhir blok `// 22) timeframe` (setelah cek `mode tak dikenal`), tambahkan:
```js
  cek("tf: segmented control ada", html.includes('id="tfSeg"') && html.includes("max 1 day") && html.includes("max 2") && html.includes("max 1 week") && html.includes("max 1 month"));
  cek("tf: sp_tf dipakai", html.includes("sp_tf"));
  cek("tf: chip sisa ada", html.includes("sisaChip") || html.includes("SISA"));
  cek("tf: banner belum terkalibrasi", html.includes("belum terkalibrasi"));
```

- [ ] **Step 2: Jalankan uji untuk pastikan 4 cek baru gagal**

Run: `node tests/_test-praktis.js`
Expected: FAIL tepat pada 4 cek string baru; semua cek fungsi Task 1 + cek 1–21 PASS.

- [ ] **Step 3: CSS + toolbar + state**

CSS (sisipkan setelah baris `.kode-susp{color:#d00;font-weight:700}`):
```css
.tfseg{display:inline-flex;gap:4px;margin-left:8px}
.tfseg button{border:1px solid var(--line2);background:transparent;border-radius:99px;padding:3px 10px;font-size:12px;cursor:pointer}
.tfseg button.on{background:#1f5fd0;color:#fff;border-color:#1f5fd0}
.sisaChip{font-size:11px;border:1px solid var(--line2);border-radius:99px;padding:1px 7px;margin-left:6px;white-space:nowrap}
.sisaChip.kdl{color:#d00;border-color:#d00;font-weight:700}
```

Toolbar: setelah `</select>` penutup `#metode` (baris ~164), sisipkan:
```html
<div class="tfseg" id="tfSeg" title="Mode timeframe — mengubah bobot skor, filter, dan max-hold"></div>
```

State + render (di dekat `renderChips`, baris ~1125): tambahkan
```js
  function tfAktif() { var t = "bulan"; try { t = localStorage.getItem("sp_tf") || migrasiTf() || "bulan"; } catch (e) {} S.tf = (SP.TF && SP.TF[t]) ? t : "bulan"; return S.tf; }
  function migrasiTf() { try { var h = localStorage.getItem("sp_horizon"); if (h === "3") return "bulan"; if (h === "1-3") return "minggu"; if (h === "1") return "kilat"; } catch (e) {} return null; }
  function renderTfSeg() {
    var t = tfAktif();
    $("tfSeg").innerHTML = Object.keys(SP.TF).map(function (k) {
      return '<button data-tf="' + k + '"' + (k === t ? ' class="on"' : "") + ">" + SP.TF[k].label + "</button>";
    }).join("");
  }
```
Klik: di `document.onclick` (tempat `data-f` chips ditangani, dekat baris ~1110), tambahkan cabang: `var tf = e.target.closest("[data-tf]"); if (tf) { try { localStorage.setItem("sp_tf", tf.getAttribute("data-tf")); } catch (e2) {} S.tf = tfAktif(); renderTfSeg(); render(); renderHorizon(); return; }`.

- [ ] **Step 4: Skor/aksi display + chip + filter + banner**

Di `render()`: di awal, panggil `var tf = tfAktif();`. Pre-pass sebelum sort/filter akhir — untuk tiap `x` di `d` hitung dan simpan display (TANPA ubah `x.skor/x.aksi` asli):
```js
d.forEach(function (x) {
  x._scD = SP.skorTF(x.r, x.k, x.fase, x.val, tf);
  x._hold = SP.sisaTF(x.umurSejak || hariIni(), hariIni(), tf);
  x._aksiD = SP.aksiTF(x.fase, x._scD, x.val, x.pos, x.asing_pnl != null ? -x.asing_pnl : null, tf, { lewatHold: x._hold.lewat, isLockH0: !!x.lockH0 });
});
```
Filter (setelah filter `S.q`, sebelum sort): lewati baris bila `toNum(x.r.nilai_harian) < SP.TF[tf].minLiq`, atau (`SP.TF[tf].hideDist && x.fase === "Distribusi"`). Sorting kolom skor memakai display: ubah entri COLS `{ k: "skor", t: "Skor", n: true }` menjadi `{ k: "skor", t: "Skor", n: true, get: function (d) { return d._scD != null ? d._scD : d.skor; } }`. Sel skor: `'<td class="n">' + bar + x.skor` → gunakan `x._scD` untuk lebar bar dan angka. Sel aksi (baris berisi `aksiBadge(x.aksi)`): `aksiBadge(x._aksiD != null ? x._aksiD : x.aksi) + '<span class="sisaChip' + (x._hold.lewat ? " kdl" : "") + '" title="Max-hold mode ' + SP.TF[tf].label + '">' + (x._hold.lewat ? "KDL" : "SISA " + x._hold.label) + "</span>"` (bila `x._hold` null karena data lama, tampilkan aksi lama tanpa chip).

`renderHorizon()`: setelah `var horizon ...`, tambahkan note bila `!SP.TF[tfAktif()].kalibrasi`: teks "Mode ini <b>belum terkalibrasi</b> — bobot skor tebakan beralasan, pakai sebagai filter bukan ramalan."

Drawer: opsi `#dwHorizon` (baris 1270–1272) diganti 4 mode (`scalp/kilat/minggu/bulan` dengan label `SP.TF`), `onchange` tulis `sp_tf` + panggil `renderTfSeg(); render();`, note `dwHorizonNote` tampil bila mode tak terkalibrasi. Migrasi sekali via `migrasiTf()` (Step 3).

- [ ] **Step 4b: Perbarui asersi horizon lama (wajib — opsi lama dihapus)**

`tests/_test-praktis.js` baris ~114:
```js
cek("select rencana keluar ≤1 bulan di drawer", html.includes('id="dwHorizon"') && html.includes("≤1 bulan (cepat)"));
```
menjadi:
```js
cek("select timeframe 4 mode di drawer", html.includes('id="dwHorizon"') && html.includes("max 1 day") && html.includes("max 1 month"));
```
`tests/_smoke-ui.py` baris ~42–50 (test browser): ganti `select_option("#dwHorizon", "1")` → `"kilat"`, ekspektasi `localStorage.getItem('sp_horizon') == "1"` → `localStorage.getItem('sp_tf') == "kilat"`, dan `"1-3"` → `"minggu"`. Bila smoke browser tak bisa jalan di mesin ini, catat sebagai manual dan pastikan sinkron nilainya sama.

- [ ] **Step 5: Jalankan uji sampai lolos + manual browser**

Run: `node tests/_test-praktis.js`
Expected: PASS — "Semua uji lulus".
Manual (wajib): buka via `Jalankan Screener.vbs` → segmented 4 mode tampil → ganti mode: skor/aksi/filter/chip berubah → reload persist → mode scalp sembunyikan Distribusi → chip KDL muncul untuk posisi lewat max-hold → drawer sinkron dengan toolbar.

- [ ] **Step 6: Verifikasi akhir (tanpa commit — bukan git repo)**

Run: `node tests/_test-praktis.js` + `node scripts/fetch-data-idx.py --tickers BBCA,TEBE --delay 1.5` (pastikan tidak merusak alur data).
Expected: semua hijau. Selesai.

## Self-Review

1. **Spec coverage:** §2 mode+chip → Task 2 Step 3–4; §3 bobot+filter → Task 1 Step 3 (`TF`/`skorTF`) + Task 2 Step 4 (filter `minLiq`/`hideDist`); §4 aksi+exit → `aksiTF` + `sisaTF` + lock H+0; §5 UI → segmented/banner/drawer; §6 testing → blok 22 (10 cek fungsi + 4 cek string) + manual; §7 non-goals dipatuhi (tak sentuh rumus lama/fetcher/bounty, tanpa commit karena bukan git repo).
2. **Placeholder scan:** tidak ada TBD/TODO; semua kode blok lengkap; angka bobot/filter disalin verbatim dari spec yang disetujui.
3. **Type consistency:** `skorTF(r,k,fase,val,tf)` dipakai konsisten di uji + render; `aksiTF(fase,sc,val,pos,mosBandar,tf,extra)` konsisten; `sisaTF` return `{sisa, lewat, label}` dipakai konsisten (`hold.lewat`, `hold.label`); `x.lockH0` hanya dibaca boolean (produsen lock-flag di luar scope plan ini — default `false`, tidak merusak).
