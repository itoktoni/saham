# Bounty Board Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Papan 3 quest malam (skor pulse+streak+insider) dengan Terima/Lewat + arsip kemarin.

**Architecture:** `SP.bounty` murni menilai dan memotong 3 teratas; `renderQuest` render panel + baca/tulis `localStorage sp_bounty` date-keyed; highlight baris via class di `render()`.

**Tech Stack:** Vanilla JS satu file HTML (tanpa CDN), Node smoke test. Tanpa backend.

## Global Constraints

- Satu file HTML offline tanpa CDN — tidak tambah dependensi eksternal.
- Syarat masuk: ada entry scope DAN `nilai_harian ≥ Rp5.000.000.000`; tanpa data = tidak masuk papan.
- Bobot fixed: pulse 50 + streak n/5×30 + insider 20; seri → streak lalu abjad kode.
- Keputusan per kode per tanggal; arsip read-only 1 hari ke belakang.
- Tanpa ubah skor/aksi/fase; tanpa rebuild `.exe` (launcher mode source).

---

### Task 1: `SP.bounty` + uji smoke

**Files:**
- Modify: `web/screener-praktis.html` (modul `SP`: sisip setelah `smartMoney`, sebelum `// ---------- valuasi sederhana`; blok `return`)
- Test: `tests/_test-praktis.js` (blok 15 baru)

**Interfaces:**
- Consumes: `SP.toNum` (ada); record `build()` (`kode`, `r.nilai_harian`); scope `{pulse: {top_net_buy[{kode}]}, emiten: {KODE: {acc: {top_buyers, series}, insider[]}}}`
- Produces: `SP.bounty(data, scope)` → ≤3 `{kode, skor, rinci: {pulse, streak, insider}, jejak: {broker, hit, insiderNama}}`; dipakai Task 2.

- [ ] **Step 1: Tambah blok uji yang gagal (blok 15)**

Di `tests/_test-praktis.js`, tepat sebelum `console.log(gagal`, sisipkan:
```js
// 15) bounty 3 quest
{
  const rows15 = [
    { kode: "AA", r: { nilai_harian: "9000000000" } },
    { kode: "BB", r: { nilai_harian: "9000000000" } },
    { kode: "CC", r: { nilai_harian: "9000000000" } },
    { kode: "DD", r: { nilai_harian: "9000000000" } },
    { kode: "XX", r: { nilai_harian: "1000000" } },
    { kode: "YY", r: {} }
  ];
  const d60 = new Date(Date.now() - 10 * 864e5).toISOString().slice(0, 10);
  const sc15 = { pulse: { top_net_buy: [{ kode: "AA", broker: "OD", nval: 5 }] }, emiten: {
    AA: { acc: { top_buyers: [{ broker: "OD" }], series: { OD: [[1, 1], [1, 1], [1, 1], [1, 1], [1, 1]] } }, insider: [{ name: "DIR A", date: d60, action_type: "buy" }] },
    BB: { acc: { top_buyers: [{ broker: "CC" }], series: { CC: [[1, 1], [1, 1], [-1, 1], [1, 1], [-1, 1]] } }, insider: [] },
    CC: { acc: { top_buyers: [{ broker: "YU" }], series: { YU: [[1, 1], [1, 1], [1, 1], [1, 1], [1, 1]] } }, insider: [] },
    DD: { acc: { top_buyers: [{ broker: "SQ" }], series: { SQ: [[-1, 1], [-1, 1], [-1, 1], [-1, 1], [-1, 1]] } }, insider: [] } } };
  const bq = SP.bounty(rows15, sc15);
  cek("bounty: tepat 3 (illiquid + tanpa scope tersingkir)", bq.length === 3, JSON.stringify(bq.map(q => q.kode)));
  cek("bounty: AA teratas 100", bq[0].kode === "AA" && bq[0].skor === 100, JSON.stringify(bq[0]));
  cek("bounty: breakdown benar", bq[0].rinci.pulse === 50 && bq[0].rinci.streak === 30 && bq[0].rinci.insider === 20);
  cek("bounty: tanpa scope kosong", SP.bounty(rows15, {}).length === 0);
}
```

- [ ] **Step 2: Jalankan uji untuk pastikan gagal**

Run: `node tests/_test-praktis.js`
Expected: error `TypeError: SP.bounty is not a function`.

- [ ] **Step 3: Implementasi minimal**

