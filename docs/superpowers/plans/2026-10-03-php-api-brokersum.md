# SQLite Broker Summary Implementation Plan (REVISI: tanpa PHP/MariaDB)

> **Untuk user:** atas permintaan, PHP API + MariaDB DIBATALKAN. Penyimpanan =
> SQLite `data/saham.db` via `sqlite3` stdlib — Python langsung eksekusi.
> Tabel `broker_summary` yang sempat dibuat di MariaDB dibiarkan kosong
> (tidak dipakai, tidak mengganggu).

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Simpan broker-summary IndoPremier ke SQLite lokal dan pakai avg-nya sebagai sumber utama level broker.

**Architecture:** `fetch-brokersum.py` ambil agregat 30 hari/emiten → tulis `data/saham.db` (idempoten) → respons Download bawa peta avg; frontend prefer peta avg, fallback series SahamScope.

**Tech Stack:** Python stdlib (`sqlite3`, `urllib`), vanilla JS satu file HTML, Node smoke test. Tanpa dependensi/PHP/service baru.

## Global Constraints

- Python hanya standard library; DB = file `data/saham.db` (portable ikut folder).
- IndoPremier sopan: delay 2 dtk/req, timeout 30; skip fetch bila DB sudah punya window sama.
- Gagal di titik mana pun → fallback JSON lama; Download tetap sukses.
- Tanpa ubah skor/aksi; tanpa rebuild `.exe` (launcher mode source).

---

### Task 1: Skema SQLite + tulis/baca (`scripts/fetch-brokersum.py`)

**Files:**
- Modify: `scripts/fetch-brokersum.py` (TAMBAH fungsi DB di bawah; fetch/parse ikut Task 2)
- Test: `python -c` roundtrip ke DB temp (tanpa network)

**Interfaces:**
- Consumes: `sqlite3` stdlib; path DB dari caller (default `saham.db` di cwd)
- Produces: `db_init(db)`, `db_ada(db, kode, awal, akhir) -> bool`, `db_simpan(db, snapshot) -> int`, `db_baca(db, kode, awal, akhir) -> rows`; dipakai Task 3.

- [ ] **Step 1: Tambah fungsi DB ke `fetch-brokersum.py`**

Setelah konstanta (sebelum parser), sisipkan:
```python
import sqlite3

DDL_BROKER = ("CREATE TABLE IF NOT EXISTS broker_summary (kode TEXT NOT NULL, tgl_awal TEXT NOT NULL, tgl_akhir TEXT NOT NULL, broker TEXT NOT NULL, sisi TEXT NOT NULL, lot INTEGER NOT NULL DEFAULT 0, val_rp INTEGER NOT NULL DEFAULT 0, avg INTEGER NOT NULL DEFAULT 0, diambil TEXT NOT NULL, PRIMARY KEY (kode, tgl_awal, tgl_akhir, broker, sisi)) WITHOUT ROWID")


def db_init(db):
    c = sqlite3.connect(db)
    try:
        c.execute(DDL_BROKER)
        c.commit()
    finally:
        c.close()


def db_ada(db, kode, awal, akhir):
    try:
        c = sqlite3.connect(db)
        try:
            n = c.execute("SELECT COUNT(*) FROM broker_summary WHERE kode=? AND tgl_awal=? AND tgl_akhir=?", (kode, awal, akhir)).fetchone()[0]
            return n > 0
        finally:
            c.close()
    except Exception:
        return False


def db_simpan(db, snapshot):
    db_init(db)
    rows = []
    for sisi, lst in (("B", snapshot["buyers"]), ("S", snapshot["sellers"])):
        for b in lst:
            rows.append((snapshot["kode"], snapshot["tgl_awal"], snapshot["tgl_akhir"],
                         b["broker"], sisi, b["lot"], b["val"], b["avg"],
                         datetime.now().astimezone().isoformat(timespec="seconds")))
    c = sqlite3.connect(db)
    try:
        c.executemany("INSERT OR REPLACE INTO broker_summary (kode,tgl_awal,tgl_akhir,broker,sisi,lot,val_rp,avg,diambil) VALUES (?,?,?,?,?,?,?,?,?)", rows)
        c.commit()
    finally:
        c.close()
    return len(rows)


def db_baca(db, kode, awal, akhir):
    c = sqlite3.connect(db)
    try:
        return [dict(r) for r in c.execute(
            "SELECT broker,sisi,lot,val_rp AS val,avg FROM broker_summary WHERE kode=? AND tgl_awal=? AND tgl_akhir=?", (kode, awal, akhir)).fetchall()]
    except Exception:
        return []
    finally:
        try: c.close()
        except Exception: pass
```
(Catatan: `fetchall` tanpa `row_factory` memberi tuple — perbaiki: set `c.row_factory = sqlite3.Row` sebelum execute di `db_baca`. Tulis `c.row_factory = sqlite3.Row` sebagai baris pertama setelah connect di `db_baca`.)

