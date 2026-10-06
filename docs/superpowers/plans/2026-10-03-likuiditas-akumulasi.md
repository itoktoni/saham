# Likuiditas + Bar Akumulasi Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tambah kolom Likuiditas otomatis dan 30 bar akumulasi harian di drawer tiap saham.

**Architecture:** `scripts/fetch-data-idx.py` menempelkan `bars_30` ke record (CSV writer hanya memakai kunci CSV_HEADER sehingga format CSV lama tidak berubah); `SP.barAkumulasi` murni di frontend menghitung status harian; kolom + drawer render hasilnya.

**Tech Stack:** Python stdlib (fetch-data-idx.py), vanilla JS satu file HTML, Node smoke test `tests/_test-praktis.js`. `app/app-screener.py` tidak diubah (meneruskan semua field kecuali `_catatan`).

## Global Constraints

- Satu file HTML offline tanpa CDN — tidak tambah dependensi eksternal.
- Jangan ubah `detectFase`, `valuasi`, `skor`, `aksi`, `build`, `matchMetode`, `agregatSektor`, kalibrasi horizon 3 bulan.
- Semua akses angka di JS via `SP.toNum()` agar CSV kosong tidak menghasilkan NaN.
- Ambang likuid fixed Rp5.000.000.000/hari (preseden `minNilai 5e9`).
- Warna blok akumulasi: hijau `#17795e` = hari serapan, merah `#c62828` = hari sebaran, abu `#c9cfd6` = sepi; selalu dengan legenda eksplisit.
- Narasi jujur: heuristik harga×volume, BUKAN data broker; tanpa klaim sebab.
- Ekspor CSV tidak diubah; format CSV 31+ kolom lama tetap bisa diimpor.

---

### Task 1: Backend `bars_30` di `build_record`

**Files:**
- Modify: `scripts/fetch-data-idx.py` (fungsi `build_record`, setelah baris `"s_resistance"`)
- Test: cek offline via `python -c` (tanpa network; `args` tidak dipakai di dalam `build_record`)

**Interfaces:**
- Consumes: `ch` = `{"close": [...], "volume": [...]}` dari `fetch_chart` (sudah ada)
- Produces: `rec["bars_30"]` = array `[tutup_int, volume_int]` (maks 30, urutan lama→baru); dipakai Task 3 via JSON. CSV writer mengabaikannya (hanya kunci CSV_HEADER).

- [ ] **Step 1: Tulis cek gagal**

Run:
```bash
python -c "import importlib.util; s=importlib.util.spec_from_file_location('f','scripts/fetch-data-idx.py'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); ch={'close':[100.0+i for i in range(40)],'high':[101.0]*40,'low':[99.0]*40,'volume':[1000.0]*40}; r=m.build_record('TST',{'nama':'T','sektor':'Energi'},None,ch,None); assert r['bars_30'][0]==[110,1000] and len(r['bars_30'])==30, r.get('bars_30'); print('bars_30 OK')"
```
Expected: FAIL dengan `KeyError: 'bars_30'`.

- [ ] **Step 2: Implementasi minimal**

Di `scripts/fetch-data-idx.py`, tepat sebelum `sw = hitung_swing(ch)` (baris ~539) sisipkan:
```python
    bars_30 = []
    if ch and ch.get("close") and ch.get("volume"):
        n = min(30, len(ch["close"]), len(ch["volume"]))
        bars_30 = [[int(round(ch["close"][-n + i])), int(ch["volume"][-n + i] or 0)]
                   for i in range(n)]
```
Dan di dict return, setelah baris `"s_resistance": sw["s_resistance"],` tambahkan:
```python
        "bars_30": bars_30,
```

- [ ] **Step 3: Jalankan cek sampai lolos**

Run: perintah `python -c` yang sama seperti Step 1 (dengan `[110,1000]`).
Expected: mencetak `bars_30 OK`.

- [ ] **Step 4: Pastikan CSV tidak berubah dan app meneruskan field**

Run:
```bash
python -c "import importlib.util; s=importlib.util.spec_from_file_location('f','scripts/fetch-data-idx.py'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); assert 'bars_30' not in m.CSV_HEADER; print('CSV aman')"
```
Dan:
```bash
Select-String -LiteralPath "app/app-screener.py" -Pattern 'rec\.pop' -SimpleMatch
```
Expected: `CSV aman`, dan satu-satunya `rec.pop` adalah `rec.pop("_catatan", None)` (artinya `bars_30` diteruskan ke JSON).

