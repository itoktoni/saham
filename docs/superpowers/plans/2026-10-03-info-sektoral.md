# Info Sektoral Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tampilkan sektor terkuat + narasi otomatis di strip makro dan panel rotasi sektoral.

**Architecture:** Agregasi murni di frontend dalam `web/screener-praktis.html`; `SP.agregatSektor` + `SP.narasiSektor` diisolasi di modul SP agar bisa diuji via smoke test; UI reuse komponen `.macro`/`.adv` yang ada.

**Tech Stack:** Vanilla JS satu file HTML (tanpa CDN), Node smoke test `tests/_test-praktis.js`, Python backend tidak disentuh.

## Global Constraints

- Satu file offline tanpa CDN — tidak tambah dependensi eksternal.
- Jangan ubah `detectFase`, `valuasi`, `skor`, `aksi`, `build`, `matchMetode`, kalibrasi horizon 3 bulan.
- Semua akses angka via `SP.toNum()` agar CSV kosong tidak menghasilkan NaN.
- Warna naik = merah (`pos`) turun = hijau (`neg`); narasi tanpa klaim sebab di luar angka; bukan nasihat investasi.
- Ekspor CSV tidak diubah.

---

### Task 1: Tambah uji gagal untuk agregat + narasi sektoral

**Files:**
- Modify: `tests/_test-praktis.js` (tambah blok 9 setelah blok 8, sebelum `console.log(gagal`)
- Test: `tests/_test-praktis.js`

**Interfaces:**
- Consumes: `SP.toNum`, `SP.nf` (sudah ada di `web/screener-praktis.html`)
- Produces: kontrak yang harus dipenuhi Task 2 — `SP.agregatSektor(data)` → array `{sektor, avg1m, hijau, total, pendorong: [{kode, ret}]}` urut `avg1m` menurun; `SP.narasiSektor(ag, totalEmiten)` → string. Bentuk input `x` = `{kode, sektor, r: {ret20}}` (subset record `SP.build()`).

- [ ] **Step 1: Tambah blok uji yang gagal**

Di `tests/_test-praktis.js`, tepat sebelum baris `console.log(gagal`, sisipkan blok ini persis:

```js
// 9) agregat sektoral + narasi
{
  const rows9 = [
    { kode: "ADRO", sektor: "Energi", r: { ret20: "5" } },
    { kode: "PTBA", sektor: "Energi", r: { ret20: "1" } },
    { kode: "BBCA", sektor: "Keuangan", r: { ret20: "-2" } },
    { kode: "NON", sektor: "", r: {} }
  ];
  const ag = SP.agregatSektor(rows9);
  cek("agregat: 3 grup (Energi, Keuangan, Lainnya)", ag.length === 3, JSON.stringify(ag.map(g => g.sektor)));
  cek("agregat: Energi teratas avg +3,0%", ag[0].sektor === "Energi" && ag[0].avg1m === 3, JSON.stringify(ag[0]));
  cek("agregat: breadth Energi 2/2", ag[0].hijau === 2 && ag[0].total === 2);
  cek("agregat: pendorong ADRO dulu", ag[0].pendorong[0].kode === "ADRO" && ag[0].pendorong.length === 2);
  const nar = SP.narasiSektor(ag, 4);
  cek("narasi menyebut sektor + pendorong + sampel kecil", nar.includes("Energi") && nar.includes("ADRO") && nar.includes("sampel kecil"), nar);
  cek("narasi kosong bila tanpa return", SP.narasiSektor(SP.agregatSektor([{ kode: "X", sektor: "A", r: {} }]), 1).includes("Belum ada data"));
}
```

- [ ] **Step 2: Jalankan uji untuk pastikan gagal**

Run: `node tests/_test-praktis.js`
Expected: error `TypeError: SP.agregatSektor is not a function` (fungsi belum ada); ini sinyal gagal yang diharapkan.

- [ ] **Step 3: Lewati commit (bukan git repo)**

Repo ini bukan git repository (`git status` → "not a git repository"), jadi langkah commit dilewati. Jangan inisialisasi repo baru.