- [ ] **Step 2: Uji roundtrip ke DB temp**

Run (tulis ke skrip temp bila quoting bermasalah, pola `cek*.py`):
```bash
python -c "import importlib.util,tempfile,os; s=importlib.util.spec_from_file_location('b','scripts/fetch-brokersum.py'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); d=os.path.join(tempfile.mkdtemp(),'t.db'); snap={'kode':'TST','tgl_awal':'2026-09-03','tgl_akhir':'2026-10-03','buyers':[{'broker':'OD','lot':10,'val':20000,'avg':2000}],'sellers':[]}; assert m.db_simpan(d,snap)==1; assert m.db_ada(d,'TST','2026-09-03','2026-10-03'); r=m.db_baca(d,'TST','2026-09-03','2026-10-03'); assert r[0]['avg']==2000 and r[0]['sisi']=='B', r; print('sqlite OK')"
```
Expected: mencetak `sqlite OK`. (Modul `fetch-brokersum.py` belum ada saat Step 1 Task 2 lama — file dibuat di Task 2 revised di bawah; URUTAN: kerjakan Task 2 (fetch+parse) DULU lalu kembali ke sini. Tandai Task 1 selesai setelah keduanya hijau.)

### Task 2: PHP query API — DIBATALKAN

Dibatalkan atas permintaan user (tanpa PHP). Inspeksi DB via `sqlite3` CLI? Tidak ada CLI sqlite di Windows — inspeksi via `python -c` satu baris bila perlu. Tidak ada file/test.

### Task 3: `fetch-brokersum.py` fetch + parse (nomor lama Task 3, isi sama)

(Lihat draf sebelumnya: parser `_Sum`, `parse_nom`/`parse_int`, `ambil_satu`, `tulis_db` DIHAPUS diganti `db_simpan`, `main` menulis DB via `db_simpan("saham.db")` di cwd.)
- [ ] Step 1-3 sama, dengan penyesuaian: tidak ada pipe PHP; setelah `ambil_satu` → `db_simpan("saham.db", snap)` best-effort try/except; main cetak ringkas.
- [ ] Uji offline fixture + live 1 emiten + verifikasi `db_baca` mengembalikan barisnya.

