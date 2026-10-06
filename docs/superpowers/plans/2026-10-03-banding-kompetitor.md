# Banding Kompetitor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Blok perbandingan kompetitor se-industri di drawer langkah 2.

**Architecture:** `SP.pesaing` murni menghitung grup + median + rank + vonis dari `S.data` + `S.fund.emiten`; `saingBox(x)` render tabel + vonis di drawer.

**Tech Stack:** Vanilla JS satu file HTML, Node smoke test. Tanpa backend.

## Global Constraints

- Satu file HTML offline tanpa CDN — tidak tambah dependensi eksternal.
- Jangan ubah rumus valuasi/fase/skor/aksi/kalibrasi.
- Semua angka via `SP.toNum()`/`nf`; absen → "—".
- Tanpa fetch baru; tanpa kolom tabel utama baru; tanpa rebuild `.exe`.

---

### Task 1: `SP.pesaing` + uji smoke

**Files:**
- Modify: `web/screener-praktis.html` (modul `SP`: sisip setelah `smartMoney`/`bounty`, sebelum `// ---------- valuasi sederhana`; blok `return`)
- Test: `tests/_test-praktis.js` (blok 19 baru)

**Interfaces:**
- Consumes: `SP.toNum`, `SP.nf` (sudah ada)
- Produces: `SP.pesaing(kode, data, fundMap)` → `{industri, sejenis, peers, med, rankPbv, rankRoe, n, vonis}`; dipakai Task 2.

- [ ] **Step 1: Tambah blok uji yang gagal (blok 19)**

Di `tests/_test-praktis.js`, tepat sebelum `console.log(gagal`, sisipkan:
```js
// 19) banding kompetitor
{
  const fd = {
    A: { klasifikasi: { industri: ["Bank"] }, sejenis: ["B", "C"] },
    B: { klasifikasi: { industri: ["Bank"] }, sejenis: [] },
    C: { klasifikasi: { industri: ["Bank"] }, sejenis: [] },
    D: { klasifikasi: { industri: ["Energi"] }, sejenis: [] }
  };
  const dd = [
    { kode: "A", r: { harga: "1000" }, val: { per: 10, pbv: 1, roe: 20, intrinsic: 1200, mos: 15 }, fase: "Akumulasi", skor: 70 },
    { kode: "B", r: { harga: "2000" }, val: { per: 20, pbv: 2, roe: 10, intrinsic: 1800, mos: -5 }, fase: "Markup", skor: 60 },
    { kode: "C", r: { harga: "3000" }, val: { per: 30, pbv: 3, roe: 5, intrinsic: 2500, mos: 0 }, fase: "Netral", skor: 50 },
    { kode: "D", r: { harga: "4000" }, val: { per: 5, pbv: 0.5, roe: 30, intrinsic: 5000, mos: 25 }, fase: "Netral", skor: 55 }
  ];
  const p = SP.pesaing("A", dd, fd);
  cek("pesaing: 2 peer se-industri (D tersingkir)", p.peers.length === 2 && p.peers[0].kode === "B", JSON.stringify(p.peers.map(q => q.kode)));
  cek("pesaing: industri Bank", p.industri === "Bank");
  cek("pesaing: median pbv 2 roe 10", p.med.pbv === 2 && p.med.roe === 10, JSON.stringify(p.med));
  cek("pesaing: rank pbv 1 roe 1", p.rankPbv === 1 && p.rankRoe === 1);
  cek("pesaing: vonis menyebut termurah + tertinggi", p.vonis.includes("termurah") && p.vonis.includes("tertinggi"), p.vonis);
  cek("pesaing: tanpa fund aman", SP.pesaing("Z", dd, {}).peers.length === 0);
}
```

- [ ] **Step 2: Jalankan uji untuk pastikan gagal**

Run: `node tests/_test-praktis.js`
Expected: error `TypeError: SP.pesaing is not a function`.

- [ ] **Step 3: Implementasi minimal**

