# Direktori Broker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Label kategori + warna + flag ukuran di setiap kode broker yang tampil.

**Architecture:** `data/broker-direktori.json` (user-editable) diserve via Download + `/api/direktori`; `SP.brokerInfo` + `SP.brTag` sentral dipakai semua titik render; legenda di Lanjutan.

**Tech Stack:** JSON statis, Python (serve saja), vanilla JS, Node smoke test. Tanpa dependensi baru.

## Global Constraints

- Display-only: tanpa ubah angka/skor/aturan/fase.
- Kode tak dikenal → abu "Lainnya"; `nval` absen → tanpa flag ukuran.
- Warna fixed sesuai spec; user boleh edit JSON tanpa sentuh kode.
- Tanpa rebuild `.exe` (launcher mode source).

---

### Task 1: JSON direktori + serve + `SP.brokerInfo`

**Files:**
- Create: `data/broker-direktori.json`
- Modify: `app/app-screener.py` (baca file di `muat_semua` + rute `/api/direktori`), `web/screener-praktis.html` (`SP.brokerInfo`, `SP.brTag`, ekspor, `S.dirBroker`)
- Test: `tests/_test-praktis.js` (blok 17 baru)

**Interfaces:**
- Consumes: JSON `{KODE: {kat, nama, afiliasi, kombo?, scalper?}}`
- Produces: `SP.brokerInfo(kode, nval, dir)` → `{label, warna, flag}`; `SP.brTag(kode, nval, dir)` → HTML; `S.dirBroker` terisi.

- [ ] **Step 1: Tulis `data/broker-direktori.json`**

Konten persis (kat: asing|smart|abu|ritel|zombie):
```json
{
  "AK": {"kat": "asing", "nama": "UBS Sekuritas Indonesia", "afiliasi": ""},
  "BK": {"kat": "asing", "nama": "J.P. Morgan Sekuritas Indonesia", "afiliasi": ""},
  "ZP": {"kat": "asing", "nama": "Maybank Sekuritas Indonesia", "afiliasi": ""},
  "YU": {"kat": "asing", "nama": "CGS International Sekuritas", "afiliasi": "PP"},
  "AI": {"kat": "asing", "nama": "UOB Kay Hian Sekuritas", "afiliasi": ""},
  "KZ": {"kat": "asing", "nama": "CLSA Sekuritas Indonesia", "afiliasi": ""},
  "BQ": {"kat": "asing", "nama": "Korea Investment & Securities", "afiliasi": ""},
  "DP": {"kat": "asing", "nama": "DBS Vickers Sekuritas", "afiliasi": ""},
  "RX": {"kat": "asing", "nama": "Macquarie Sekuritas Indonesia", "afiliasi": ""},
  "RF": {"kat": "smart", "nama": "Buana Capital Sekuritas", "afiliasi": ""},
  "KI": {"kat": "smart", "nama": "Ciptadana Sekuritas Asia", "afiliasi": "Bakrie"},
  "IF": {"kat": "smart", "nama": "Samuel Sekuritas Indonesia", "afiliasi": ""},
  "HP": {"kat": "smart", "nama": "Henan Putihrai Sekuritas", "afiliasi": "PP"},
  "DH": {"kat": "smart", "nama": "Sinarmas Sekuritas", "afiliasi": "Sinarmas"},
  "SS": {"kat": "smart", "nama": "Supra Sekuritas Indonesia", "afiliasi": "Sinarmas"},
  "MU": {"kat": "smart", "nama": "Minna Padi Investama", "afiliasi": "Salim"},
  "ES": {"kat": "smart", "nama": "Ekokapital Sekuritas", "afiliasi": ""},
  "DR": {"kat": "smart", "nama": "RHB Sekuritas Indonesia", "afiliasi": ""},
  "YJ": {"kat": "smart", "nama": "Lotus Andalan Sekuritas", "afiliasi": ""},
  "BB": {"kat": "smart", "nama": "Verdhana Sekuritas", "afiliasi": ""},
  "DX": {"kat": "smart", "nama": "Bahana Sekuritas", "afiliasi": "PP"},
  "OD": {"kat": "smart", "nama": "BRI Danareksa Sekuritas", "afiliasi": ""},
  "RB": {"kat": "smart", "nama": "Ina Sekuritas Indonesia", "afiliasi": "Salim"},
  "OK": {"kat": "smart", "nama": "NET Sekuritas", "afiliasi": "Bakrie"},
  "CC": {"kat": "abu", "nama": "Mandiri Sekuritas", "afiliasi": ""},
  "SQ": {"kat": "abu", "nama": "BCA Sekuritas", "afiliasi": ""},
  "NI": {"kat": "abu", "nama": "BNI Sekuritas", "afiliasi": "PP"},
  "AZ": {"kat": "abu", "nama": "Sucor Sekuritas", "afiliasi": "", "kombo": true},
  "LG": {"kat": "abu", "nama": "Trimegah Sekuritas", "afiliasi": ""},
  "XA": {"kat": "abu", "nama": "NH Korindo Sekuritas", "afiliasi": ""},
  "YB": {"kat": "abu", "nama": "Yakin Bertumbuh Sekuritas", "afiliasi": ""},
  "XC": {"kat": "ritel", "nama": "Ajaib Sekuritas Asia", "afiliasi": "", "kombo": true},
  "XL": {"kat": "ritel", "nama": "Stockbit Sekuritas Digital", "afiliasi": "", "kombo": true},
  "YP": {"kat": "ritel", "nama": "Mirae Asset Sekuritas", "afiliasi": "", "kombo": true},
  "PD": {"kat": "ritel", "nama": "Indo Premier Sekuritas", "afiliasi": "", "kombo": true},
  "MG": {"kat": "ritel", "nama": "Semesta Indovest Sekuritas", "afiliasi": "", "scalper": true},
  "CP": {"kat": "ritel", "nama": "KB Valbury Sekuritas", "afiliasi": "", "scalper": true},
  "ZOMBIE": {"kat": "zombie", "nama": "Broker Pasif / Dormant", "afiliasi": ""}
}
```

