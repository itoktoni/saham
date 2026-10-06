#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
diag-skor.py — Diagnostik skor Screener Praktis (Fase 0).

Menjawab dua pertanyaan sebelum rumus skor diubah:
  1. Komponen skor (Nilai/Kualitas/Timing/Aliran) mana yang benar-benar
     memprediksi return maju 20 hari (fwd20) — dan mana yang memilih merah?
  2. Apakah calon fix (decay MOS, MOS bandar, gate IHSG) menaikkan
     hit-rate "Beli" yang hijau, di data HOLD-OUT (bulan terakhir)?

Tahap yang dijalankan berurutan:
  1. snapshot -> data/diag-snapshot.csv   (scan seluruh pasar, skor hari ini)
  2. universe -> data/diag-universe.txt   (top-N kandidat, lewat node)
  3. fitur    -> data/diag-fitur.csv      (fitur harian ~6 bulan + label fwd20)
  4. laporan  -> node tests/_diag-skor.js

Catatan jujur (bukan kelemahan tersembunyi):
  - Fundamental (EPS/ekuitas/MOS) dianggap KONSTAN selama jendela (laporan
    keuangan kuartalan; approksimasi makin lemah utk jendela 2 tahun —
    dicatat jujur di sini, bukan disembunyikan).
  - Baris berulang per saham (tiap `step` hari) -> hit-rate dihitung per baris.
  - Split train/test: train = ~16 bulan pertama jendela, test = ekor ~7 bulan
    terakhir (memuat crash Mei'26 + recovery — dua regim beda). Konstanta fix
    ditulis tangan dari TANDA korelasi, TIDAK di-grid-search.

Pemakaian:
  python scripts/diag-skor.py [--top 80] [--step 3] [--no-report]
"""

import argparse
import csv
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
SCRIPTS = os.path.join(ROOT, "scripts")
TESTS = os.path.join(ROOT, "tests")

SNAPSHOT = os.path.join(DATA, "diag-snapshot.csv")
UNIVERSE = os.path.join(DATA, "diag-universe.txt")
FITUR = os.path.join(DATA, "diag-fitur.csv")
IHSG_CACHE = os.path.join(DATA, "diag-ihsg.json")

CHART_RANGE = "5y"           # cukup untuk high 52 minggu + jendela 2 tahun
BARS_WINDOW = 504            # ~2 tahun bursa (fitur dalam jendela ini)
BARS_TRAIN = 168             # panjang EKOR test: test = bar [n-168, n-21)
                             #   -> train = 504-168 = 336 bar (~16 bulan),
                             #      test ~147 bar (~7 bulan: crash Mei'26 + recovery)
BARS_HIGH52 = 252            # high_52 butuh 252 bar di belakang t
BARS_FWD = 21                # label return maju 21 bar (~1 bulan bursa)
KSEI_BULAN = 12              # seri bulanan untuk delta historis


def log(msg=""):
    print(msg, flush=True)


def load_mod(nama, path):
    spec = importlib.util.spec_from_file_location(nama, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def reconfigure_stdout():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


# ----------------------------------------------------------------------------
# Tahap 1 — snapshot pasar hari ini (pakai ambil_tv() milik aplikasi)
# ----------------------------------------------------------------------------

def tahap_snapshot():
    app = load_mod("app_screener", os.path.join(ROOT, "app", "app-screener.py"))
    tv = app.ambil_tv()
    if not tv:
        log("[!] TradingView scan gagal — universe pakai watchlist saja.")
        return False
    with open(SNAPSHOT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=sorted({k for r in tv for k in r}))
        w.writeheader()
        for r in tv:
            w.writerow(r)
    log("[1] snapshot: %d saham -> %s" % (len(tv), os.path.relpath(SNAPSHOT, ROOT)))
    return True


# ----------------------------------------------------------------------------
# Tahap 2 — universe: top-N kandidat menurut modul SP yang asli
# ----------------------------------------------------------------------------

def tahap_universe(top):
    node = shutil.which("node")
    if not node:
        log("[!] node tidak ada di PATH — lewati pemilihan universe.")
        return []
    r = subprocess.run([node, os.path.join(TESTS, "_score-top.js"), str(top)],
                       cwd=ROOT, capture_output=True, text=True)
    sys.stdout.write(r.stdout)
    if r.returncode != 0:
        sys.stderr.write(r.stderr)
        log("[!] _score-top.js gagal.")
        return []
    if not os.path.exists(UNIVERSE):
        return []
    with open(UNIVERSE, encoding="utf-8") as fh:
        kodes = [ln.strip().upper() for ln in fh if ln.strip()]
    log("[2] universe: %d kandidat" % len(kodes))
    return kodes


# ----------------------------------------------------------------------------
# Pengambilan chart dengan timestamp (fetch_chart() bawaan membuang tanggal)
# ----------------------------------------------------------------------------

def chart_dated(f, kode, rng=CHART_RANGE, suffix=".JK"):
    d = f.get("https://query1.finance.yahoo.com/v8/finance/chart/%s%s"
              "?range=%s&interval=1d" % (kode, suffix, rng))
    if not d:
        return None
    res = ((d.get("chart") or {}).get("result") or [None])[0]
    if not res:
        return None
    q = ((res.get("indicators") or {}).get("quote") or [{}])[0]
    ts = res.get("timestamp") or []
    cl = q.get("close") or []
    hi = q.get("high") or []
    lo = q.get("low") or []
    vo = q.get("volume") or []
    out = {"ts": [], "close": [], "high": [], "low": [], "volume": []}
    for i in range(len(ts)):
        c = cl[i] if i < len(cl) else None
        if c is None:
            continue
        out["ts"].append(int(ts[i]))
        out["close"].append(float(c))
        out["high"].append(float(hi[i]) if i < len(hi) and hi[i] else float(c))
        out["low"].append(float(lo[i]) if i < len(lo) and lo[i] else float(c))
        out["volume"].append(float(vo[i]) if i < len(vo) and vo[i] else 0.0)
    return out if len(out["close"]) > 60 else None


def tanggal(ts):
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


# ----------------------------------------------------------------------------
# Seri bulanan KSEI (delta + biaya asing berjalan per tanggal)
# ----------------------------------------------------------------------------

def seri_ksei(fk, kodes_butuh):
    daftar = fk.daftar_bulan(KSEI_BULAN)
    seri = {}
    for tgl, url in reversed(daftar):
        p = fk.unduh_zip(url)
        if not p:
            continue
        d = fk.parse_zip(p)
        for kode, row in d.items():
            if kode in kodes_butuh:
                seri.setdefault(kode, []).append((tgl, row))
    log("    seri KSEI: %d emiten x s.d. %d bulan" % (len(seri), len(daftar)))
    return seri


def ksei_pada(rows, kunci):
    """(delta_asing, delta_inst, asing_pct, asing_avg) pada/ sebelum kunci YYYYMMDD."""
    idx = -1
    for i, (tgl, _r) in enumerate(rows):
        if tgl <= kunci:
            idx = i
        else:
            break
    if idx < 0:
        return None
    cur = rows[idx][1]
    d_asing = d_inst = None
    if idx >= 1:
        pv = rows[idx - 1][1]
        d_asing = round(cur["asing_pct"] - pv["asing_pct"], 3)
        d_inst = round(cur["institusi_pct"] - pv["institusi_pct"], 3)
    # biaya rata-rata asing berjalan: hanya bulan yang lembar asingnya naik
    buy_sh = buy_cost = 0.0
    prev_fs = None
    for (_t, row) in rows[:idx + 1]:
        fs = float(row.get("asing_saham") or 0)
        pr = float(row.get("harga_ksei") or 0)
        if prev_fs is not None and fs > prev_fs:
            add = fs - prev_fs
            buy_sh += add
            buy_cost += add * pr
        prev_fs = fs
    avg = round(buy_cost / buy_sh, 2) if buy_sh > 0 else None
    return d_asing, d_inst, cur["asing_pct"], avg


# ----------------------------------------------------------------------------
# Tahap 3 — fitur historis + label maju
# ----------------------------------------------------------------------------

FITUR_COLS = [
    "t", "split", "kode", "nama", "sektor", "harga",
    "eps", "ekuitas", "saham", "laba", "der", "cagr", "roe", "pbv", "per",
    "eps_trend", "nilai_harian",
    "s_sideways", "s_vol_ratio", "s_freqspike", "s_spring",
    "s_closeabove", "s_springlow", "s_resistance", "high_52",
    "dksei_asing_1m", "dksei_institusi_1m", "asing_pct", "asing_avg_price",
    "ret20", "ihsg_r1", "fwd20", "fwd60",
]


def baca_fundamen():
    """Fundamental TERKINI per kode: watchlist (data-idx.csv) lalu snapshot TV."""
    fund = {}
    idx_csv = os.path.join(DATA, "data-idx.csv")
    if os.path.exists(idx_csv):
        with open(idx_csv, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if r.get("kode"):
                    fund[r["kode"].strip().upper()] = r
    if os.path.exists(SNAPSHOT):
        with open(SNAPSHOT, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                k = (r.get("kode") or "").strip().upper()
                if k and k not in fund:
                    fund[k] = r
    return fund


def _ihsg_valid(ch):
    """Validasi keras chart IHSG: rentang level indeks + jumlah bar.

    Pernah gagal diam-diam (respons Yahoo terdegradasi setelah banyak request)
    -> ihsg_r1 jadi -11..-35% untuk semua baris. Sekarang gagal = tak dipakai.
    """
    if not ch or not ch.get("close"):
        return False
    closes = [c for c in ch["close"] if c]
    if len(closes) < 200:
        return False
    lo, hi = min(closes), max(closes)
    if not (1000 < lo < 20000 and 1000 < hi < 20000):
        return False
    tgl = {tanggal(t) for t in ch["ts"]}
    return len(tgl) >= 400  # ~2 tahun bursa


def _ambil_ihsg(f):
    """Chart IHSG dengan cache + validasi; ulang sekali bila tak masuk akal."""
    if os.path.exists(IHSG_CACHE):
        with open(IHSG_CACHE, encoding="utf-8") as fh:
            cache = json.load(fh)
        ch = {"ts": cache.get("ts") or [], "close": cache.get("close") or []}
        if _ihsg_valid(ch):
            log("[i] IHSG dari cache: %d bar (%s .. %s)"
                % (len(ch["close"]), tanggal(ch["ts"][0]), tanggal(ch["ts"][-1])))
            return ch
        log("[!] cache IHSG tak valid — diambil ulang.")
    ch = chart_dated(f, "^JKSE", suffix="")
    if not _ihsg_valid(ch):
        log("[!] chart IHSG lolos fetch tapi gagal validasi — coba ulang sekali.")
        time.sleep(2)
        ch = chart_dated(f, "^JKSE", suffix="")
    if not _ihsg_valid(ch):
        raise RuntimeError(
            "chart IHSG tidak valid (kemungkinan respons Yahoo rusak) — "
            "hasil ihsg_r1 akan salah, berhenti daripada menulis CSV keliru.")
    with open(IHSG_CACHE, "w", encoding="utf-8") as fh:
        json.dump({"ts": ch["ts"], "close": ch["close"]}, fh)
    log("[i] IHSG segar: %d bar (%s .. %s) -> cache"
        % (len(ch["close"]), tanggal(ch["ts"][0]), tanggal(ch["ts"][-1])))
    return ch


def tahap_fitur(fd, fk, kodes, step):
    fund = baca_fundamen()
    f = fd.Fetcher(delay=0.3)
    f._login()
    log("[3] mengambil chart %s untuk %d kandidat..." % (CHART_RANGE, len(kodes)))
    charts = {}
    for i, kode in enumerate(kodes, 1):
        ch = chart_dated(f, kode)
        if ch:
            charts[kode] = ch
        else:
            log("    %s: chart gagal" % kode)
        time.sleep(0.2)
        if i % 10 == 0:
            log("    %d/%d" % (i, len(kodes)))
    ihsg = _ambil_ihsg(f)
    ihsg_tgl = {tanggal(t): c for t, c in zip(ihsg["ts"], ihsg["close"])}
    ihsg_urut = sorted(ihsg_tgl.items())

    def ihsg_close_le(kunci):
        """Close IHSG terakhir pada/ sebelum kunci YYYYMMDD (boleh ber-dash)."""
        kunci = kunci.replace("-", "")  # kunci bisa datang sebagai YYYY-MM-DD
        best = None
        for tgl, c in ihsg_urut:
            if tgl.replace("-", "") <= kunci:
                best = c
            else:
                break
        return best

    seri = seri_ksei(fk, set(charts))

    n_baris = 0
    with open(FITUR, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(FITUR_COLS)
        for kode, ch in charts.items():
            fu = fund.get(kode) or {}
            cl, hi, lo, vo = ch["close"], ch["high"], ch["low"], ch["volume"]
            n = len(cl)
            i_awal = max(BARS_HIGH52, n - BARS_WINDOW)
            i_akhir = n - BARS_FWD
            rows_k = seri.get(kode) or []
            i_test = n - BARS_TRAIN
            for i in range(i_awal, i_akhir, step):
                tgl = tanggal(ch["ts"][i])
                kunci = tgl.replace("-", "")
                sw = fd.hitung_swing({"close": cl[:i + 1], "high": hi[:i + 1],
                                      "low": lo[:i + 1], "volume": vo[:i + 1]})
                k = ksei_pada(rows_k, kunci)
                d_asing, d_inst, asing_pct, asing_avg = (k if k else (None, None, None, None))
                harga = cl[i]
                ret20 = (cl[i] / cl[i - 21] - 1.0) * 100 if i >= 21 else None
                i0 = ihsg_close_le(kunci)
                i1 = ihsg_close_le(tanggal(ch["ts"][i - 21])) if i >= 21 else None
                ihsg_r1 = (i0 / i1 - 1.0) * 100 if (i0 and i1) else None
                if ihsg_r1 is not None and abs(ihsg_r1) > 30:
                    raise RuntimeError(
                        "ihsg_r1 tak masuk akal di %s (%s): %.1f%% — data IHSG korup."
                        % (kode, tgl, ihsg_r1))
                fwd20 = (cl[i + BARS_FWD] / harga - 1.0) * 100
                fwd60 = (cl[i + 60] / harga - 1.0) * 100 if i + 60 < n else None
                split = "test" if i >= i_test else "train"
                w.writerow([
                    tgl, split, kode,
                    fu.get("nama", ""), fu.get("sektor", ""), _f(harga),
                    fu.get("eps", 0), fu.get("ekuitas", 0), fu.get("saham", 0),
                    fu.get("laba", 0), fu.get("der", 0), fu.get("cagr", 0),
                    fu.get("roe", 0), fu.get("pbv", 0), fu.get("per", 0),
                    fu.get("eps_trend", "fluktuatif"), fu.get("nilai_harian", 0),
                    sw["s_sideways"], sw["s_vol_ratio"], sw["s_freqspike"],
                    sw["s_spring"], sw["s_closeabove"], sw["s_springlow"],
                    sw["s_resistance"], _f(max(hi[i - BARS_HIGH52 + 1:i + 1])),
                    _s(d_asing), _s(d_inst), _s(asing_pct), _s(asing_avg),
                    _s(ret20), _s(ihsg_r1), _f(fwd20), _s(fwd60),
                ])
                n_baris += 1
    log("[3] fitur: %d baris -> %s" % (n_baris, os.path.relpath(FITUR, ROOT)))
    return n_baris


def _f(x):
    try:
        return round(float(x), 4)
    except (TypeError, ValueError):
        return 0


def _s(x):
    return "" if x is None else _f(x)


# ----------------------------------------------------------------------------
# Tahap 4 — laporan lewat node (modul SP yang sama dengan halaman)
# ----------------------------------------------------------------------------

def tahap_laporan():
    node = shutil.which("node")
    if not node:
        log("[!] node tidak ada — laporan dilewati. Jalankan: node tests/_diag-skor.js")
        return 1
    r = subprocess.run([node, os.path.join(TESTS, "_diag-skor.js")], cwd=ROOT)
    return r.returncode


def main():
    reconfigure_stdout()
    ap = argparse.ArgumentParser(description="Diagnostik skor Screener Praktis")
    ap.add_argument("--top", type=int, default=80, help="jumlah kandidat (default 80)")
    ap.add_argument("--step", type=int, default=3, help="jarak bar antar sampel (default 3)")
    ap.add_argument("--no-report", action="store_true", help="hanya tulis CSV, tanpa laporan")
    args = ap.parse_args()

    os.makedirs(DATA, exist_ok=True)
    fd = load_mod("fetch_idx", os.path.join(SCRIPTS, "fetch-data-idx.py"))
    fk = load_mod("fetch_ksei", os.path.join(SCRIPTS, "fetch-ksei.py"))

    log("=" * 68)
    log(" DIAGNOSTIK SKOR — Screener Praktis")
    log("=" * 68)

    tahap_snapshot()
    kodes = tahap_universe(args.top)
    if not kodes:
        log("[!] universe kosong — berhenti.")
        return 1
    if tahap_fitur(fd, fk, kodes, args.step) == 0:
        log("[!] tidak ada baris fitur — berhenti.")
        return 1
    if args.no_report:
        return 0
    log("")
    return tahap_laporan()


if __name__ == "__main__":
    sys.exit(main())