Sisipkan setelah akhir fungsi `bounty` (baris `}` tepat sebelum `// ---------- valuasi sederhana`):
```js
  // ---------- banding kompetitor se-industri (display-only) ----------
  function medNum(arr) {
    var v = arr.filter(function (x) { return isFinite(x); }).sort(function (a, b) { return a - b; });
    if (!v.length) return null;
    return v.length % 2 ? v[(v.length - 1) / 2] : (v[v.length / 2 - 1] + v[v.length / 2]) / 2;
  }
  function pesaing(kode, data, fundMap) {
    fundMap = fundMap || {};
    var f = fundMap[kode] || {};
    var industri = (((f.klasifikasi || {}).industri) || [])[0] || "";
    var sej = f.sejenis || [];
    var grup = (data || []).filter(function (d) {
      if (d.kode === kode) return true;
      if (sej.indexOf(d.kode) >= 0) return true;
      var pf = fundMap[d.kode] || {};
      return industri && (((pf.klasifikasi || {}).industri) || [])[0] === industri;
    });
    var diri = grup.filter(function (d) { return d.kode === kode; })[0];
    var peers = grup.filter(function (d) { return d.kode !== kode; });
    peers.sort(function (a, b) {
      var ia = sej.indexOf(a.kode), ib = sej.indexOf(b.kode);
      if (ia < 0) ia = 999; if (ib < 0) ib = 999;
      return ia - ib || (a.kode < b.kode ? -1 : (a.kode > b.kode ? 1 : 0));
    });
    peers = peers.slice(0, 7);
    if (!diri) return { industri: industri, sejenis: sej, peers: [], med: {}, rankPbv: null, rankRoe: null, n: 0, vonis: "" };
    var semua = [diri].concat(peers);
    function kolom(fn) { return semua.map(fn).filter(function (x) { return x != null && isFinite(x); }); }
    var med = { per: medNum(kolom(function (d) { return toNum(d.val.per); })), pbv: medNum(kolom(function (d) { return toNum(d.val.pbv); })), roe: medNum(kolom(function (d) { return toNum(d.val.roe); })), mos: medNum(kolom(function (d) { return d.val.mos == null ? NaN : toNum(d.val.mos); })) };
    function rank(get, kecil) {
      var arr = semua.map(function (d) { return { k: d.kode, v: get(d); }; }).filter(function (o) { return isFinite(o.v); });
      arr.sort(function (a, b) { return kecil ? a.v - b.v : b.v - a.v; });
      for (var i = 0; i < arr.length; i++) if (arr[i].k === kode) return i + 1;
      return null;
    }
    var rP = rank(function (d) { return toNum(d.val.pbv) > 0 ? toNum(d.val.pbv) : NaN; }, true);
    var rR = rank(function (d) { return toNum(d.val.roe) || 0; }, false);
    var n = semua.length;
    function kata(rk, satu, tengah) {
      if (rk == null) return "tak terbandingkan";
      if (rk === 1) return satu;
      if (rk === n && n > 1) return tengah === "murah" ? "termahal" : "terendah";
      return "urutan ke-" + rk + " dari " + n;
    }
    var siapa = industri || "saham sejenis";
    var vonis = n > 1
      ? "Di antara " + n + " " + siapa + " yang termuat (" + semua.map(function (d) { return d.kode; }).join(", ") + "), " + kode + " PBV-nya " + kata(rP, "termurah", "murah") + ", ROE " + kata(rR, "tertinggi", "roe") + "."
      : "";
    return { industri: industri, sejenis: sej, peers: peers, med: med, rankPbv: rP, rankRoe: rR, n: n, vonis: vonis };
  }
```
(Catatan: sintaks `v: get(d);` di atas SALAH ketik — tulis yang benar `v: get(d)` tanpa titik-koma. Hati-hati saat menyalin.)
Di blok `return` modul SP tambahkan `pesaing: pesaing,` (setelah `bounty: bounty,`).

- [ ] **Step 4: Jalankan uji sampai lolos**

Run: `node tests/_test-praktis.js`
Expected: PASS — "Semua uji lulus".

### Task 2: Blok drawer + wiring

**Files:**
- Modify: `web/screener-praktis.html` (`saingBox`, panggil di langkah 2 setelah `fundBox`, 2 cek string)
- Test: `tests/_test-praktis.js` + manual browser

