#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
app-screener.py
===============
Aplikasi lokal "Screener Praktis Saham IDX".

Dijalankan dengan klik dua kali pada "Jalankan Screener.vbs" (tanpa ketik
perintah). Aplikasi:
  1. menyalakan server kecil di 127.0.0.1,
  2. membuka screener-praktis.html di peramban bawaan,
  3. menyediakan tombol "Download Data" yang mengambil data untuk Anda:
       - kepemilikan KSEI (asing/lokal per emiten)  -> gratis
       - harga & fundamental (Yahoo Finance)         -> gratis
  tanpa perlu menjalankan skrip apa pun secara manual.

Hanya standard library. Sumber data langsung dari internet saat tombol ditekan.
"""

import importlib.util
import json
import os
import socket
import sys
import threading
import time
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
import urllib.request

# Modul standard-library yang dipakai oleh skrip data (fetch-data-idx.py /
# fetch-ksei.py) yang dimuat saat RUNTIME. Diimpor di sini agar PyInstaller
# ikut mengemasnya ke dalam .exe (kalau tidak -> "No module named 'xml'").
import argparse               # noqa: F401
import collections            # noqa: F401
import http.cookiejar         # noqa: F401
import io                     # noqa: F401
import math                   # noqa: F401
import re                     # noqa: F401
import shutil                 # noqa: F401
import struct                 # noqa: F401
import subprocess             # noqa: F401
import urllib.error           # noqa: F401
import xml.etree.ElementTree  # noqa: F401
import zipfile                # noqa: F401

HERE = os.path.dirname(os.path.abspath(__file__))          # .../app (mode sumber)
if getattr(sys, "frozen", False):
    ROOT = os.path.dirname(sys.executable)     # folder .exe (mode portable)
    RES = getattr(sys, "_MEIPASS", ROOT)       # sumber daya terpaket di dalam .exe
else:
    ROOT = os.path.dirname(HERE)               # akar proyek
    RES = ROOT
WEB_DIR = os.path.join(RES, "web")
SCRIPTS_DIR = os.path.join(RES, "scripts")
DATA_DIR = os.path.join(ROOT, "data")
LOGS_DIR = os.path.join(ROOT, "logs")
for _d in (DATA_DIR, LOGS_DIR):
    os.makedirs(_d, exist_ok=True)
os.chdir(DATA_DIR)              # keluaran & cache relatif tinggal di data/

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
TV_URL = "https://scanner.tradingview.com/indonesia/scan"
TV_COLS = ["name", "description", "close", "volume", "relative_volume_10d_calc",
           "market_cap_basic", "price_earnings_ttm", "price_book_ratio",
           "return_on_equity", "debt_to_equity", "sector", "High.1M", "Low.1M",
           "earnings_per_share_basic_ttm", "RSI", "SMA50", "SMA200", "change",
           "price_52_week_high", "Perf.1M"]

HTML_FILE = "screener-praktis.html"
WATCHLIST_FILE = "daftar-saham.txt"
CONFIG_FILE = "config.json"
LOG_FILE = os.path.join(LOGS_DIR, "screener-app.log")
PID_FILE = os.path.join(ROOT, "screener.pid")
BASE_PORT = 8765
DEFAULT_BULAN_KSEI = 24
DEFAULT_WATCHLIST = ["BBCA", "BBRI", "BMRI", "BBNI", "TLKM", "ASII", "ANTM", "ADRO", "ICBP", "PTBA"]

_cache = {}          # nama -> {"t": epoch, "v": data}
CACHE_KSEI = 1 * 3600      # 1 jam
CACHE_EMITEN = 1 * 3600    # 1 jam
CACHE_TV = 1 * 3600        # 1 jam (data pasar TradingView)


def tulis_log(msg):
    line = "[%s] %s" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        pass


def load_mod(nama, berkas):
    path = os.path.join(SCRIPTS_DIR, berkas)
    spec = importlib.util.spec_from_file_location(nama, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


_fd = None      # fetch-data-idx (Yahoo + IDX)
_ksei = None    # fetch-ksei
_scope = None   # fetch-sahamscope


def modul():
    global _fd, _ksei
    if _fd is None:
        _fd = load_mod("fetch_idx", "fetch-data-idx.py")
    if _ksei is None:
        _ksei = load_mod("fetch_ksei", "fetch-ksei.py")
    return _fd, _ksei


CACHE_SCOPE = 1 * 3600   # 1 jam


def modul_scope():
    global _scope
    if _scope is None:
        _scope = load_mod("fetch_scope", "fetch-sahamscope.py")
    return _scope


def ambil_scope(kodes, tulis_cache=True):
    sc = modul_scope()
    return sc.ambil_scope(kodes, log_fn=lambda m: tulis_log("scope " + m.strip() if m else ""),
                          tulis_cache=tulis_cache)


TEMA_TTL_HARI = 30


def _baca_json(nama):
    try:
        with open(nama, "r", encoding="utf-8") as fh:
            return json.load(fh) or {}
    except (OSError, json.JSONDecodeError):
        return {}


def baca_harian_terbaru(data_dir, tanggal=None):
    import glob as _glob
    if tanggal:
        path = os.path.join(data_dir, "harian-%s.json" % tanggal)
        if not os.path.exists(path):
            return None
    else:
        files = sorted(_glob.glob(os.path.join(data_dir, "harian-*.json")))
        if not files:
            return None
        path = files[-1]
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None


def muat_tema():
    base = _baca_json("tema.json")
    segar = False
    if base and base.get("diambil"):
        try:
            selisih = datetime.now().astimezone() - datetime.fromisoformat(base["diambil"])
            segar = selisih.days < TEMA_TTL_HARI
        except ValueError:
            segar = False
    if not segar:
        try:
            ft = load_mod("fetch_tema", "fetch-tema.py")
            base = ft.ambil_tema(log_fn=lambda m: tulis_log("tema " + m.strip() if m else ""))
        except Exception as e:  # noqa: BLE001
            tulis_log("tema gagal: %s" % e)
            base = base or {}
    man = _baca_json("tema-manual.json")
    if man and base.get("tema"):
        for t in base["tema"]:
            des = (man.get("deskripsi") or {}).get(t["nama"])
            if des:
                t["deskripsi"] = des
            for k in (man.get("tambahan") or {}).get(t["nama"], []):
                kk = str(k).strip().upper()
                if kk and kk not in t["emiten"]:
                    t["emiten"].append(kk)
    return base or {}


FUND_TTL_HARI = 30


def muat_fund(kodes):
    try:
        with open("fund-gabungan.json", "r", encoding="utf-8") as fh:
            base = json.load(fh) or {}
    except (OSError, json.JSONDecodeError):
        base = {}
    perlu = [k for k in (kodes or []) if k not in (base.get("emiten") or {})]
    segar = False
    if base.get("diambil"):
        try:
            segar = (datetime.now().astimezone() - datetime.fromisoformat(base["diambil"])).days < FUND_TTL_HARI
        except ValueError:
            segar = False
    if perlu and not segar:
        try:
            ff = load_mod("fetch_fund", "fetch-fund-gabungan.py")
            base = ff.ambil_semua(perlu, log_fn=lambda m: tulis_log("fund " + m.strip() if m else ""))
        except Exception as e:  # noqa: BLE001
            tulis_log("fund gagal: %s" % e)
    return base if isinstance(base, dict) else {}


def baca_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as fh:
                return json.load(fh) or {}
        except (OSError, json.JSONDecodeError):
            return {}
    return {}


def bersih_kode(daftar):
    out, lihat = [], set()
    for x in (daftar or []):
        k = str(x).strip().upper().replace(".JK", "")
        if k and k not in lihat:
            lihat.add(k)
            out.append(k)
    return out


def bulan_ksei():
    try:
        v = int(baca_config().get("bulan_ksei") or DEFAULT_BULAN_KSEI)
    except (TypeError, ValueError):
        v = DEFAULT_BULAN_KSEI
    return max(2, min(48, v))


def daftar_baca():
    cfg = baca_config()
    kodes = bersih_kode(cfg.get("daftar_saham"))
    if kodes:
        return kodes
    if os.path.exists(WATCHLIST_FILE):
        with open(WATCHLIST_FILE, "r", encoding="utf-8") as fh:
            kodes = [ln.strip().upper().replace(".JK", "") for ln in fh
                     if ln.strip() and not ln.strip().startswith("#")]
    return bersih_kode(kodes) or list(DEFAULT_WATCHLIST)


def cache_ambil(nama, ttl, pembuat, log_fn=print):
    c = _cache.get(nama)
    if c and (time.time() - c["t"]) < ttl:
        log_fn("[cache] memakai %s yang tersimpan (%.0f menit lalu)"
               % (nama, (time.time() - c["t"]) / 60))
        return c["v"]
    v = pembuat()
    if v is not None:
        _cache[nama] = {"t": time.time(), "v": v}
    return v


def ambil_ksei():
    _, ks = modul()
    return ks.ambil_ksei(log_fn=lambda m: tulis_log("ksei " + m.strip() if m else ""),
                         bulan=bulan_ksei())


def ambil_emiten(kodes):
    fd, _ = modul()
    log = lambda m: tulis_log("emiten " + m)
    f = fd.Fetcher(delay=1.0)
    if not f._login():
        tulis_log("emiten: gagal sesi Yahoo")
        return None
    prof = fd.load_idx_profiles(f, use_cache=True)
    recs = []
    for i, kode in enumerate(kodes, 1):
        try:
            fund = fd.fetch_fundamental(f, kode)
            time.sleep(0.3)
            ch = fd.fetch_chart(f, kode, "1y")
            if not fund and not ch:
                log("%s: tidak ada data" % kode)
                continue
            rec = fd.build_record(kode, prof.get(kode), fund, ch, None)
            rec.pop("_catatan", None)
            if ch and ch.get("high"):
                h = [x for x in ch["high"][-252:] if x]
                if h:
                    rec["high_52"] = max(h)
            if ch and ch.get("close"):
                c = [x for x in ch["close"] if x]
                if len(c) > 22:
                    rec["ret20"] = (c[-1] / c[-22] - 1.0) * 100
            recs.append(rec)
            log("[%d/%d] %s ok" % (i, len(kodes), kode))
        except Exception as e:  # noqa: BLE001
            log("%s: error %s" % (kode, str(e)[:120]))
    return recs


def ambil_tv():
    """Seluruh pasar IDX dari TradingView scanner (gratis, tanpa kunci).

    Mengembalikan daftar baris yang kompatibel dengan mesin screener:
    High.1M/Low.1M dipakai sebagai resistance/support (setara rentang 20 hari).
    """
    body = {
        "filter": [{"left": "type", "operation": "equal", "right": "stock"}],
        "options": {"lang": "en"},
        "columns": TV_COLS,
        "sort": {"sortBy": "market_cap_basic", "sortOrder": "desc"},
        "range": [0, 1200],
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(TV_URL, data=data, headers={
        "Content-Type": "application/json;charset=UTF-8",
        "Accept": "application/json",
        "User-Agent": UA,
        "Origin": "https://www.tradingview.com",
        "Referer": "https://www.tradingview.com/",
    })
    with urllib.request.urlopen(req, timeout=60) as r:
        obj = json.loads(r.read().decode("utf-8", "replace"))
    rows = []
    for it in obj.get("data") or []:
        kode = str(it.get("s", "")).split(":")[-1].upper()
        if not kode:
            continue
        d = dict(zip(TV_COLS, it.get("d") or []))
        close = d.get("close") or 0
        hi = d.get("High.1M")
        lo = d.get("Low.1M")
        vol = d.get("volume") or 0
        rv = d.get("relative_volume_10d_calc")
        pos = ((close - lo) / (hi - lo)) if (hi and lo and hi > lo) else 0.5
        lebar = (hi / lo - 1) if (hi and lo and lo > 0) else 1
        sideways = 1 if (lebar < 0.12 and pos < 0.40) else 0
        rows.append({
            "kode": kode, "nama": d.get("description") or kode, "sektor": d.get("sector") or "",
            "harga": close, "eps": d.get("earnings_per_share_basic_ttm") or 0,
            "per": d.get("price_earnings_ttm"), "pbv": d.get("price_book_ratio"),
            "roe": d.get("return_on_equity"), "der": d.get("debt_to_equity") or 0,
            "cagr": 0, "eps_trend": "fluktuatif",
            "s_sideways": sideways,
            "s_vol_ratio": round(rv, 2) if rv is not None else 1.0,
            "s_freqspike": 0, "s_spring": 0,
            "s_closeabove": 1 if (lo and close > lo) else 0,
            "s_springlow": int(lo) if lo else 0,
            "s_resistance": int(hi) if hi else 0,
            "high_52": d.get("price_52_week_high"),
            "ret20": d.get("Perf.1M"),
            "nilai_harian": close * vol, "volatil": 0,
            "sumber": "TradingView scanner (pasar)",
        })
    return rows or None


def muat_semua():
    """Ambil KSEI + emiten; kembalikan (hasil, log)."""
    baris = []

    def say(m):
        baris.append(m)
        tulis_log(m)

    kodes = daftar_baca()
    say("Daftar pantau: %d emiten (%s)" % (len(kodes), ", ".join(kodes[:8]) + ("..." if len(kodes) > 8 else "")))

    say("Mengunduh kepemilikan KSEI...")
    ksei = cache_ambil("ksei", CACHE_KSEI, ambil_ksei, log_fn=say)
    if not ksei:
        return {"ok": False, "error": "Gagal mengambil data KSEI (cek koneksi internet).", "log": baris}, baris

    say("Mengunduh harga & fundamental (%d emiten)..." % len(kodes))
    saham = cache_ambil("emiten", CACHE_EMITEN, lambda: ambil_emiten(kodes), log_fn=say)
    if not saham:
        return {"ok": False, "error": "Gagal mengambil data harga/fundamental (Yahoo).", "log": baris}, baris

    say("Mengunduh broker & insider (SahamScope, watchlist)...")
    try:
        scope = cache_ambil("scope", CACHE_SCOPE, lambda: ambil_scope(kodes), log_fn=say)
    except Exception as e:  # noqa: BLE001
        tulis_log("scope gagal: %s" % e)
        say("SahamScope gagal — memakai cache lama bila ada.")
        scope = (_cache.get("scope") or {}).get("v")

    say("Menambah avg broker IndoPremier (SQLite)...")
    try:
        from datetime import timedelta as _td
        bs = load_mod("fetch_brokersum", "fetch-brokersum.py")
        hoy = datetime.now()
        aw, ak = (hoy - _td(days=30)).strftime("%Y-%m-%d"), hoy.strftime("%Y-%m-%d")
        usa, use = (hoy - _td(days=30)).strftime("%m/%d/%Y"), hoy.strftime("%m/%d/%Y")
        DBB = os.path.join(DATA_DIR, "saham.db")
        if not isinstance(scope, dict):
            scope = {}
        em = scope.setdefault("emiten", {})
        n_ip = 0
        for kode in kodes:
            try:
                if not bs.db_ada(DBB, kode, aw, ak):
                    snap = bs.ambil_satu(kode, usa, use)
                    snap["tgl_awal"], snap["tgl_akhir"] = aw, ak
                    bs.db_simpan(DBB, snap)
                    time.sleep(2.0)
                rows = bs.db_baca(DBB, kode, aw, ak)
                bB, bS, vB, vS = {}, {}, {}, {}
                for r in rows:
                    if r["sisi"] == "B":
                        bB[r["broker"]] = r["avg"]
                        vB[r["broker"]] = r["val"]
                    else:
                        bS[r["broker"]] = r["avg"]
                        vS[r["broker"]] = r["val"]
                if bB or bS:
                    ent = em.setdefault(kode, {"acc": {}, "insider": []})
                    acc = ent.setdefault("acc", {})
                    if not acc.get("top_buyers") and vB:
                        acc["top_buyers"] = [{"broker": b, "nval": v} for b, v in sorted(vB.items(), key=lambda kv: -kv[1])[:5]]
                    if not acc.get("top_sellers") and vS:
                        acc["top_sellers"] = [{"broker": b, "nval": v} for b, v in sorted(vS.items(), key=lambda kv: -kv[1])[:5]]
                    acc["avgB"], acc["avgS"], acc["sumber"] = bB, bS, "IP"
                    n_ip += 1
            except Exception as e:  # noqa: BLE001
                tulis_log("brokersum %s: %s" % (kode, str(e)[:100]))
        say("Avg broker IndoPremier: %d emiten." % n_ip)
    except Exception as e:  # noqa: BLE001
        tulis_log("brokersum gagal: %s" % e)

    say("Selesai. %d emiten siap." % len(saham))
    say("Memuat peta tema...")
    tema = muat_tema()
    say("Memuat fundamental gabungan...")
    fund = muat_fund(kodes)
    hasil = {
        "ok": True,
        "dibuat": datetime.now().astimezone().isoformat(timespec="seconds"),
        "jumlah": len(saham),
        "ksei": ksei,
        "saham": saham,
        "scope": scope or {},
        "tema": tema,
        "fund": fund,
        "direktori": _baca_json("broker-direktori.json"),
        "log": baris,
    }
    return hasil, baris


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _kirim(self, kode, tipe, data):
        if isinstance(data, str):
            data = data.encode("utf-8")
        self.send_response(kode)
        self.send_header("Content-Type", tipe)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _json(self, obj, kode=200):
        self._kirim(kode, "application/json; charset=utf-8",
                    json.dumps(obj, ensure_ascii=False))

    def do_GET(self):
        u = urlparse(self.path)
        jalur = u.path
        try:
            if jalur in ("/", "/index.html", "/screener-praktis.html"):
                path = os.path.join(WEB_DIR, HTML_FILE)
                if not os.path.exists(path):
                    return self._json({"ok": False, "error": "%s tidak ditemukan" % HTML_FILE}, 500)
                with open(path, "rb") as fh:
                    return self._kirim(200, "text/html; charset=utf-8", fh.read())
            if jalur == "/api/status":
                return self._json({"app": True, "watchlist": daftar_baca(),
                                   "bulan_ksei": bulan_ksei(),
                                   "ksei_cache": "ksei" in _cache, "emiten_cache": "emiten" in _cache})
            if jalur == "/api/config":
                return self._json({"ok": True, "config": {
                    "daftar_saham": daftar_baca(), "bulan_ksei": bulan_ksei()}})
            if jalur == "/api/download":
                q = parse_qs(u.query)
                hasil, _ = muat_semua()
                return self._json(hasil, 200 if hasil.get("ok") else 502)
            if jalur == "/api/scan":
                ksei = cache_ambil("ksei", CACHE_KSEI, ambil_ksei,
                                   log_fn=lambda m: tulis_log("ksei " + m))
                saham = cache_ambil("tv", CACHE_TV, ambil_tv,
                                    log_fn=lambda m: tulis_log("tv " + m))
                if not saham:
                    return self._json({"ok": False, "error": "Gagal mengambil data TradingView."}, 502)
                return self._json({
                    "ok": True, "jumlah": len(saham), "ksei": ksei or {}, "saham": saham,
                    "dibuat": datetime.now().astimezone().isoformat(timespec="seconds"),
                })
            if jalur == "/api/harian":
                q = parse_qs(u.query)
                tgl = (q.get("tanggal", [""])[0] or "").strip()
                d = baca_harian_terbaru(DATA_DIR, tgl or None)
                if not d:
                    return self._json({"ok": False, "error": "belum ada data harian."}, 404)
                return self._json({"ok": True, "tanggal": d.get("tanggal"),
                                   "jumlah": d.get("jumlah", len(d.get("saham", []))),
                                   "saham": d.get("saham", [])})
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
            if jalur == "/api/tema":
                tm = muat_tema()
                if not tm or not tm.get("tema"):
                    return self._json({"ok": False, "error": "belum ada data tema."}, 404)
                return self._json({"ok": True, "tema": tm})
            if jalur == "/api/fund":
                fu = muat_fund([])
                if not fu or not fu.get("emiten"):
                    return self._json({"ok": False, "error": "belum ada data fundamental gabungan."}, 404)
                return self._json({"ok": True, "fund": fu})
            if jalur == "/api/stock":
                q = parse_qs(u.query)
                kk = bersih_kode([q.get("kode", [""])[0]])
                if not kk:
                    return self._json({"ok": False, "error": "kode kosong."}, 400)
                kode = kk[0]
                recs = ambil_emiten([kode])
                if not recs:
                    return self._json({"ok": False, "error": "Gagal mengambil data %s." % kode}, 502)
                kmap = ((_cache.get("ksei") or {}).get("v") or {}).get("emiten", {}) or (_baca_json("ksei.json").get("emiten") or {})
                try:
                    sc = ambil_scope([kode], tulis_cache=False)
                    scopeEntry = (sc.get("emiten") or {}).get(kode, {})
                except Exception as e:  # noqa: BLE001
                    tulis_log("scope stock gagal: %s" % e)
                    scopeEntry = {}
                fundEntry = {}
                try:
                    base = _baca_json("fund-gabungan.json")
                    if kode not in (base.get("emiten") or {}):
                        ff = load_mod("fetch_fund", "fetch-fund-gabungan.py")
                        base = ff.ambil_semua([kode], log_fn=lambda m: tulis_log("fund " + m.strip() if m else ""))
                    fundEntry = (base.get("emiten") or {}).get(kode, {})
                except Exception as e:  # noqa: BLE001
                    tulis_log("fund stock gagal: %s" % e)
                ipmap = {}
                try:
                    bs = load_mod("fetch_brokersum", "fetch-brokersum.py")
                    from datetime import timedelta as _td
                    hoy = datetime.now()
                    aw, ak = (hoy - _td(days=30)).strftime("%Y-%m-%d"), hoy.strftime("%Y-%m-%d")
                    DBB = os.path.join(DATA_DIR, "saham.db")
                    if not bs.db_ada(DBB, kode, aw, ak):
                        usa, use = (hoy - _td(days=30)).strftime("%m/%d/%Y"), hoy.strftime("%m/%d/%Y")
                        snap = bs.ambil_satu(kode, usa, use)
                        snap["tgl_awal"], snap["tgl_akhir"] = aw, ak
                        bs.db_simpan(DBB, snap)
                        time.sleep(2.0)
                    bB, bS, vB, vS = {}, {}, {}, {}
                    for r in bs.db_baca(DBB, kode, aw, ak):
                        if r["sisi"] == "B":
                            bB[r["broker"]] = r["avg"]
                            vB[r["broker"]] = r["val"]
                        else:
                            bS[r["broker"]] = r["avg"]
                            vS[r["broker"]] = r["val"]
                    if bB or bS:
                        ipmap = {"avgB": bB, "avgS": bS,
                                 "topB": sorted(vB, key=lambda b: -vB[b])[:5],
                                 "topS": sorted(vS, key=lambda b: -vS[b])[:5]}
                except Exception as e:  # noqa: BLE001
                    tulis_log("ip stock gagal: %s" % e)
                if ipmap:
                    scopeEntry = dict(scopeEntry)
                    acc = dict(scopeEntry.get("acc") or {})
                    acc.update({"avgB": ipmap["avgB"], "avgS": ipmap["avgS"], "sumber": "IP"})
                    if not acc.get("top_buyers") and ipmap.get("topB"):
                        acc["top_buyers"] = [{"broker": b, "nval": 0} for b in ipmap["topB"]]
                    if not acc.get("top_sellers") and ipmap.get("topS"):
                        acc["top_sellers"] = [{"broker": b, "nval": 0} for b in ipmap["topS"]]
                    scopeEntry["acc"] = acc
                wajar = None
                try:
                    for t in (_baca_json("tema.json").get("tema") or []):
                        if kode in (t.get("emiten") or {}) and (t.get("wajar") or {}).get(kode):
                            wajar = t["wajar"][kode]
                            break
                except Exception:
                    pass
                return self._json({
                    "ok": True, "dibuat": datetime.now().astimezone().isoformat(timespec="seconds"),
                    "saham": recs[0], "k": kmap.get(kode, {}), "scopeEntry": scopeEntry,
                    "fundEntry": fundEntry, "wajar": wajar,
                })
            if jalur == "/api/direktori":
                dd = _baca_json("broker-direktori.json")
                return self._json({"ok": True, "direktori": dd})
            if jalur == "/favicon.ico":
                return self._kirim(204, "image/x-icon", b"")
            return self._json({"ok": False, "error": "rute tidak dikenal"}, 404)
        except Exception as e:  # noqa: BLE001
            tulis_log("ERROR %s: %s" % (jalur, e))
            return self._json({"ok": False, "error": str(e)}, 500)

    def do_POST(self):
        jalur = urlparse(self.path).path
        try:
            if jalur == "/api/training":
                n = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(n) if n else b"{}"
                data = json.loads(raw.decode("utf-8-sig"))
                teks = data.get("csv") or data.get("content") or ""
                nama = str(data.get("nama") or data.get("filename") or "").strip()
                if not teks.strip():
                    return self._json({"ok": False, "error": "isi CSV kosong."}, 400)
                # Validasi ringan: header wajib ada kode + harga/tanggal
                baris0 = teks.lstrip("\ufeff").splitlines()
                head = baris0[0].lower() if baris0 else ""
                if "kode" not in head:
                    return self._json({"ok": False, "error": "header CSV harus memuat kolom 'kode'."}, 400)
                # Nama file aman: huruf/angka/-/_ saja, wajib .csv
                import re as _re
                nama = _re.sub(r"[^A-Za-z0-9._-]", "_", nama) or "training.csv"
                if not nama.lower().endswith(".csv"):
                    nama += ".csv"
                if len(nama) > 64:
                    nama = nama[-64:]
                tdir = os.path.join(DATA_DIR, "training")
                os.makedirs(tdir, exist_ok=True)
                path = os.path.join(tdir, nama)
                # Tolak path traversal
                if os.path.abspath(path) != os.path.normpath(path) or \
                        not os.path.abspath(path).startswith(os.path.abspath(tdir)):
                    return self._json({"ok": False, "error": "nama file tidak valid."}, 400)
                with open(path, "w", encoding="utf-8-sig", newline="") as fh:
                    fh.write(teks if teks.endswith("\n") else teks + "\n")
                nbar = max(0, len([l for l in teks.splitlines() if l.strip()]) - 1)
                tulis_log("training tersimpan: %s (%d baris)" % (nama, nbar))
                return self._json({"ok": True, "nama": nama, "baris": nbar})
            if jalur != "/api/config":
                return self._json({"ok": False, "error": "rute tidak dikenal"}, 404)
            n = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(n) if n else b"{}"
            data = json.loads(raw.decode("utf-8-sig"))
            daftar = bersih_kode(data.get("daftar_saham"))
            try:
                bulan = max(2, min(48, int(data.get("bulan_ksei") or DEFAULT_BULAN_KSEI)))
            except (TypeError, ValueError):
                bulan = DEFAULT_BULAN_KSEI
            cfg = {"daftar_saham": daftar, "bulan_ksei": bulan}
            with open(CONFIG_FILE, "w", encoding="utf-8") as fh:
                json.dump(cfg, fh, ensure_ascii=False, indent=2)
            try:
                with open(WATCHLIST_FILE, "w", encoding="utf-8") as fh:
                    fh.write("# Daftar emiten (diedit dari aplikasi)\n")
                    for k in daftar:
                        fh.write(k + "\n")
            except OSError:
                pass
            _cache.pop("ksei", None)   # jumlah bulan berubah -> cache KSEI batal
            tulis_log("konfigurasi disimpan: %d emiten, %d bulan KSEI" % (len(daftar), bulan))
            return self._json({"ok": True, "config": cfg})
        except Exception as e:  # noqa: BLE001
            tulis_log("ERROR POST %s: %s" % (jalur, e))
            return self._json({"ok": False, "error": str(e)}, 500)


def pilih_port():
    for p in range(BASE_PORT, BASE_PORT + 12):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", p)) != 0:
                return p
    return None


def buka_browser(port):
    if os.environ.get("SCREENER_NO_BROWSER"):
        return
    time.sleep(1.0)
    webbrowser.open("http://127.0.0.1:%d/" % port)


def main():
    tulis_log("=" * 50)
    tulis_log("Aplikasi Screener dimulai")
    port = pilih_port()
    if port is None:
        tulis_log("Port tidak tersedia; buka peramban manual ke 127.0.0.1:%d" % BASE_PORT)
        webbrowser.open("http://127.0.0.1:%d/" % BASE_PORT)
        return 1
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    tulis_log("Melayani di http://127.0.0.1:%d/" % port)
    try:
        with open(PID_FILE, "w", encoding="utf-8") as fh:
            fh.write(str(os.getpid()))
        import atexit

        def _bersih():
            try:
                os.remove(PID_FILE)
            except OSError:
                pass
        atexit.register(_bersih)
    except OSError:
        pass
    threading.Thread(target=buka_browser, args=(port,), daemon=True).start()
    tulis_log("Screener Praktis berjalan di http://127.0.0.1:%d/" % port)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