Sisipkan setelah akhir fungsi `smartMoney` (baris `}` tepat sebelum `// ---------- valuasi sederhana`):
```js
  // ---------- misi malam ini (bounty 3 quest) ----------
  function bounty(data, scope) {
    data = data || [];
    var emiten = (scope && scope.emiten) || {};
    var pulse = ((scope && scope.pulse) || {}).top_net_buy || [];
    var diPulse = {};
    pulse.forEach(function (b) { diPulse[b.kode] = true; });
    var cutoff = "";
    try { cutoff = new Date(Date.now() - 60 * 864e5).toISOString().slice(0, 10); } catch (e) {}
    var out = [];
    (data || []).forEach(function (x) {
      if (toNum(x.r && x.r.nilai_harian) < 5000000000) return;
      var en = emiten[x.kode];
      if (!en) return;
      var pPts = diPulse[x.kode] ? 50 : 0;
      var acc = en.acc || {};
      var b1 = (acc.top_buyers || [])[0];
      var hit = 0, br = "";
      if (b1 && acc.series && acc.series[b1.broker]) {
        var last5 = acc.series[b1.broker].slice(-5);
        hit = last5.filter(function (p) { return toNum(p[0]) > 0; }).length;
        br = b1.broker;
      }
      var sPts = Math.round(hit / 5 * 30);
      var ins = ((en.insider) || []).filter(function (t) { return t && t.action_type === "buy" && t.date && t.date >= cutoff; });
      var iPts = ins.length ? 20 : 0;
      out.push({ kode: x.kode, skor: pPts + sPts + iPts,
        rinci: { pulse: pPts, streak: sPts, insider: iPts },
        jejak: { broker: br, hit: hit, insiderNama: ins.length ? ins[0].name.split(" ").slice(0, 2).join(" ") : "" } });
    });
    out.sort(function (a, b) {
      return (b.skor - a.skor) || (b.jejak.hit - a.jejak.hit) || (a.kode < b.kode ? -1 : (a.kode > b.kode ? 1 : 0));
    });
    return out.slice(0, 3);
  }
```
Di blok `return` modul SP tambahkan `bounty: bounty,` (setelah `smartMoney: smartMoney,`).

- [ ] **Step 4: Jalankan uji sampai lolos**

Run: `node tests/_test-praktis.js`
Expected: PASS — "Semua uji lulus", termasuk 4 cek baru blok 15 (AA=50+30+20=100 teratas; CC=30 kedua; BB=18 ketiga; DD=0 terpotong; XX/YY tersingkir).

### Task 2: Panel quest + aksi + arsip

**Files:**
- Modify: `web/screener-praktis.html` (CSS 1 baris, panel `#questPanel`, `renderQuest`, highlight di `render`, hook `rebuild`, cek string test)
- Test: `tests/_test-praktis.js` + manual browser

**Interfaces:**
- Consumes: `SP.bounty` dari Task 1; `S.data`, `S.scope`; `hariIni()`, `openDrawer`, pola `muatKontrak/simpanKontrak`
- Produces: UI selesai. `localStorage sp_bounty` = `{YYYY-MM-DD: {KODE: {status, alasan?}}}`.

- [ ] **Step 1: Tambah 3 cek string ke uji (gagal dulu)**

Di blok 7 tambah:
```js
  cek("panel quest ada", html.includes('id="questPanel"') && html.includes("Misi Malam Ini"));
  cek("bounty dipakai", html.includes("SP.bounty"));
  cek("arsip sp_bounty ada", html.includes("sp_bounty"));
```

- [ ] **Step 2: Jalankan uji untuk pastikan 3 cek baru gagal**

Run: `node tests/_test-praktis.js`
Expected: FAIL tepat pada 3 cek baru; semua cek lama PASS.

- [ ] **Step 3: CSS + panel HTML**

Di CSS setelah baris `tbody tr:hover{background:#f8fbff}` tambahkan:
```css
tbody tr.dipantau td{background:var(--accent2)}
```
Setelah `</details>` panel `#sektorPanel` (sebelum `<details class="adv" id="cfgPanel">`) sisipkan:
```html
  <details class="adv" id="questPanel">
    <summary>Misi Malam Ini <span id="questDate" class="mut"></span></summary>
    <div class="bd" id="questBody"></div>
  </details>
```

- [ ] **Step 4: `renderQuest` + hook + highlight + event**