**Interfaces:**
- Consumes: `SP.pesaing` dari Task 1; `S.data`, `S.fund.emiten`; `row`, `nf`, `faseBadge`
- Produces: UI selesai.

- [ ] **Step 1: Tambah 2 cek string (gagal dulu)**

Blok 7 tambah:
```js
  cek("blok saing ada", html.includes("Banding kompetitor") && html.includes("SP.pesaing"));
  cek("helper saing ada", html.includes("saingBox"));
```

- [ ] **Step 2-4: Implementasi**

Tepat sebelum `function smBox(x) {` sisipkan:
```js
  function saingBox(x) {
    var fm = (S.fund.emiten || {});
    var p = SP.pesaing(x.kode, S.data, fm);
    if (!p.n) return '<div class="mut" style="margin-top:6px">Belum ada data pembanding — klik Download Data.</div>';
    var head = '<div style="margin-top:8px"><b>Banding kompetitor</b><div class="mut">Industri: <b>' + (p.industri || "—") + "</b> · sejenis: " + (p.sejenis.length ? p.sejenis.join(", ") : "—") + "</div>";
    function baris(d, tebal) {
      function sel(v, des) { return (v == null || v === "" || !isFinite(v)) ? "—" : nf(v, des == null ? 1 : des); }
      var b = tebal ? ' style="font-weight:700"' : "";
      return "<tr" + b + "><td>" + d.kode + "</td>" +
        '<td class="n">' + nf(SP.toNum(d.r.harga), 0) + "</td>" +
        '<td class="n">' + sel(toNum(d.val.per)) + "</td>" +
        '<td class="n">' + sel(toNum(d.val.pbv)) + "</td>" +
        '<td class="n">' + sel(toNum(d.val.roe)) + "</td>" +
        '<td class="n">' + (d.val.intrinsic > 0 ? nf(d.val.intrinsic, 0) : "—") + "</td>" +
        '<td class="n">' + (d.val.mos == null ? "—" : sel(toNum(d.val.mos), 0) + "%") + "</td>" +
        "<td>" + faseBadge(d.fase) + "</td>" +
        '<td class="n">' + d.skor + "</td></tr>";
    }
    function barisMed(m) {
      function sel(v, des) { return (v == null || !isFinite(v)) ? "—" : nf(v, des == null ? 1 : des); }
      return '<tr><td class="mut">Median</td><td class="n">—</td>' +
        '<td class="n">' + sel(m.per) + "</td>" +
        '<td class="n">' + sel(m.pbv) + "</td>" +
        '<td class="n">' + sel(m.roe) + "</td>" +
        '<td class="n">—</td><td class="n">' + sel(m.mos, 0) + (m.mos != null && isFinite(m.mos) ? "%" : "") + "</td>" +
        '<td class="mut">—</td><td class="n">—</td></tr>';
    }
    var semua = [x].concat(p.peers);
    return head + '<table style="margin-top:4px"><thead><tr><th>Kode</th><th>Harga</th><th>PER</th><th>PBV</th><th>ROE</th><th>FV</th><th>MOS</th><th>Fase</th><th>Skor</th></tr></thead><tbody>' +
      semua.map(function (d) { return baris(d, d.kode === x.kode); }).join("") + barisMed(p.med) + "</tbody></table>" +
      (p.vonis ? '<div class="note" style="margin-top:6px">' + p.vonis + "</div>" : "") + "</div>";
  }
```
Di langkah 2 drawer, setelah `fundBox(x) +` tambahkan (sebelum `"</div>"` penutup s2 — anchor: baris `fundBox(x) + "</div>";`):
`saingBox(x) +` — tepatnya ubah `fundBox(x) + "</div>";` menjadi `fundBox(x) + saingBox(x) + "</div>";`
(Hati-hati: pastikan anchor unik — cek kemunculan `fundBox(x)`; bila >1, gunakan konteks baris s2.)

- [ ] **Step 5-6: Uji**

Run smoke → PASS. Manual: Download → drawer BBNI menampilkan BBCA/BMRI/BBRI + median + vonis; tanpa fund → fallback.