### Task 2: Implementasi SP.agregatSektor + SP.narasiSektor

**Files:**
- Modify: `web/screener-praktis.html` (modul `SP`: sisip setelah fungsi `matchMetode`, sebelum `// ---------- valuasi sederhana`; dan blok `return` modul SP)
- Test: `tests/_test-praktis.js`

**Interfaces:**
- Consumes: `SP.toNum`, `SP.nf` dari modul yang sama
- Produces: `SP.agregatSektor(data)`, `SP.narasiSektor(ag, total)` → dipakai Task 3 di `renderMacro()` dan `renderSektor()`

- [ ] **Step 1: Tambah dua fungsi murni setelah `matchMetode`**

Temukan akhir `matchMetode` (baris `return true;` + `}` tepat sebelum `// ---------- valuasi sederhana`). Sisipkan persis blok ini di antaranya:

```js
  // ---------- agregat sektoral (rotasi sektor, dari data yang dimuat) ----------
  function agregatSektor(data) {
    var kumpul = {};
    (data || []).forEach(function (x) {
      var s = ((x && x.sektor) || "").trim() || "Lainnya";
      var ret = toNum(x.r && x.r.ret20);
      if (!kumpul[s]) kumpul[s] = { arr: [], hijau: 0, pend: [] };
      kumpul[s].arr.push(ret);
      if (ret > 0) kumpul[s].hijau++;
      kumpul[s].pend.push({ kode: x.kode, ret: ret });
    });
    return Object.keys(kumpul).map(function (s) {
      var g = kumpul[s];
      var avg = g.arr.reduce(function (a, b) { return a + b; }, 0) / g.arr.length;
      g.pend.sort(function (a, b) { return b.ret - a.ret; });
      return { sektor: s, avg1m: Math.round(avg * 10) / 10, hijau: g.hijau, total: g.arr.length, pendorong: g.pend.slice(0, 2) };
    }).sort(function (a, b) { return b.avg1m - a.avg1m; });
  }

  function narasiSektor(ag, total) {
    if (!ag || !ag.length) return "Belum ada data return sektoral pada muatan ini.";
    var adaRet = ag.some(function (g) { return g.pendorong.some(function (p) { return p.ret !== 0; }); });
    if (!adaRet) return "Belum ada data return sektoral pada muatan ini.";
    var t = ag[0];
    var pend = t.pendorong.map(function (p) { return p.kode + " " + (p.ret > 0 ? "+" : "") + nf(p.ret, 1) + "%"; }).join(" dan ");
    var s = t.sektor + " memimpin " + (t.avg1m > 0 ? "+" : "") + nf(t.avg1m, 1) + "% sebulan (" + t.hijau + "/" + t.total + " saham hijau), didorong " + pend + ".";
    if ((total || 0) < 15) s += " (sampel kecil \u2014 paling bermakna setelah Scan Seluruh Pasar)";
    return s;
  }
```

- [ ] **Step 2: Ekspor dari modul SP**

Temukan blok `return {` modul SP (berisi `METODE: METODE, matchMetode: matchMetode,`). Ubah baris itu menjadi:

```js
    METODE: METODE, matchMetode: matchMetode, agregatSektor: agregatSektor, narasiSektor: narasiSektor,
```

Satu baris berubah, sisa return jangan disentuh.

- [ ] **Step 3: Jalankan uji sampai lolos**

Run: `node tests/_test-praktis.js`
Expected: PASS — "Semua uji lulus", termasuk 6 cek baru blok 9.

- [ ] **Step 4: Cek sintaks HTML**

Run: `node tests/_test-praktis.js`
Expected: baris pertama "OK sintaks blok <script> HTML valid" (uji ini sudah mencakup `node --check` seluruh blok script).

### Task 3: Panel sektoral + item makro + integrasi render

**Files:**
- Modify: `web/screener-praktis.html` (HTML panel setelah `</div>` panel tabel; `renderMacro()`; fungsi baru `renderSektor()`; `rebuild()`)
- Test: `tests/_test-praktis.js` (3 cek string HTML) + uji manual browser