Tepat sebelum `function renderChips()` sisipkan:
```js
  function muatQuest() {
    try { return JSON.parse(localStorage.getItem("sp_bounty") || "{}"); } catch (e) { return {}; }
  }
  function simpanQuest(q) { try { localStorage.setItem("sp_bounty", JSON.stringify(q)); } catch (e) {} }
  function renderQuest() {
    var board = SP.bounty(S.data, S.scope);
    var hari = hariIni();
    var semua = muatQuest();
    var dip = semua[hari] || {};
    var pulseTgl = (S.scope.pulse && S.scope.pulse.tgl) || "";
    $("questDate").textContent = pulseTgl ? "(data " + pulseTgl + ")" : "";
    var nPant = 0, nLew = 0;
    Object.keys(dip).forEach(function (k) { if (dip[k].status === "dipantau") nPant++; else nLew++; });
    var html = "<p class='mut'>dipantau (" + nPant + ") · dilewat (" + nLew + ")</p>";
    if (!board.length) html += '<p class="mut">Butuh Download Data (SahamScope).</p>';
    html += board.map(function (q) {
      var st = dip[q.kode];
      var stat = st ? (st.status === "dipantau" ? "✅ dipantau" : "➖ lewat: " + (st.alasan || "")) : "";
      return '<div class="kv"><span class="k"><b>' + q.kode + "</b> skor " + q.skor +
        " (" + q.rinci.pulse + "+" + q.rinci.streak + "+" + q.rinci.insider + ")" +
        "<br><span class='mut'>" + (q.jejak.broker ? q.jejak.broker + " " + q.jejak.hit + "/5" : "tanpa streak") +
        (q.jejak.insiderNama ? " · insider " + q.jejak.insiderNama : "") + "</span></span>" +
        '<span class="v">' + stat + " " +
        '<button class="btn pri" data-q="terima" data-kode="' + q.kode + '">Terima</button> ' +
        '<select class="mini-sel" id="alasan-' + q.kode + '"><option>Terlalu jauh</option><option>Sepi</option><option>Tunggu besok</option></select> ' +
        '<button class="btn" data-q="lewat" data-kode="' + q.kode + '">Lewat</button></span></div>' +
        '<div data-kode="' + q.kode + '" style="font-size:11px;color:var(--accent);cursor:pointer">buka drawer →</div>';
    }).join("");
    var lampau = Object.keys(semua).filter(function (d) { return d < hari; }).sort();
    if (lampau.length) {
      var t = lampau[lampau.length - 1];
      html += '<p class="mut" style="margin-top:8px">Arsip ' + t + ": " + Object.keys(semua[t]).map(function (k) {
        return k + " " + (semua[t][k].status === "dipantau" ? "✅" : "➖");
      }).join(" · ") + "</p>";
    }
    $("questBody").innerHTML = html;
  }
  $("questBody").onclick = function (e) {
    var b = e.target.closest("[data-q]");
    if (b) {
      var k = b.getAttribute("data-kode"), semua = muatQuest(), hari = hariIni();
      semua[hari] = semua[hari] || {};
      if (b.getAttribute("data-q") === "terima") semua[hari][k] = { status: "dipantau" };
      else {
        var sel = $("alasan-" + k);
        semua[hari][k] = { status: "lewat", alasan: sel ? sel.value : "" };
      }
      simpanQuest(semua); renderQuest(); render(); return;
    }
    var dw = e.target.closest("[data-kode]");
    if (dw) openDrawer(dw.getAttribute("data-kode"));
  };
```
Catatan emoji ✅➖ di status/arsip: konsisten dengan gaya penanda yang sudah ada di app (⚠, ⏳); bila dianggap bising boleh diganti teks — draf ini final.
Di `rebuild()`, setelah `renderSektor();` tambahkan `renderQuest();`.
Highlight baris di `render()`: ubah `return "<tr data-kode='" + x.kode + "'>" +` menjadi:
```js
      var dipH = (muatQuest()[hariIni()] || {});
      var rcls = (dipH[x.kode] && dipH[x.kode].status === "dipantau") ? ' class="dipantau"' : "";
      return "<tr data-kode='" + x.kode + "'" + rcls + ">" +
```
(Tempatkan 2 baris `dipH/rcls` tepat sebelum `return`, di dalam `d.map(function (x) {`.)

- [ ] **Step 5: Jalankan uji sampai lolos**

Run: `node tests/_test-praktis.js`
Expected: PASS — "Semua uji lulus".

- [ ] **Step 6: Uji manual browser (wajib)**

1. Server + Download Data → panel Misi Malam Ini: 3 kartu + breakdown + badge tanggal pulse.
2. Terima 1 + Lewat 1 (pilih alasan) → baris Terima tersorot; reload → keputusan awet.
3. Arsip: di console devtools jalankan `localStorage.setItem("sp_bounty", JSON.stringify({"2000-01-01":{"BBCA":{"status":"dipantau"}}}))`, reload → baris arsip tampil. (Jangan lupa login ulang normal setelahnya? Tidak perlu — kunci tanggal lampau tidak mengganggu hari ini; hapus bila ingin bersih.)