- [ ] **Step 1: Tulis modul**

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fetch-brokersum.py: broker summary IndoPremier -> SQLite + respons scope-shape."""
import json, re, sqlite3, sys, time, urllib.request
from datetime import datetime, timedelta
from html.parser import HTMLParser

BASE = "https://www.indopremier.com/module/saham/include/data-brokersummary.php"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
DB_FILE = "saham.db"


def parse_nom(s):
    s = (s or "").strip().upper().replace("RP", "").strip()
    if not s or s in ("—", "-", "--"):
        return 0
    m = 1
    if s.endswith("B"): m, s = 1000000000, s[:-1]
    elif s.endswith("M"): m, s = 1000000, s[:-1]
    elif s.endswith("K"): m, s = 1000, s[:-1]
    s = s.replace(",", "")
    try: return int(float(s) * m)
    except ValueError: return 0


def parse_int(s):
    return parse_nom(s) if s and re.search(r"[BMK]$", (s or "").strip().upper()) else int((s or "0").replace(",", "").strip() or 0)


class _Sum(HTMLParser):
    def __init__(self):
        super().__init__()
        self.baris, self._td, self._tr = [], [], False
    def handle_starttag(self, tag, attrs):
        if tag == "tr": self._tr, self._td = True, []
        if tag == "td" and self._tr: self._td.append("")
    def handle_data(self, data):
        if self._tr and self._td: self._td[-1] += data
    def handle_endtag(self, tag):
        if tag == "tr" and self._tr:
            c = [t.strip() for t in self._td]
            if len(c) >= 9 and re.fullmatch(r"[A-Z]{2}", c[0] or ""):
                self.baris.append(c)
            self._tr = False


def ambil_satu(kode, awal, akhir, timeout=30):
    url = "%s?code=%s&start=%s&end=%s&fd=all&board=all" % (BASE, kode, awal, akhir)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        t = _Sum(); t.feed(r.read().decode("utf-8", "replace"))
    buy, sell = [], []
    for c in t.baris:
        try:
            buy.append({"broker": c[0], "lot": parse_int(c[1]), "val": parse_nom(c[2]), "avg": parse_int(c[3])})
            sell.append({"broker": c[5], "lot": parse_int(c[6]), "val": parse_nom(c[7]), "avg": parse_int(c[8])})
        except (IndexError, ValueError): continue
    return {"kode": kode, "tgl_awal": awal, "tgl_akhir": akhir, "buyers": buy, "sellers": sell}
```
(Catatan: `parse_int("58,700")` → 58700; `parse_int("2,503")` → 2503; `parse_nom("14.7 B")` → 14700000000. Format `MM/DD/YYYY` untuk awal/akhir.)

Fungsi tulis/baca DB (langsung sqlite3, best-effort di caller):
```python
def db_ada(db, kode, awal, akhir):
    try:
        c = sqlite3.connect(db)
        try:
            return c.execute("SELECT COUNT(*) FROM broker_summary WHERE kode=? AND tgl_awal=? AND tgl_akhir=?", (kode, awal, akhir)).fetchone()[0] > 0
        finally: c.close()
    except Exception: return False


Struktur akhir modul: konstanta + 4 fungsi DB Task 1 + parser/fetch di atas + main:
untuk tiap kode argv (atau BBCA bila kosong): window `akhir=today`,
`awal=today-30` (ISO untuk DB, `MM/DD/YYYY` untuk URL); bila `db_ada` →
cetak "skip (DB)"; else `ambil_satu` → `db_simpan` dalam try/except
(gagal = log, lanjut) → cetak ringkas. Delay 2 dtk antar emiten.

- [ ] **Step 2: Uji offline fixture**

Simpan cuplikan 1 baris buyer+seller HTML asli ke `tests/fixture-brokersum.html` (salin dari respons live secukupnya: 1 `<tr>...</tr>` buyer-seller + footer tidak perlu), lalu:
```bash
python -c "parse fixture -> buyers[0]=={broker:'DX',lot:58700,val:14700000000,avg:2503}"
```
(Perintah `python -c` panjang rawan quoting PowerShell — tulis cek ke berkas temp bila perlu, seperti pola `cek*.py` sebelumnya.) Expected: angka persis.

- [ ] **Step 3: Uji live 1 emiten + tulis DB**

Run: `python scripts/fetch-brokersum.py ADRO` (main: window today-30..today format MM/DD/YYYY, delay, tulis DB, cetak ringkas).
Expected: buyers/sellers terisi; `db_baca` mengembalikan barisnya (cek via skrip temp bila perlu).

### Task 4: Wire ke Download + preferensi frontend

**Files:**
- Modify: `app/app-screener.py` (panggil fetch-brokersum di `muat_semua`, sertakan peta avg di `scope.emiten[*].acc`), `web/screener-praktis.html` (`exitLevel`/`smartMoney` prefer peta, label sumber)
- Test: smoke + manual

**Interfaces:**
- Consumes: Task 3
- Produces: drawer avg broker dari IndoPremier bila ada, fallback scope.

- [ ] **Step 1: Server sertakan peta avg**

Di `muat_semua()`, setelah scope diambil: untuk tiap kode watchlist, cek DB via CLI `get` (window = 30 hari s/d hari ini, format ISO `YYYY-MM-DD`? DB simpan DATE — window IndoPremier MM/DD/YYYY vs DB: simpan ISO di DB, konversi saat fetch). Bila baris ada → `scope["emiten"][kode]["acc"]["avgB"/"avgS"] = {broker: avg}` + `"sumber": "IP"`. Gagal/DB mati → lewati diam-diam (fallback scope).
(Konversi tanggal: fetch pakai MM/DD/YYYY ke IndoPremier; simpan ISO ke DB.)

- [ ] **Step 2: Frontend prefer peta avg**

`exitLevel`: bila `acc.avgS` ada → level dari peta (tanpa hitung mean series); `acc.avgB` untuk bargain. `smartMoney` baris broker: avg dari `avgB[top-1]` bila ada. Tambah teks sumber di blok: `"Sumber avg broker: IndoPremier."` vs `"Sumber avg broker: SahamScope."` (1 baris mut di `levelBox`/`smBox`).
Fallback: perilaku lama bila peta absen (jangan hapus kode lama).

- [ ] **Step 3: Uji**

Smoke hijau (kasus lama tetap lolos = fallback utuh) + cek baru: entry dengan `avgB/avgS` → level dipakai langsung. Manual: Download → drawer BBCA dkk berlabel IndoPremier (bila fetch hari itu sukses).