- [ ] **Step 2: Serve di `app/app-screener.py`**

Di `muat_semua()`, sebelum `say("Selesai...")` tambahkan:
```python
    direktori = _baca_json("broker-direktori.json")
```
Dan di dict `hasil` tambahkan `"direktori": direktori,`.
Setelah blok rute `/api/tema` (sebelum `/favicon.ico`) tambahkan:
```python
            if jalur == "/api/direktori":
                dd = _baca_json("broker-direktori.json")
                return self._json({"ok": True, "direktori": dd})
```
(`_baca_json` sudah ada dari wiring tema.)

- [ ] **Step 3: `SP.brokerInfo` + `SP.brTag` + ekspor + state (gagal dulu)**

Di `tests/_test-praktis.js`, sebelum `console.log(gagal`, sisipkan blok 17:
```js
// 17) direktori broker
{
  const dir = { OD: { kat: "smart", nama: "BRI Danareksa", afiliasi: "" }, XL: { kat: "ritel", nama: "Stockbit", afiliasi: "", kombo: true }, XC: { kat: "ritel", nama: "Ajaib", afiliasi: "", kombo: true } };
  cek("brokerInfo: OD smart", SP.brokerInfo("OD", 0, dir).label.includes("Smart money"));
  cek("brokerInfo: XL besar bukan ritel", SP.brokerInfo("XL", 2000000000, dir).flag === "besar, bukan ritel");
  cek("brokerInfo: XL kecil tetap ritel", SP.brokerInfo("XL", 50000000, dir).flag === "" && SP.brokerInfo("XL", 50000000, dir).warna === "#fdd835");
  cek("brokerInfo: campuran 100jt-1M", SP.brokerInfo("XL", 500000000, dir).flag === "campuran");
  cek("brokerInfo: tak dikenal abu", SP.brokerInfo("ZZ", 0, dir).warna === "#8a8f98");
  cek("brokerInfo: tanpa nval tanpa flag", SP.brokerInfo("XL", null, dir).flag === "");
}
```
Run: `node tests/_test-praktis.js` → error `TypeError: SP.brokerInfo is not a function`.
Lalu sisipkan setelah fungsi `bounty` (sebelum `// ---------- valuasi sederhana`, DI DALAM modul SP — modul berakhir di `})();` pertama setelah `return {`):
```js
  // ---------- direktori broker (label + warna + flag ukuran) ----------
  var BROKER_KAT = { asing: ["Asing", "#1f5fd0"], smart: ["Smart money", "#17795e"], abu: ["Abu-abu", "#8a8f98"], ritel: ["Ritel", "#b26a00"], zombie: ["Zombie", "#c9cfd6"] };
  var BROKER_AF = { PP: "#e65100", Sinarmas: "#4fc3f7", Salim: "#1a237e", Bakrie: "#6a1b9a" };
  function brokerInfo(kode, nval, dir) {
    var d = (dir || {})[kode] || null;
    if (!d) return { label: "Lainnya", warna: "#8a8f98", flag: "" };
    var base = BROKER_KAT[d.kat] || BROKER_KAT.abu;
    var warna = base[1];
    if (d.kombo) warna = "#fdd835";
    else if (d.scalper) warna = "#9ccc65";
    else if (d.afiliasi && BROKER_AF[d.afiliasi]) warna = BROKER_AF[d.afiliasi];
    var flag = "";
    if (d.kat === "ritel" && nval != null && isFinite(nval)) {
      var a = Math.abs(nval);
      if (a >= 1000000000) flag = "besar, bukan ritel";
      else if (a >= 100000000) flag = "campuran";
    }
    return { label: base[0] + " — " + (d.nama || kode) + (d.afiliasi ? " (" + d.afiliasi + ")" : ""), warna: warna, flag: flag };
  }
  function brTag(kode, nval, dir) {
    var b = brokerInfo(kode, nval, dir);
    return '<span title="' + b.label + (b.flag ? " · " + b.flag : "") + '">' + kode + ' <i style="display:inline-block;width:8px;height:8px;border-radius:99px;background:' + b.warna + '"></i></span>';
  }
```
Ekspor: tambahkan `brokerInfo: brokerInfo, brTag: brTag,` di `return` SP.
State: deklarasi `var S` tambah `dirBroker: {},`; handler Download tambah `S.dirBroker = j.direktori || {};`; init tambah fetch `/api/direktori` setara `/api/tema`.
Run: PASS.