**Interfaces:**
- Consumes: `SP.agregatSektor`, `SP.narasiSektor` dari Task 2; pola `nf`, `$`, `renderHorizon` yang sudah ada
- Produces: UI selesai — tidak ada konsumen lanjutan

- [ ] **Step 1: Tambah 3 cek string HTML ke uji**

Di `tests/_test-praktis.js` blok 7, tepat setelah baris `cek("pilihan metode dipersist"...`, tambahkan 3 baris ini persis:

```js
  cek("panel sektoral ada", html.includes('id="sektorPanel"') && html.includes("Rotasi sektoral"));
  cek("renderSektor dipanggil di rebuild", html.includes("renderSektor"));
  cek("makro memuat item Sektor", html.includes("Sektor:</span>"));
```

- [ ] **Step 2: Jalankan uji untuk pastikan 3 cek baru gagal**

Run: `node tests/_test-praktis.js`
Expected: FAIL tepat pada 3 cek baru di atas; semua cek lama PASS.

- [ ] **Step 3: Tambah panel HTML setelah panel tabel**

Temukan potongan ini (akhir panel tabel, sebelum `<details class="adv" id="cfgPanel">`):

```html
    <div class="empty" id="empty">
      <h3>Belum ada data</h3>
      <p>Klik <b>Download Data</b> untuk mengambil data terbaru secara otomatis<br>(kepemilikan KSEI + harga &amp; fundamental Yahoo). Butuh aplikasi sedang berjalan.</p>
      <p>Sudah punya berkasnya? Klik <b>Impor Berkas</b>. Atau <b>Muat Contoh</b> untuk melihat tampilannya.</p>
    </div>
  </div>

  <details class="adv" id="cfgPanel">
```

Sisipkan panel baru di antara `</div>` dan `<details class="adv" id="cfgPanel">` sehingga menjadi:

```html
    <div class="empty" id="empty">
      <h3>Belum ada data</h3>
      <p>Klik <b>Download Data</b> untuk mengambil data terbaru secara otomatis<br>(kepemilikan KSEI + harga &amp; fundamental Yahoo). Butuh aplikasi sedang berjalan.</p>
      <p>Sudah punya berkasnya? Klik <b>Impor Berkas</b>. Atau <b>Muat Contoh</b> untuk melihat tampilannya.</p>
    </div>
  </div>

  <details class="adv" id="sektorPanel">
    <summary>Rotasi sektoral (dari data yang dimuat)</summary>
    <div class="bd">
      <p id="sektorNarasi" style="margin:2px 0 8px"></p>
      <table><thead><tr><th>Sektor</th><th>Rata-rata 1bln</th><th>Hijau</th><th>Pendorong</th></tr></thead><tbody id="sektorBody"></tbody></table>
    </div>
  </details>

  <details class="adv" id="cfgPanel">
```

- [ ] **Step 4: Tambah item Sektor di `renderMacro()`**

Temukan fungsi `renderMacro()`:

```js
  function renderMacro() {
    var p = S.pasar;
    if (!p || !p.ihsg) { $("macro").hidden = true; return; }
    var ih = p.ihsg;
    var liq = p.likuiditas && (p.likuiditas.status || p.likuiditas.label);
    var liqTxt = liq ? liq : (p.likuiditas ? "—" : "belum diambil");
    $("macro").innerHTML =
      '<div class="m"><span>Kuadran:</span><b style="text-transform:capitalize">' + (ih.saran_kuadran || "-") + "</b></div>" +
      '<div class="m"><span>IHSG:</span><b>' + nf(ih.tutup, 0) + "</b> <span>(" + pct(ih.r3, 2) + " 3bln, " + nf(ih.jarak_puncak, 1) + "% dari puncak)</span></div>" +
      '<div class="m"><span>Likuiditas:</span><b>' + liqTxt + "</b></div>" +
      '<div class="m"><span>BI Rate:</span><b>' + (p.suku_bunga_bi != null ? nf(p.suku_bunga_bi, 2) + "%" : "-") + "</b></div>";
    $("macro").hidden = false;
  }
```

Ganti seluruh fungsi dengan:

```js
  function renderMacro() {
    var p = S.pasar;
    var sekItem = "";
    var ag0 = SP.agregatSektor(S.data);
    if (ag0.length && S.data.length) {
      var t0 = ag0[0];
      sekItem = '<div class="m"><span>Sektor:</span><b>' + t0.sektor + " " + (t0.avg1m > 0 ? "+" : "") + nf(t0.avg1m, 1) + "%</b> <span>(" + t0.hijau + "/" + t0.total + " hijau)</span></div>";
    }
    if (!p || !p.ihsg) {
      if (sekItem) { $("macro").innerHTML = sekItem; $("macro").hidden = false; }
      else { $("macro").hidden = true; }
      return;
    }
    var ih = p.ihsg;
    var liq = p.likuiditas && (p.likuiditas.status || p.likuiditas.label);
    var liqTxt = liq ? liq : (p.likuiditas ? "—" : "belum diambil");
    $("macro").innerHTML =
      '<div class="m"><span>Kuadran:</span><b style="text-transform:capitalize">' + (ih.saran_kuadran || "-") + "</b></div>" +
      '<div class="m"><span>IHSG:</span><b>' + nf(ih.tutup, 0) + "</b> <span>(" + pct(ih.r3, 2) + " 3bln, " + nf(ih.jarak_puncak, 1) + "% dari puncak)</span></div>" +
      '<div class="m"><span>Likuiditas:</span><b>' + liqTxt + "</b></div>" +
      '<div class="m"><span>BI Rate:</span><b>' + (p.suku_bunga_bi != null ? nf(p.suku_bunga_bi, 2) + "%" : "-") + "</b></div>" +
      sekItem;
    $("macro").hidden = false;
  }
```

Perilaku lama dipertahankan: tanpa data sama sekali makro tetap hidden; tanpa regime tapi ada data saham, makro tampil berisi item Sektor saja.

- [ ] **Step 5: Tambah `renderSektor()` dan panggil di `rebuild()`**

Temukan:

```js
  function rebuild() {
    S.data = SP.build(S._csvRows || [], S.ksei);
    updateUmur();
    render();
    renderHorizon();
    checkAlerts();
  }
```

Ganti menjadi:

```js
  function renderSektor() {
    var ag = SP.agregatSektor(S.data);
    $("sektorNarasi").textContent = SP.narasiSektor(ag, S.data.length);
    $("sektorBody").innerHTML = ag.map(function (g) {
      var pend = g.pendorong.map(function (p) { return p.kode + " " + (p.ret > 0 ? "+" : "") + nf(p.ret, 1) + "%"; }).join(" · ") || "—";
      var cls = g.avg1m > 0 ? "pos" : (g.avg1m < 0 ? "neg" : "mut");
      return "<tr><td>" + g.sektor + "</td>" +
        '<td class="n ' + cls + '">' + (g.avg1m > 0 ? "+" : "") + nf(g.avg1m, 1) + "%</td>" +
        '<td class="n">' + g.hijau + "/" + g.total + "</td><td>" + pend + "</td></tr>";
    }).join("") || '<tr><td colspan="4" class="mut" style="text-align:center">—</td></tr>';
  }

  function rebuild() {
    S.data = SP.build(S._csvRows || [], S.ksei);
    updateUmur();
    render();
    renderHorizon();
    renderSektor();
    checkAlerts();
  }
```

- [ ] **Step 6: Jalankan uji sampai lolos**

Run: `node tests/_test-praktis.js`
Expected: PASS — "Semua uji lulus".

- [ ] **Step 7: Uji manual browser (wajib sebelum selesai)**

1. Jalankan via `Screener Saham.exe`, klik **Muat Contoh**.
2. Strip makro tampil berisi item Sektor (tanpa regime). Panel "Rotasi sektoral" menampilkan narasi "Belum ada data return..." (data contoh tanpa ret20) + tabel grup sektor avg 0,0%.
3. Klik **Scan Seluruh Pasar**: makro + panel menampilkan sektor terkuat nyata + pendorongnya; tidak ada error console.
4. Buka panel dengan data kosong (sebelum muat apa pun): narasi fallback + baris "—".