### Task 2: `SP.barAkumulasi` + uji smoke

**Files:**
- Modify: `web/screener-praktis.html` (modul `SP`: sisip setelah `narasiSektor`, sebelum `// ---------- skor tunggal`; dan blok `return` modul SP)
- Test: `tests/_test-praktis.js` (blok 10 baru)

**Interfaces:**
- Consumes: `SP.toNum` (sudah ada)
- Produces: `SP.barAkumulasi(bars)` → array `{h: 0–100, c: "H"|"M"|"A"}`; dipakai Task 3 di drawer. Aturan: dasar = rata-rata volume; hari i≥1 hijau bila tutup naik dan vol ≥ rata-rata; merah bila tutup turun dan vol ≥ rata-rata; selainnya abu; hari pertama selalu abu; max vol 0 → semua tinggi 0.

- [ ] **Step 1: Tambah blok uji yang gagal (blok 10)**

Di `tests/_test-praktis.js`, tepat sebelum `console.log(gagal`, sisipkan:
```js
// 10) bar akumulasi harian
{
  const up = [[100, 500], [101, 2000], [102, 2000], [103, 100]];
  const bu = SP.barAkumulasi(up);
  cek("barAkumulasi: 4 hasil, hari pertama abu", bu.length === 4 && bu[0].c === "A", JSON.stringify(bu));
  cek("barAkumulasi: naik+vol tinggi = hijau", bu[1].c === "H" && bu[2].c === "H");
  cek("barAkumulasi: naik+vol kecil = abu", bu[3].c === "A");
  const dn = [[100, 500], [99, 2000], [98, 100]];
  const bd = SP.barAkumulasi(dn);
  cek("barAkumulasi: turun+vol tinggi = merah", bd[1].c === "M" && bd[2].c === "A");
  cek("barAkumulasi: kosong aman", Array.isArray(SP.barAkumulasi(undefined)) && SP.barAkumulasi(undefined).length === 0);
}
```

- [ ] **Step 2: Jalankan uji untuk pastikan gagal**

Run: `node tests/_test-praktis.js`
Expected: error `TypeError: SP.barAkumulasi is not a function`.

- [ ] **Step 3: Implementasi minimal**

Sisipkan setelah akhir fungsi `narasiSektor` (baris `return s;` + `}` tepat sebelum `// ---------- skor tunggal`):
```js
  // ---------- bar akumulasi harian (heuristik harga x volume) ----------
  function barAkumulasi(bars) {
    bars = bars || [];
    if (!bars.length) return [];
    var vols = bars.map(function (b) { return toNum(b[1]); });
    var avg = vols.reduce(function (a, b) { return a + b; }, 0) / vols.length;
    var mx = Math.max.apply(null, vols.concat([0]));
    return bars.map(function (b, i) {
      var tutup = toNum(b[0]), vol = toNum(b[1]);
      var c = "A";
      if (i > 0) {
        var prev = toNum(bars[i - 1][0]);
        if (vol >= avg && tutup > prev) c = "H";
        else if (vol >= avg && tutup < prev) c = "M";
      }
      return { h: mx > 0 ? Math.round(vol / mx * 100) : 0, c: c };
    });
  }
```
Dan di blok `return` modul SP ubah baris ekspor menjadi:
```js
    METODE: METODE, matchMetode: matchMetode, agregatSektor: agregatSektor, narasiSektor: narasiSektor, barAkumulasi: barAkumulasi,
```

- [ ] **Step 4: Jalankan uji sampai lolos**

Run: `node tests/_test-praktis.js`
Expected: PASS — "Semua uji lulus", termasuk 5 cek baru blok 10.

### Task 3: Kolom Likuid + blok drawer + integrasi

**Files:**
- Modify: `web/screener-praktis.html` (COLS + render body + drawer `s3`; tambah 3 cek string di `tests/_test-praktis.js`)
- Test: `tests/_test-praktis.js` + uji manual browser

**Interfaces:**
- Consumes: `SP.barAkumulasi` dari Task 2; `x.r.nilai_harian`, `x.r.bars_30` dari data; pola `nf`, `row()`, badge yang sudah ada
- Produces: UI selesai — tidak ada konsumen lanjutan