### Task 2: Terapkan di titik render + legenda

**Files:**
- Modify: `web/screener-praktis.html` (`levelBox`, `smBox`, `comboBox`, `renderQuest`, `renderAdv`, cek string)
- Test: smoke + manual

**Interfaces:**
- Consumes: `SP.brTag`, `S.dirBroker`; `entry.acc.top_*[{broker,nval}]` untuk nval (bila ada)
- Produces: UI selesai.

- [ ] **Step 1: 2 cek string (gagal dulu)**

Blok 7 tambah:
```js
  cek("brTag dipakai", html.includes("brTag("));
  cek("legenda broker ada", html.includes("Direktori broker"));
```

- [ ] **Step 2-3: Terapkan + legenda**

`levelBox`: ubah `L.broker.join(", ")` (2 tempat: alarm + bargain) menjadi peta brTag dengan nval dari entry:
```js
    function brList(codes) {
      var tops = {};
      ((e.acc.top_sellers || []).concat(e.acc.top_buyers || [])).forEach(function (b) { tops[b.broker] = b.nval || 0; });
      return codes.map(function (k) { return SP.brTag(k, tops[k] || 0, S.dirBroker); }).join(", ");
    }
```
(sisipkan tepat sebelum `if (L.tipe === "alarm")`, ganti kedua `L.broker.join(", ")` dengan `brList(L.broker)`.)
`smBox`: ubah baris broker — setelah `var m = SP.smartMoney(x, e, wj);` cari kode broker top: `var tbk = (((e.acc || {}).top_buyers || [])[0] || {}).broker || "";` lalu di rows-map: bila `r.sumber` mulai "Broker " ganti label dengan `SP.brTag(tbk)` (tanpa nval): implementasi — ubah `rows = m.rows.map(...)` menjadi bangun manual:
```js
    var rows = m.rows.map(function (r) {
      var lab = r.sumber;
      if (r.sumber.indexOf("Broker ") === 0 && tbk) lab = SP.brTag(tbk) + " (avg " + nf(r.avg, 0) + ")";
      else if (r.sumber.indexOf("Broker ") === 0) lab = r.sumber + " (avg " + nf(r.avg, 0) + ")";
      else lab = r.sumber + " (avg " + nf(r.avg, 0) + ")";
      return row(lab, ...sama...);
    }).join("");
```
Hati-hati: baris asli `row(r.sumber + " (avg " + nf(r.avg, 0) + ")", ...)` — pertahankan struktur, hanya `lab` yang berubah.
`comboBox` streak chip: `e1` bukti dapat field `broker`? SP.combo e1 TIDAK punya broker (hanya txt). Tambahkan: di `SP.combo`, e1 `{st, txt, broker}` (broker = b1.broker atau ""). Test lama tetap lolos (aditif). Chip: `nm[i] + ": " + (i === 0 && b.broker ? SP.brTag(b.broker) + " " : "") + b.txt` — dengan txt "OD 4/5..." akan ganda ("OD● OD 4/5"). Perbaiki: txt e1 tanpa kode? Ubah e1 txt menjadi `hit + "/5 hari net-buy"` (tanpa kode, kode lewat brTag). Cek lama: blok 12 tidak assert isi txt e1 (hanya level/breaker/?) — verifikasi: blok 12 asserts level, breaker, bukti[0].st — aman.
`renderQuest` jejak: `(q.jejak.broker ? q.jejak.broker + " " + ...)` → ganti kode dengan `SP.brTag(q.jejak.broker)` (tanpa nval).
Legenda `renderAdv`: tambah `<h3>Direktori broker</h3>` + daftar dot warna + kalimat ukuran. (Sisip sebelum `<h3>5 ·`/terakhir yang ada — anchor: baris `"<h3>5 · Kombo` atau akhir; baca dulu posisiheadingsaat eksekusi.)

- [ ] **Step 4: Uji**

Run smoke → PASS. Manual: drawer (dot+tooltip+flag), bounty, edit JSON 1 kategori → reload berubah (tanpa rebuild), legenda tampil.