- [ ] **Step 1: Tambah 3 cek string HTML ke uji**

Di `tests/_test-praktis.js` blok 7, setelah baris `cek("makro memuat item Sektor"...`, tambahkan:
```js
  cek("kolom Likuid ada", html.includes('t: "Likuid"'));
  cek("blok akumulasi drawer ada", html.includes("Akumulasi 30 hari") && html.includes("barAkumulasi"));
  cek("ambang likuid 5M", html.includes("5000000000"));
```

- [ ] **Step 2: Jalankan uji untuk pastikan 3 cek baru gagal**

Run: `node tests/_test-praktis.js`
Expected: FAIL tepat pada 3 cek baru; semua cek lama PASS.

- [ ] **Step 3: Tambah kolom Likuid**

Di `COLS`, setelah baris `{ k: "aksi", t: "Aksi", n: false }` tambahkan koma dan baris baru sehingga menjadi:
```js
    { k: "aksi", t: "Aksi", n: false },
    { k: "likuid", t: "Likuid", n: false, get: function (d) { return SP.toNum(d.r.nilai_harian); } }
```
Di render body, setelah baris `"<td>" + aksiBadge(x.aksi) + "</td>" +` tambahkan:
```js
        "<td>" + likuidBadge(x) + "</td>" +
```
Dan tepat sebelum `function deltaCls` tambahkan fungsi:
```js
  function likuidBadge(x) {
    var v = SP.toNum(x.r.nilai_harian);
    if (!(v > 0)) return '<span class="mut">—</span>';
    var ok = v >= 5000000000;
    return '<span class="aksi ' + (ok ? "a-beli" : "a-pantau") + '" title="Rp' + nf(v / 1e9, 1) + 'M/hari">' + (ok ? "Likuid" : "Sepi") + "</span>";
  }
```
Reuse class badge aksi (`a-beli` hijau / `a-pantau` kuning) agar tanpa CSS baru.

- [ ] **Step 4: Tambah baris drawer + blok 30 bar di langkah 3**

Di `s3`, setelah baris `row("Volume vs rata-rata 20h", ...)` tambahkan:
```js
      row("Nilai transaksi harian", SP.toNum(r.nilai_harian) > 0 ? "Rp" + nf(SP.toNum(r.nilai_harian) / 1e9, 1) + "M" : "—") +
```
Dan setelah baris `row("Resistance 20h", nf(SP.toNum(r.s_resistance), 0)) +` tambahkan:
```js
      akumulasiBox(r) +
```
Tepat sebelum `function alasanFase` tambahkan fungsi:
```js
  function akumulasiBox(r) {
    var bars = SP.barAkumulasi(r.bars_30);
    if (!bars.length) return '<div class="mut" style="margin-top:6px">Bar harian hanya tersedia dari Download Data (butuh riwayat Yahoo).</div>';
    var W = { H: "#17795e", M: "#c62828", A: "#c9cfd6" };
    var html = bars.map(function (b) {
      return '<span title="' + b.c + '" style="display:inline-block;width:8px;height:' + Math.max(3, b.h * 0.4) + 'px;background:' + W[b.c] + ';border-radius:2px;margin-right:2px;vertical-align:bottom"></span>';
    }).join("");
    return '<div style="margin-top:8px"><b>Akumulasi 30 hari</b><div style="margin-top:4px">' + html + '</div>' +
      '<div class="mut" style="margin-top:2px">hijau = hari serapan · merah = hari sebaran · abu = sepi (heuristik harga×volume — bukan data broker).</div></div>';
  }
```

- [ ] **Step 5: Jalankan uji sampai lolos**

Run: `node tests/_test-praktis.js`
Expected: PASS — "Semua uji lulus".

- [ ] **Step 6: Uji manual browser (wajib sebelum selesai)**

1. Jalankan via `Screener Saham.exe`, klik **Download Data** (watchlist kecil agar cepat).
2. Kolom Likuid terisi (Likuid/Sepi/—) di kedua mode; tooltip menampilkan RpM/hari.
3. Buka drawer satu saham hasil Download: blok "Akumulasi 30 hari" menampilkan ±30 bar berwarna + legenda.
4. Klik **Scan Seluruh Pasar**, buka drawer: tampil teks fallback (tanpa error console).
