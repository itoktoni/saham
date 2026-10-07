#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch-data-idx.py
=================
Penarik data otomatis untuk "Screener Saham Indonesia — Alur Tunggal 7 Langkah".

Mengisi sendiri seluruh kolom yang dibutuhkan screener, termasuk perhitungan
turunan (BVPS, ekuitas, DER, rasio volume, deteksi sideways/spring) dan
pemeriksaan kualitas data.

SUMBER DATA
-----------
1. IDX resmi  : https://www.idx.co.id/primary/ListedCompany/GetCompanyProfiles
                -> KodeEmiten, NamaEmiten, Sektor, SubSektor  (962 emiten, tanpa API key)
2. Yahoo Finance (endpoint publik, tanpa API key)
                - /v8/finance/chart      -> harga harian, volume, high, low
                - /v10/finance/quoteSummary -> EPS, BVPS, ekuitas turunan, kas, utang,
                                               arus kas operasi, dividen, laba kuartalan
3. SEKI Bank Indonesia: https://www.bi.go.id/SEKI/tabel/TABEL1_25_1.xls
                - BI Rate (baris "Policy Rate"), seri bulanan 2017-sekarang.
                  Dibaca langsung dari format XLS (OLE2/BIFF) tanpa pustaka tambahan.

CATATAN PENTING
---------------
- Yahoo TIDAK menyediakan neraca & arus kas kuartalan untuk emiten IDX.
  Karena itu ekuitas diturunkan: ekuitas = BVPS x jumlah saham beredar.
- Data Yahoo bagus untuk emiten besar/mid, tetapi sering RUSAK untuk emiten
  kecil (contoh nyata: BVPS KRAS terbaca 0,035). Script ini memvalidasi dan
  menandai baris yang meragukan lewat kolom "sumber" + laporan di layar.
- Broker summary (konsentrasi Top Buyer) TIDAK tersedia di sumber gratis mana pun.
  Kolom s_topbuyer diisi 0 dan harus diisi manual dari RTI/Stockbit/IDX.

PEMAKAIAN
---------
  python fetch-data-idx.py --tickers BBCA,BBRI,TLKM,ANTM
  python fetch-data-idx.py --file daftar-saham.txt
  python fetch-data-idx.py --all                  # seluruh emiten IDX
  python fetch-data-idx.py --all --delay 2.5      # lebih sopan ke server

Butuh Python 3.8+. TANPA pustaka tambahan (hanya standard library).
"""

import argparse
import http.cookiejar
import json
import math
import os
import re
import shutil
import struct
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from collections import Counter
from datetime import datetime, timezone
from xml.etree import ElementTree as ET

# Ruang nama XML SpreadsheetML, dipakai saat membaca .xlsx laporan keuangan IDX.
XL_NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'

# Bila dijalankan langsung, taruh keluaran di folder data/ proyek (bukan cwd).
_BASE = os.path.dirname(os.path.abspath(__file__))
_DATA = os.path.join(os.path.dirname(_BASE), "data")
if os.path.isdir(_DATA):
    os.chdir(_DATA)

# ----------------------------------------------------------------------------
# Konfigurasi
# ----------------------------------------------------------------------------
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

YAHOO_MODULES = ",".join([
    "price", "summaryDetail", "defaultKeyStatistics", "financialData",
    "incomeStatementHistoryQuarterly", "incomeStatementHistory", "assetProfile",
])

IDX_PROFILE_URL = ("https://www.idx.co.id/primary/ListedCompany/"
                   "GetCompanyProfiles?start=0&length=1000")

CURL = shutil.which("curl") or shutil.which("curl.exe")

CSV_HEADER = [
    "kode", "nama", "sektor", "harga", "eps", "kuartal", "ekuitas", "saham", "laba",
    "der", "nilai_harian", "eps_trend", "dividen", "cagr", "cyclical", "volatil",
    "fcf", "wacc", "kas", "utang", "fcf_terminal", "g_terminal",
    "s_sideways", "s_vol_ratio", "s_freqspike", "s_topbuyer", "s_spring",
    "s_closeabove", "s_springlow", "s_resistance", "sumber",
    # 12 kolom tambahan -- HARUS tetap di akhir agar berkas 31 kolom yang lama
    # tetap bisa diimpor. Sebagian hanya terisi lewat jalur tempel JSON Key Stats;
    # hist_laba dan div_yield terisi juga lewat --laporan.
    "piotroski", "rs_rating", "altman_z", "interest_cov", "current_ratio",
    "quick_ratio", "roic", "roce", "ev_ebitda", "peg", "div_yield", "hist_laba",
    "ev_cfo", "ev_fcf", "cfo3", "sloan", "cash_badge",
    "peg_cfo", "cfo_cagr", "gross_margin", "margin_stabil", "capex_inten", "klasifikasi", "thowilz",
]

# Pemetaan sektor IDX-IC -> daftar sektor di dalam screener.
# Catatan: IDX-IC memakai nama "Barang Konsumen Primer" / "Barang Konsumen Non-Primer"
# (bukan "Konsumen Primer"), dan "Barang Perindustrian" untuk sebagian emiten lama.
SEKTOR_MAP = {
    "energi": "Energi",
    "barang baku": "Barang Baku",
    "perindustrian": "Perindustrian",
    "barang perindustrian": "Perindustrian",
    "barang konsumen primer": "Konsumer Primer",
    "konsumen primer": "Konsumer Primer",
    "barang konsumen non-primer": "Konsumer Non-Primer",
    "barang konsumen non primer": "Konsumer Non-Primer",
    "konsumen non-primer": "Konsumer Non-Primer",
    "kesehatan": "Kesehatan",
    "keuangan": "Keuangan",
    "properti & real estat": "Properti",
    "properti dan real estat": "Properti",
    "teknologi": "Teknologi",
    "infrastruktur": "Infrastruktur",
    "telekomunikasi": "Telekomunikasi",
    "transportasi & logistik": "Transportasi",
    "transportasi dan logistik": "Transportasi",
}
SEKTOR_CYCLICAL = {"Energi", "Barang Baku", "Perindustrian", "Konsumer Non-Primer",
                   "Properti", "Transportasi"}

# Daftar sektor yang dikenali screener (harus sama persis dengan SEKTOR di HTML)
SEKTOR_SAH = ["Energi", "Barang Baku", "Perindustrian", "Konsumer Primer",
              "Konsumer Non-Primer", "Kesehatan", "Keuangan", "Properti",
              "Teknologi", "Infrastruktur", "Telekomunikasi", "Transportasi", "Utilitas"]


def normalisasi_sektor(raw):
    """Ubah nama sektor apa pun (IDX-IC / Yahoo / bahasa Inggris) ke sektor screener.

    Kalau tidak dikenali, kembalikan "" supaya pemanggil bisa jatuh ke cadangan,
    bukan mengirim nama asing yang akan ditolak importer HTML.
    """
    if not raw:
        return ""
    key = str(raw).strip().lower()
    if key in SEKTOR_MAP:
        return SEKTOR_MAP[key]
    if key in SEKTOR_EN_MAP:
        return SEKTOR_EN_MAP[key]
    # Cocokkan langsung dengan daftar resmi (tanpa peduli huruf besar/kecil)
    for s in SEKTOR_SAH:
        if key == s.lower():
            return s
    # Tebakan terakhir berbasis kata kunci, urut dari paling spesifik
    if "konsumen non" in key or "consumer cyclical" in key:
        return "Konsumer Non-Primer"
    if "konsumen primer" in key or "consumer defensive" in key:
        return "Konsumer Primer"
    for kata, sektor in (("energi", "Energi"), ("tambang", "Barang Baku"),
                         ("baku", "Barang Baku"), ("kimia", "Barang Baku"),
                         ("industri", "Perindustrian"), ("kesehatan", "Kesehatan"),
                         ("farmasi", "Kesehatan"), ("keuangan", "Keuangan"),
                         ("bank", "Keuangan"), ("properti", "Properti"),
                         ("real estat", "Properti"), ("teknologi", "Teknologi"),
                         ("telekomunikasi", "Telekomunikasi"),
                         ("infrastruktur", "Infrastruktur"),
                         ("transportasi", "Transportasi"), ("logistik", "Transportasi"),
                         ("utilitas", "Utilitas")):
        if kata in key:
            return sektor
    return ""

# Cadangan bila IDX tidak bisa diakses: sektor bahasa Inggris dari Yahoo
SEKTOR_EN_MAP = {
    "basic materials": "Barang Baku",
    "energy": "Energi",
    "industrials": "Perindustrian",
    "consumer defensive": "Konsumer Primer",
    "consumer cyclical": "Konsumer Non-Primer",
    "healthcare": "Kesehatan",
    "financial services": "Keuangan",
    "real estate": "Properti",
    "technology": "Teknologi",
    "communication services": "Infrastruktur",
    "utilities": "Utilitas",
}


# ----------------------------------------------------------------------------
# Utilitas
# ----------------------------------------------------------------------------
def log(msg=""):
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        print(msg.encode("ascii", "replace").decode("ascii"), flush=True)


def setup_stdout():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def num(v, default=0.0):
    """Ambil angka mentah dari format Yahoo ({'raw': x}) atau langsung."""
    if v is None:
        return default
    if isinstance(v, dict):
        v = v.get("raw")
    if v is None:
        return default
    try:
        f = float(v)
    except (TypeError, ValueError):
        return default
    if f != f or f in (float("inf"), float("-inf")):  # NaN / inf
        return default
    return f


def clean(v, default=0.0):
    """Angka bersih untuk CSV: bulatkan bila besar, jaga presisi bila kecil."""
    x = num(v, default)
    if abs(x) >= 1000:
        return int(round(x))
    return round(x, 4)


def compute_ev(market_cap, total_debt, total_cash):
    """EV = MarketCap + TotalDebt - TotalCash. None bila MarketCap <= 0."""
    try:
        mc = float(market_cap or 0)
        db = float(total_debt or 0)
        cs = float(total_cash or 0)
    except (TypeError, ValueError):
        return None
    if mc <= 0:
        return None
    return mc + db - cs


def compute_cash_quality(hist, total_assets, sektor):
    """hist: [(tahun, laba, cfo)] urut bebas. Return cfo3/sloan/badge/alasan."""
    pts = sorted([(t, l, c) for t, l, c in (hist or []) if t is not None], key=lambda p: p[0])
    if len(pts) < 3:
        return {"cfo3": 0, "sloan": None, "badge": "-", "alasan": "riwayat <3 tahun"}
    last3 = pts[-3:]
    cfo3 = 0
    if all((c is not None and l is not None and c > 0 and c > l) for _, l, c in last3):
        cfo3 = 1
    sloan = None
    try:
        _, ni, cfo = pts[-1]
        ta = float(total_assets or 0)
        if ni is not None and cfo is not None and ta > 0:
            sloan = (float(ni) - float(cfo)) / ta
    except (TypeError, ValueError):
        sloan = None
    # streak sloan 2 tahun
    streak = 0
    for _, l, c in pts[-2:]:
        try:
            ta = float(total_assets or 0)
            s = (float(l) - float(c)) / ta if (l is not None and c is not None and ta > 0) else None
        except (TypeError, ValueError):
            s = None
        if s is not None and s > 0.05:
            streak += 1
    is_bank = (sektor or "").strip().lower() == "keuangan"
    if sloan is not None and (sloan > 0.10 or streak >= 2) and not is_bank:
        return {"cfo3": cfo3, "sloan": round(sloan, 4), "badge": "Kill", "alasan": "akrual tinggi (Sloan %.2f)" % sloan}
    if cfo3 == 0 or (sloan is not None and sloan > 0.05):
        why = "CFO tidak > laba 3thn" if cfo3 == 0 else ("akrual waspada (bank)" if is_bank else "akrual waspada")
        return {"cfo3": cfo3, "sloan": round(sloan, 4) if sloan is not None else None, "badge": "Watchlist", "alasan": why}
    return {"cfo3": cfo3, "sloan": round(sloan, 4) if sloan is not None else None, "badge": "Lolos", "alasan": "CFO selaras laba"}


def compute_margin_quality(margins):
    """margins: fraksi laba kotor per tahun, urut bebas. Stabil bila >=3 thn,
    semua >0, dan rentang <=8pp (proksi pricing power Thowilz)."""
    ms = [float(x) for x in (margins or []) if x is not None]
    if not ms:
        return {"gross_margin": None, "margin_stabil": 0}
    stabil = 0
    if len(ms) >= 3 and min(ms) > 0 and (max(ms) - min(ms)) <= 0.08:
        stabil = 1
    return {"gross_margin": round(ms[-1] * 100.0, 1), "margin_stabil": stabil}


def compute_cfo_cagr(hist_cf):
    """CAGR CFO dari [(tahun, laba, cfo)] urut bebas. None bila <2 titik atau
    titik awal/akhir tidak positif."""
    pts = sorted([(t, c) for t, _, c in (hist_cf or []) if t is not None], key=lambda p: p[0])
    if len(pts) < 2:
        return None
    awal, akhir = pts[0][1], pts[-1][1]
    tahun = pts[-1][0] - pts[0][0]
    if awal is None or akhir is None or awal <= 0 or akhir <= 0 or tahun <= 0:
        return None
    return round((akhir / awal) ** (1.0 / tahun) - 1.0, 4)


def compute_peg_cfo(ev_cfo, cagr):
    """PEG-CFO = EV/CFO dibagi pertumbuhan CFO (%). Ambang sama seperti PEG
    Thowilz: <1.0 murah, >1.5 mahal. None bila tak terhitung."""
    try:
        ev = float(ev_cfo) if ev_cfo is not None else None
        g = float(cagr) if cagr is not None else None
    except (TypeError, ValueError):
        return None
    if ev is None or g is None or ev <= 0 or g <= 0:
        return None
    return round(ev / (g * 100.0), 2)


def compute_klasifikasi(sektor, cagr_earn, dividen, der, laba_hist, net_cash_mcap):
    """Satu label Thowilz. Preseden: Turnaround > AssetPlay > FastGrowing >
    Cyclical > Stalwart > '-'. cagr_earn dalam persen (mis. 25.0)."""
    lh = sorted([(t, v) for t, v in (laba_hist or []) if t is not None], key=lambda p: p[0])
    if len(lh) >= 2 and lh[-2][1] is not None and lh[-1][1] is not None:
        if lh[-2][1] < 0 < lh[-1][1]:
            return "Turnaround"
    if net_cash_mcap is not None and net_cash_mcap > 0.3:
        return "AssetPlay"
    if cagr_earn is not None and cagr_earn > 20:
        return "FastGrowing"
    if (sektor or "") in SEKTOR_CYCLICAL:
        return "Cyclical"
    try:
        d = float(der or 0)
    except (TypeError, ValueError):
        d = 99.0
    if dividen == 1 and d < 1:
        return "Stalwart"
    return "-"


def compute_thowilz(ev_cfo, peg_cfo, badge, margin_stabil, klasifikasi, hist_years, spring, sideways):
    """Skor komposit 0-100. Valuasi 35 + Kualitas 35 + Tesis 15 + Timing 15.
    Timing memakai sinyal chart yang sudah ada (spring ~ SOS, sideways ~ serapan)."""
    try:
        ev = float(ev_cfo) if ev_cfo not in (None, "") else None
    except (TypeError, ValueError):
        ev = None
    v = 25 if (ev is not None and ev <= 10) else (18 if (ev is not None and ev <= 15) else (10 if (ev is not None and ev <= 20) else (4 if (ev is not None and ev > 0) else 0)))
    try:
        pg = float(peg_cfo) if peg_cfo not in (None, "") else None
    except (TypeError, ValueError):
        pg = None
    v += 10 if (pg is not None and pg < 1) else (5 if (pg is not None and pg < 1.5) else 0)
    k = {"Lolos": 28, "Watchlist": 12, "Kill": 0}.get(badge, 10) + (7 if margin_stabil else 0)
    t = (10 if klasifikasi not in (None, "", "-") else 3) + (5 if (hist_years or 0) >= 4 else 0)
    m = 15 if spring else (10 if sideways else 5)
    total = min(100, v + k + t + m)
    return {"thowilz": int(total), "rincian": {"valuasi": v, "kualitas": k, "tesis": t, "timing": m}}


# ----------------------------------------------------------------------------
# HTTP
# ----------------------------------------------------------------------------
class Fetcher:
    def __init__(self, delay=1.5, retries=3):
        self.delay = delay
        self.retries = retries
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar))
        self.crumb = None
        self.count = 0
        self.used_curl = False

    def _curl_get(self, url, headers):
        """Transport cadangan: sebagian server (mis. IDX di belakang Cloudflare)
        menolak urllib karena sidik jari TLS, tetapi menerima curl."""
        if not CURL:
            return None
        cmd = [CURL, "-s", "-L", "-m", "40"]
        ua = headers.get("User-Agent", UA) if headers else UA
        cmd += ["-A", ua]
        for k, v in (headers or {}).items():
            if k.lower() == "user-agent":
                continue
            cmd += ["-H", "%s: %s" % (k, v)]
        cmd.append(url)
        try:
            p = subprocess.run(cmd, capture_output=True, timeout=70)
            if p.returncode != 0 or not p.stdout:
                return None
            return p.stdout
        except Exception:
            return None

    def _decode(self, body, expect_json):
        if expect_json:
            try:
                return json.loads(body.decode("utf-8", "replace"))
            except json.JSONDecodeError:
                return None
        return body

    def get(self, url, headers=None, expect_json=True, quiet_429=False):
        h = {"User-Agent": UA,
             "Accept": "application/json, text/javascript, */*; q=0.01",
             "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7"}
        if headers:
            h.update(headers)
        last_err = None
        for attempt in range(self.retries + 1):
            try:
                req = urllib.request.Request(url, headers=h)
                with self.opener.open(req, timeout=30) as r:
                    body = r.read()
                self.count += 1
                return self._decode(body, expect_json)
            except urllib.error.HTTPError as e:
                last_err = "HTTP %s" % e.code
                if e.code == 429:
                    if not quiet_429:
                        log("    [rate limit] tunggu %ds lalu coba lagi..." % (15 * (attempt + 1)))
                    time.sleep(15 * (attempt + 1))
                    continue
                if e.code in (401, 403) and "yahoo" in url and attempt < self.retries:
                    self.crumb = None          # crumb kedaluwarsa -> ambil ulang
                    self._login()
                    time.sleep(2)
                    continue
                break
            except Exception as e:  # noqa: BLE001
                last_err = str(e)
                time.sleep(2)

        # --- cadangan curl ---
        body = self._curl_get(url, h)
        if body:
            out = self._decode(body, expect_json)
            if out is not None:
                self.count += 1
                if not self.used_curl:
                    self.used_curl = True
                    log("    [i] memakai transport curl untuk %s"
                        % urllib.parse.urlsplit(url).netloc)
                return out
        log("    [gagal] %s" % last_err)
        return None

    # -- Yahoo: cookie + crumb ------------------------------------------------
    def _login(self):
        try:
            self.get("https://fc.yahoo.com", expect_json=False)
        except Exception:
            pass
        time.sleep(1.0)
        try:
            self.get("https://finance.yahoo.com/quote/AAPL", expect_json=False)
        except Exception:
            pass
        time.sleep(1.0)
        raw = self.get("https://query1.finance.yahoo.com/v1/test/getcrumb",
                       expect_json=False)
        if raw:
            try:
                self.crumb = raw.decode("utf-8", "replace").strip()
            except Exception:
                self.crumb = None
        return self.crumb

    def yahoo(self, path):
        if not self.crumb:
            self._login()
        sep = "&" if "?" in path else "?"
        url = "https://query2.finance.yahoo.com" + path + sep + "crumb=" + \
              urllib.parse.quote(self.crumb or "")
        return self.get(url)


# ----------------------------------------------------------------------------
# 1. Profil emiten dari IDX
# ----------------------------------------------------------------------------
def load_idx_profiles(f, cache_file="idx-profil.json", max_age_days=7, use_cache=True):
    if use_cache and os.path.exists(cache_file):
        age = (time.time() - os.path.getmtime(cache_file)) / 86400.0
        if age < max_age_days:
            try:
                with open(cache_file, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                # Cache menyimpan hasil pemetaan versi lama. Petakan ulang saat
                # dibaca supaya perbaikan SEKTOR_MAP langsung berlaku tanpa
                # menunggu cache kedaluwarsa (dulu ini membuat sektor MEJA salah).
                for v in data.values():
                    if isinstance(v, dict):
                        v["sektor"] = normalisasi_sektor(v.get("sektor"))
                log("  Profil IDX dari cache: %d emiten (umur %.1f hari)"
                    % (len(data), age))
                return data
            except Exception:
                pass

    log("  Mengambil profil emiten dari IDX...")
    d = f.get(IDX_PROFILE_URL, headers={
        "Referer": "https://www.idx.co.id/id/perusahaan-tercatat/profil-perusahaan-tercatat",
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json, text/javascript, */*; q=0.01",
    })
    if not d or "data" not in d:
        log("  [!] IDX tidak bisa diakses. Sektor akan diambil dari Yahoo sebagai cadangan.")
        return {}

    out = {}
    for r in (d.get("data") or []):
        kode = (r.get("KodeEmiten") or "").strip().upper()
        if not kode:
            continue
        sektor_raw = (r.get("Sektor") or "").strip()
        out[kode] = {
            "nama": (r.get("NamaEmiten") or "").strip(),
            "sektor": normalisasi_sektor(sektor_raw),
            "subsektor": (r.get("SubSektor") or "").strip(),
            "papan": (r.get("PapanPencatatan") or "").strip(),
        }
    if out:
        log("  Profil IDX diterima: %d emiten (dari %s total)"
            % (len(out), d.get("recordsFiltered")))
        try:
            with open(cache_file, "w", encoding="utf-8") as fh:
                json.dump(out, fh, ensure_ascii=False)
            log("  Tersimpan ke cache: %s" % cache_file)
        except Exception:
            pass
    return out


# ----------------------------------------------------------------------------
# 2. Yahoo: fundamental + harga
# ----------------------------------------------------------------------------
def fetch_fundamental(f, kode):
    d = f.yahoo("/v10/finance/quoteSummary/%s.JK?modules=%s" % (kode, YAHOO_MODULES))
    if not d:
        return None
    res = ((d.get("quoteSummary") or {}).get("result") or [None])[0]
    return res


def fetch_chart(f, kode, rng="6mo", suffix=".JK"):
    """Riwayat harian dari Yahoo. `suffix` dikosongkan untuk indeks (^JKSE)."""
    d = f.get("https://query1.finance.yahoo.com/v8/finance/chart/%s%s"
              "?range=%s&interval=1d" % (kode, suffix, rng))
    if not d:
        return None
    res = ((d.get("chart") or {}).get("result") or [None])[0]
    if not res:
        return None
    q = ((res.get("indicators") or {}).get("quote") or [{}])[0]
    ts = res.get("timestamp") or []
    close, high, low, vol = [], [], [], []
    for i in range(len(ts)):
        c = (q.get("close") or [None] * len(ts))[i]
        if c is None:
            continue
        close.append(float(c))
        high.append(num((q.get("high") or [0] * len(ts))[i], float(c)))
        low.append(num((q.get("low") or [0] * len(ts))[i], float(c)))
        vol.append(num((q.get("volume") or [0] * len(ts))[i], 0.0))
    return {"close": close, "high": high, "low": low, "volume": vol,
            "meta": res.get("meta") or {}}


def hitung_swing(ch):
    """Turunkan 5 dari 6 input bandarmology dari riwayat harga."""
    out = {"s_sideways": 0, "s_vol_ratio": 1.0, "s_freqspike": 0, "s_spring": 0,
           "s_closeabove": 0, "s_springlow": 0, "s_resistance": 0, "volatil": 0}
    if not ch or len(ch["close"]) < 25:
        return out
    cl, hi, lo, vo = ch["close"], ch["high"], ch["low"], ch["volume"]
    n = len(cl)

    w = 20
    sup = min(lo[-w:])
    res = max(hi[-w:])
    out["s_springlow"] = int(round(sup))
    out["s_resistance"] = int(round(res))

    c20 = cl[-w:]
    lebar20 = (max(c20) / min(c20) - 1.0) if min(c20) > 0 else 1.0
    rng6 = (max(cl) / min(cl) - 1.0) if min(cl) > 0 else 1.0
    posisi = (cl[-1] - min(cl)) / (max(cl) - min(cl)) if max(cl) > min(cl) else 1.0
    out["s_sideways"] = 1 if (lebar20 < 0.12 and posisi < 0.40) else 0

    v20 = vo[-21:-1] or vo[-20:]
    avg = sum(v20) / len(v20) if v20 else 0
    out["s_vol_ratio"] = round(vo[-1] / avg, 2) if avg > 0 else 1.0

    spike = 0
    for i in range(max(1, n - 30), n):
        va = sum(vo[max(0, i - 20):i]) / max(1, len(vo[max(0, i - 20):i]))
        if va <= 0 or cl[i - 1] <= 0:
            continue
        chg = abs(cl[i] / cl[i - 1] - 1.0)
        if vo[i] > 3 * va and chg < 0.02:
            spike = 1
            break
    out["s_freqspike"] = spike

    sup_prev = min(lo[-30:-10]) if n >= 30 else sup
    for i in range(max(1, n - 10), n):
        if lo[i] < sup_prev * 0.995 and cl[i] > sup_prev:
            out["s_spring"] = 1
            break
    out["s_closeabove"] = 1 if cl[-1] > sup else 0
    out["volatil"] = 1 if rng6 > 0.60 else 0
    return out


# ----------------------------------------------------------------------------
# 3. Perakitan record + validasi kualitas
# ----------------------------------------------------------------------------
def build_record(kode, prof, fund, ch, args):
    m = ((fund or {}).get("price") or {})
    sd = ((fund or {}).get("summaryDetail") or {})
    ks = ((fund or {}).get("defaultKeyStatistics") or {})
    fd = ((fund or {}).get("financialData") or {})
    iq = (((fund or {}).get("incomeStatementHistoryQuarterly") or {})
          .get("incomeStatementHistory") or [])
    ih = (((fund or {}).get("incomeStatementHistory") or {})
          .get("incomeStatementHistory") or [])
    margins = []
    for y in sorted(ih, key=lambda z: num((z.get("endDate") or {}).get("raw"), 0)):
        rev = num(y.get("totalRevenue"), None)
        gp = num(y.get("grossProfit"), None)
        if rev is not None and rev > 0 and gp is not None:
            margins.append(gp / rev)
    mq = compute_margin_quality(margins[-4:])

    harga = num(m.get("regularMarketPrice")) or num(sd.get("previousClose"))
    if harga <= 0 and ch and ch["close"]:
        harga = ch["close"][-1]

    shares = num(ks.get("sharesOutstanding")) or num(ks.get("impliedSharesOutstanding"))
    bvps = num(ks.get("bookValue"))
    eps = num(ks.get("trailingEps"))
    laba = num(ks.get("netIncomeToCommon"))

    if laba == 0 and iq:
        vals = [num(x.get("netIncome")) for x in iq[:4]]
        if len(vals) == 4 and all(v != 0 for v in vals):
            laba = sum(vals)

    ekuitas = bvps * shares if (bvps > 0 and shares > 0) else 0.0

    if eps == 0 and shares > 0 and laba != 0:
        eps = laba / shares

    utang = num(fd.get("totalDebt"))
    kas = num(fd.get("totalCash"))
    der = (utang / ekuitas) if ekuitas > 0 else 0.0

    mcap = harga * shares if (harga > 0 and shares > 0) else 0.0
    ev = compute_ev(mcap, utang, kas)
    ocf = num(fd.get("operatingCashflow"), None)
    fcf_y = num(fd.get("freeCashflow"), None)
    ev_cfo = round(ev / ocf, 2) if (ev is not None and ocf is not None and ocf > 0) else None
    ev_fcf = round(ev / fcf_y, 2) if (ev is not None and fcf_y is not None and fcf_y > 0) else None
    capex_inten = (round((ocf - fcf_y) / ocf, 3)
                   if (ocf is not None and fcf_y is not None and ocf > 0) else None)

    avgvol = (num(sd.get("averageVolume10days")) or num(sd.get("averageVolume"))
              or (sum(ch["volume"][-20:]) / max(1, len(ch["volume"][-20:])) if ch else 0))
    nilai_harian = harga * avgvol

    div_yield = num(sd.get("dividendYield"))
    div_rate = num(sd.get("dividendRate"))
    dividen = 1 if (div_yield > 0 or div_rate > 0) else 0

    growth = num(fd.get("earningsGrowth"), None)
    if growth is None:
        eps_trend, cagr = "fluktuatif", 0.0
    else:
        eps_trend = "up" if growth > 0.05 else ("down" if growth < -0.05 else "fluktuatif")
        cagr = round(growth * 100.0, 2)

    sektor = (prof or {}).get("sektor") or ""
    ap = (fund or {}).get("assetProfile") or {}
    if not sektor and ap.get("sector"):
        sektor = normalisasi_sektor(ap.get("sector"))
    if not sektor:
        sektor = "Energi"  # cadangan terakhir agar baris tetap bisa diimpor
    cyclical = 1 if sektor in SEKTOR_CYCLICAL else 0

    bars_30 = []
    if ch and ch.get("close") and ch.get("volume"):
        n = min(30, len(ch["close"]), len(ch["volume"]))
        bars_30 = [[int(round(ch["close"][-n + i])), int(ch["volume"][-n + i] or 0)]
                   for i in range(n)]
    sw = hitung_swing(ch)
    volatil = sw.pop("volatil")
    beta = num(ks.get("beta"))
    if 0 < beta < 3 and beta > 1.5:
        volatil = 1

    wacc = 10.0 + (1.5 if cyclical else 0) + (2.0 if der > 1 else 0) + (1.0 if volatil else 0)

    cagr_earn = cagr if growth is not None else None
    net_cash_mcap = ((kas - utang) / mcap) if mcap > 0 else None
    klas = compute_klasifikasi(sektor, cagr_earn, dividen, der, [], net_cash_mcap)
    tw = compute_thowilz(ev_cfo, None, "-", mq["margin_stabil"], klas, 0,
                         sw["s_spring"], sw["s_sideways"])

    # ---- Validasi kualitas ------------------------------------------------
    catatan = []
    if harga <= 0:
        catatan.append("harga kosong")
    if ekuitas <= 0:
        catatan.append("ekuitas tidak bisa diturunkan (BVPS kosong)")
    elif ekuitas < 1e9:
        catatan.append("ekuitas sangat kecil - BVPS diduga salah")
    if eps and shares and laba and abs(eps * shares - laba) / abs(laba) > 0.25:
        catatan.append("EPS x saham tidak sinkron dengan laba bersih")
    if ekuitas > 0 and harga > 0 and shares > 0:
        pbv = harga * shares / ekuitas
        if pbv > 40 or pbv < 0.02:
            catatan.append("PBV tidak wajar (%.2fx)" % pbv)
    if laba == 0:
        catatan.append("laba bersih kosong")
    if num(fd.get("operatingCashflow")) < 0 and sektor == "Keuangan":
        catatan.append("arus kas operasi negatif (lazim tidak akurat untuk bank)")

    if not catatan:
        kualitas = "kualitas baik"
    elif len(catatan) <= 1:
        kualitas = "perlu dicek: " + catatan[0]
    else:
        kualitas = "data meragukan (%d masalah)" % len(catatan)

    sumber = "Yahoo Finance + IDX - %s" % kualitas

    return {
        "kode": kode,
        "nama": (prof or {}).get("nama") or (m.get("longName") or m.get("shortName") or kode),
        "sektor": sektor or "Energi",
        "harga": clean(harga),
        "eps": clean(eps),
        "kuartal": 4,
        "ekuitas": clean(ekuitas),
        "saham": clean(shares),
        "laba": clean(laba),
        "der": clean(der),
        "nilai_harian": clean(nilai_harian),
        "eps_trend": eps_trend,
        "dividen": dividen,
        "cagr": cagr,
        "cyclical": cyclical,
        "volatil": volatil,
        "fcf": clean(fd.get("operatingCashflow")),
        "wacc": round(wacc, 2),
        "kas": clean(kas),
        "utang": clean(utang),
        "fcf_terminal": 0,
        "g_terminal": 2.5,
        "s_sideways": sw["s_sideways"],
        "s_vol_ratio": sw["s_vol_ratio"],
        "s_freqspike": sw["s_freqspike"],
        "s_topbuyer": 0,
        "s_spring": sw["s_spring"],
        "s_closeabove": sw["s_closeabove"],
        "s_springlow": sw["s_springlow"],
        "s_resistance": sw["s_resistance"],
        "bars_30": bars_30,
        # Screener mengharapkan persen (mis. 2.5 berarti 2,5%). Yahoo kadang
        # memberi pecahan (0.025), jadi nilai di bawah 1 dianggap pecahan.
        "div_yield": round(div_yield * 100.0, 2) if 0 < div_yield < 1 else round(div_yield, 2),
        "sumber": sumber,
        "_catatan": catatan,
        "ev_cfo": ev_cfo,
        "ev_fcf": ev_fcf,
        "cfo3": 0,
        "sloan": None,
        "cash_badge": "-",
        "gross_margin": mq["gross_margin"],
        "margin_stabil": mq["margin_stabil"],
        "peg_cfo": None,
        "cfo_cagr": None,
        "capex_inten": capex_inten,
        "klasifikasi": klas,
        "thowilz": tw["thowilz"],
    }


# ----------------------------------------------------------------------------
# Regime pasar (Langkah 1: Regime Makro)
#
# Yang bisa diotomatiskan dan yang tidak, supaya tidak menyesatkan:
#   kuadran siklus  -> OTOMATIS dari riwayat IHSG (Yahoo ^JKSE)
#   likuiditas      -> OTOMATIS dari nilai transaksi harian IDX
#   kekuatan sektor -> SEMI, diagregasi dari emiten yang ikut ditarik
#   suku bunga BI   -> MANUAL (tidak ada sumber gratis yang stabil)
#   toleransi risiko-> MANUAL (selera pribadi)
# ----------------------------------------------------------------------------
IHSG_SIMBOL = "^JKSE"
IDX_INDEX_URL = "https://www.idx.co.id/primary/TradingSummary/GetIndexSummary"
IDX_STOCK_URL = "https://www.idx.id/primary/TradingSummary/GetStockSummary"

# BI Rate di-scrape dari tabel resmi SEKI Bank Indonesia (bukan BPS: API-nya
# diblokir firewall, dan halaman web BI merender angkanya lewat JavaScript
# sehingga tidak bisa dibaca tanpa browser). Berkas XLS ini adalah sumber
# yang sama persis dengan yang dipublikasikan BI di halaman Statistik.
SEKI_BIRATE_URL = "https://www.bi.go.id/SEKI/tabel/TABEL1_25_1.xls"
# Label baris suku bunga kebijakan sepanjang sejarah tabel SEKI. "Policy Rate"
# dipakai sejak penggantian nama BI7DRR -> BI-Rate (21 Des 2023).
LABEL_BI_RATE = ("policy rate", "bi rate", "bi-rate",
                 "bi 7day repo rate", "bi 7-day reverse repo rate")
BULAN_EN = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
            "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}


def rata(a):
    a = [x for x in a if x is not None]
    return sum(a) / len(a) if a else None


def return_pct(bars, n):
    """Return n hari ke belakang dalam persen."""
    if len(bars) < n + 1 or not bars[-n - 1]:
        return None
    return (bars[-1] / bars[-n - 1] - 1) * 100.0


def hitung_regime(close):
    """Tentukan kuadran siklus dari riwayat penutupan IHSG.

    Aturan disusun berurutan dari kondisi paling ekstrem. Setiap keputusan
    disertai alasan yang bisa dibaca pengguna, bukan sekadar satu label.
    """
    if not close or len(close) < 30:
        return None
    last = close[-1]
    ma50 = rata(close[-50:]) if len(close) >= 50 else rata(close)
    ma200 = rata(close[-200:]) if len(close) >= 200 else None
    hi = max(close)
    lo = min(close)
    r1 = return_pct(close, 21)
    r3 = return_pct(close, 63)
    r6 = return_pct(close, 126)
    jarak_puncak = (last / hi - 1) * 100.0 if hi else 0.0
    jarak_dasar = (last / lo - 1) * 100.0 if lo else 0.0
    di_atas_ma50 = ma50 is not None and last > ma50
    di_atas_ma200 = ma200 is not None and last > ma200

    alasan = []
    if r3 is None:
        kuadran = "slowdown"
        alasan.append("riwayat harga terlalu pendek untuk menilai tren")
    elif r3 < -10 and not di_atas_ma50:
        kuadran = "bust"
        alasan.append("turun %.1f%% dalam 3 bulan dan masih di bawah MA50" % r3)
    elif r3 < 0 and not di_atas_ma50:
        kuadran = "slowdown"
        alasan.append("tren 3 bulan negatif (%.1f%%) dan harga di bawah MA50" % r3)
    elif r3 > 0 and jarak_puncak > -8:
        kuadran = "overheat"
        alasan.append("naik %.1f%% dalam 3 bulan dan sudah dekat puncak 52 minggu" % r3)
    elif r3 > 0 and jarak_puncak <= -8:
        kuadran = "recovery"
        alasan.append("naik %.1f%% dalam 3 bulan dari posisi masih %.1f%% di bawah puncak"
                      % (r3, abs(jarak_puncak)))
    else:
        kuadran = "slowdown"
        alasan.append("tidak ada pola yang tegas; dianggap melemah")

    if di_atas_ma50:
        alasan.append("harga di atas MA50 (tren pendek membaik)")
    else:
        alasan.append("harga di bawah MA50 (tren pendek masih lemah)")
    if ma200 is not None:
        alasan.append("harga %s MA200" % ("di atas" if di_atas_ma200 else "di bawah"))

    return {
        "tutup": round(last, 2), "ma50": round(ma50, 2) if ma50 else None,
        "ma200": round(ma200, 2) if ma200 else None,
        "tinggi_52m": round(hi, 2), "rendah_52m": round(lo, 2),
        "jarak_puncak": round(jarak_puncak, 1), "jarak_dasar": round(jarak_dasar, 1),
        "r1": round(r1, 2) if r1 is not None else None,
        "r3": round(r3, 2) if r3 is not None else None,
        "r6": round(r6, 2) if r6 is not None else None,
        "di_atas_ma50": bool(di_atas_ma50), "di_atas_ma200": bool(di_atas_ma200),
        "hari": len(close), "saran_kuadran": kuadran, "alasan": alasan,
    }


def hitung_likuiditas(f, hari=30, delay=0.4):
    """Rata-rata nilai transaksi harian IDX, dibandingkan hari terakhir.

    Ini satu-satunya cara gratis untuk menilai likuiditas pasar secara objektif;
    Yahoo tidak menyediakan nilai transaksi untuk indeks.
    """
    from datetime import date, timedelta
    nilai, freq, tgl = [], [], []
    d = date.today()
    dicoba = 0
    while len(nilai) < hari and dicoba < hari * 3:
        dicoba += 1
        ds = d.strftime("%Y%m%d")
        j = f.get("%s?date=%s" % (IDX_INDEX_URL, ds), headers={
            "Referer": "https://www.idx.co.id/",
            "X-Requested-With": "XMLHttpRequest",
        })
        d -= timedelta(days=1)
        if not j:
            continue
        rows = j.get("data") if isinstance(j, dict) else None
        if not rows:
            continue
        comp = None
        for r in rows:
            if str(r.get("IndexCode", "")).upper() == "COMPOSITE":
                comp = r
                break
        if not comp:
            continue
        v = num(comp.get("Value"), None)
        if v:
            nilai.append(v)
            freq.append(num(comp.get("Frequency"), 0))
            tgl.append(str(comp.get("Date"))[:10])
        time.sleep(delay)
    if len(nilai) < 5:
        return None
    terakhir = nilai[0]                       # urut mundur dari hari terbaru
    dasar = rata(nilai[1:]) or terakhir
    rasio = terakhir / dasar if dasar else 1.0
    if rasio >= 1.15:
        saran = "longgar"
    elif rasio <= 0.85:
        saran = "ketat"
    else:
        saran = "netral"
    return {
        "hari": len(nilai), "dari": tgl[-1] if tgl else None,
        "sampai": tgl[0] if tgl else None,
        "nilai_terakhir": int(terakhir), "nilai_rata": int(dasar),
        "rasio": round(rasio, 2), "frekuensi_rata": int(rata(freq) or 0),
        "saran_likuiditas": saran,
        "alasan": "nilai transaksi terakhir %.2fx rata-rata %d hari"
                  % (rasio, len(nilai) - 1),
    }


def _ke_int(v):
    try:
        if v is None or v == "":
            return 0
        return int(float(str(v).replace(",", "").strip()))
    except (ValueError, TypeError):
        return 0


def normalkan_baris_stock(r):
    kode = str(r.get("StockCode") or r.get("kode") or "").strip().upper()
    if not kode:
        return None
    return {
        "kode": kode,
        "high": _ke_int(r.get("High")),
        "low": _ke_int(r.get("Low")),
        "close": _ke_int(r.get("Close")),
        "volume": _ke_int(r.get("Volume")),
        "value": _ke_int(r.get("Value")),
        "freq": _ke_int(r.get("Frequency")),
    }


def fetch_stock_summary(f, tanggal_yyyymmdd):
    url = "%s?date=%s" % (IDX_STOCK_URL, tanggal_yyyymmdd)
    j = f.get(url, headers={
        "Referer": "https://www.idx.id/",
        "X-Requested-With": "XMLHttpRequest",
    })
    if not j:
        return None
    rows = j.get("data") if isinstance(j, dict) else j
    if not rows:
        return None
    out = []
    for r in rows:
        n = normalkan_baris_stock(r)
        if n:
            out.append(n)
    return out or None


def tulis_harian(path_tujuan, tanggal, saham):
    import os
    from datetime import datetime
    payload = {
        "dibuat": datetime.now().astimezone().isoformat(timespec="seconds"),
        "tanggal": tanggal,
        "jumlah": len(saham),
        "sumber": "IDX Stock Summary (Volume/Value/Frequency resmi per emiten)",
        "saham": saham,
    }
    tmp = path_tujuan + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, path_tujuan)
    return path_tujuan


def hitung_sektor(records):
    """Kekuatan sektor = rata-rata return 6 bulan emiten per sektor.

    Ini perkiraan, bukan indeks sektor resmi. Semakin banyak emiten yang
    ditarik, semakin layak dipakai.
    """
    from collections import defaultdict
    kumpul = defaultdict(list)
    for r in records:
        sek = (r.get("sektor") or "").strip()
        rr = r.get("_ret6")
        if sek and rr is not None:
            kumpul[sek].append(rr)
    out = []
    for sek, arr in kumpul.items():
        out.append({"sektor": sek, "rata_return": round(rata(arr), 2),
                    "jumlah": len(arr)})
    out.sort(key=lambda x: x["rata_return"], reverse=True)
    return out


# ----------------------------------------------------------------------------
# BI Rate dari SEKI Bank Indonesia (XLS OLE2/BIFF, tanpa pustaka tambahan)
#
# Struktur berkasnya (dibedah langsung, Juni 2026):
#   - Wadah OLE2 (CFB): header 512 byte, DIFAT di header, FAT, direktori,
#     stream "Workbook" berisi record BIFF8.
#   - Record penting: 0x0085 BOUNDSHEET, 0x00FC SST (+0x003C CONTINUE),
#     0x00FD LABELSST, 0x027E RK, 0x00BD MULRK.
#   - Banyak sheet; yang terpakai berisi blok per tahun: baris atas = angka
#     tahun, baris bawahnya = label bulan ("Jan".."Dec"), diikuti baris
#     instrumen. BI Rate = baris "Policy Rate", sel pertama di blok 2017.
#   - CATATAN: nilai 0.0 pada sel bulan boleh jadi sel kosong yang diberi
#     gaya -- sel kosong tidak menghasilkan record apa pun, jadi 0.0 hanya
#     muncul bila BI benar-benar menulis nol. Data masa depan tidak ada.
# ----------------------------------------------------------------------------
def baca_ole2_workbook(data):
    """Ekstrak isi stream 'Workbook' dari berkas XLS OLE2. -> bytes."""
    if data[:8] != b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        raise ValueError("bukan berkas OLE2 (mungkin halaman error HTML)")
    ssz = 1 << struct.unpack("<H", data[0x1E:0x20])[0]
    difat = struct.unpack("<109I", data[0x4C:0x4C + 436])
    fat = []
    for s in difat:
        if s < 0xFFFFFFFA:
            fat.extend(struct.unpack("<%dI" % (ssz // 4),
                                     data[512 + s * ssz: 512 + (s + 1) * ssz]))
    if not fat:
        raise ValueError("FAT kosong")

    def rantai(mulai):
        out, s = [], mulai
        while s < 0xFFFFFFFA:
            out.append(s)
            if s >= len(fat):
                break
            s = fat[s]
        return out

    dir_data = b"".join(data[512 + s * ssz: 512 + (s + 1) * ssz]
                        for s in rantai(struct.unpack("<I", data[0x30:0x34])[0]))
    for i in range(len(dir_data) // 128):
        e = dir_data[i * 128:(i + 1) * 128]
        nama = e[:64].decode("utf-16-le", "replace").split("\x00")[0]
        if nama == "Workbook":
            mulai = struct.unpack("<I", e[116:120])[0]
            ukuran = struct.unpack("<I", e[120:124])[0]
            return b"".join(data[512 + s * ssz: 512 + (s + 1) * ssz]
                            for s in rantai(mulai))[:ukuran]
    raise ValueError("stream 'Workbook' tidak ditemukan")


def baca_biff_records(wb):
    """Pecah stream Workbook menjadi daftar (id_record, payload)."""
    recs, i = [], 0
    while i + 4 <= len(wb):
        rid, ln = struct.unpack("<HH", wb[i:i + 4])
        recs.append((rid, wb[i + 4:i + 4 + ln]))
        i += 4 + ln
    return recs


def baca_sst(recs):
    """Shared String Table (0x00FC) beserta lanjutannya di CONTINUE."""
    for idx, (rid, d) in enumerate(recs):
        if rid != 0x00FC:
            continue
        gabung = d
        j = idx + 1
        while j < len(recs) and recs[j][0] == 0x003C:
            gabung += recs[j][1]
            j += 1
        total, unik = struct.unpack("<II", gabung[:8])
        pos, sst = 8, []
        for _ in range(unik):
            cch = struct.unpack("<H", gabung[pos:pos + 2])[0]
            pos += 2
            flags = gabung[pos]
            pos += 1
            if flags & 0x01:
                sst.append(gabung[pos:pos + cch * 2].decode("utf-16-le", "replace"))
                pos += cch * 2
            else:
                sst.append(gabung[pos:pos + cch].decode("latin1", "replace"))
                pos += cch
        return sst
    return []


def rk_ke_float(rk):
    """Dekode angka RK (BIFF)."""
    if rk & 0x02:
        val = float(rk >> 2)
    else:
        val = struct.unpack("<d", b"\x00" * 4 + struct.pack("<I", rk & 0xFFFFFFFC))[0]
    if rk & 0x01:
        val /= 100.0
    return val


def baca_sheet_biff(recs, mulai, akhir):
    """Kumpulkan sel (baris, kolom) -> str/float dari rentang record satu sheet."""
    sst = baca_sst(recs)
    sel = {}
    for rid, d in recs[mulai:akhir + 1]:
        if rid == 0x00FD and len(d) >= 10:          # LABELSST
            r, c, _xf, isst = struct.unpack("<HHHI", d[:10])
            sel[(r, c)] = sst[isst] if isst < len(sst) else "?"
        elif rid == 0x0204 and len(d) >= 8:         # LABEL (jarang, tapi ada)
            r, c, _xf = struct.unpack("<HHH", d[:6])
            cch = struct.unpack("<H", d[6:8])[0]
            sel[(r, c)] = d[8:8 + cch].decode("latin1", "replace")
        elif rid == 0x027E and len(d) >= 10:        # RK
            r, c, _xf = struct.unpack("<HHH", d[:6])
            sel[(r, c)] = rk_ke_float(struct.unpack("<I", d[6:10])[0])
        elif rid == 0x00BD and len(d) >= 10:        # MULRK
            r, c1 = struct.unpack("<HH", d[:4])
            for k in range((len(d) - 6) // 6):
                rk = struct.unpack("<I", d[4 + k * 6 + 2:4 + k * 6 + 6])[0]
                sel[(r, c1 + k)] = rk_ke_float(rk)
        elif rid == 0x0203 and len(d) >= 14:        # NUMBER (float penuh)
            r, c, _xf = struct.unpack("<HHH", d[:6])
            sel[(r, c)] = struct.unpack("<d", d[6:14])[0]
    return sel


def ambil_birate(f, delay=1.5):
    """Unduh TABEL1_25_1.xls SEKI dan ekstrak seri bulanan BI Rate.

    Kembalikan dict berisi nilai terakhir, tanggalnya, riwayat 25 bulan
    terakhir, dan alasannya -- atau None bila semua jalur gagal.
    """
    log("  Mengambil BI Rate dari SEKI Bank Indonesia (TABEL1_25_1.xls)...")
    body = f._curl_get(SEKI_BIRATE_URL, {"User-Agent": UA,
                                         "Accept": "*/*"})
    if not body:
        # jalankan jalur urllib sebagai upaya kedua
        body_raw = f.get(SEKI_BIRATE_URL, headers={"Referer": "https://www.bi.go.id/"},
                         expect_json=False, quiet_429=True)
        body = body_raw if isinstance(body_raw, (bytes, bytearray)) else None
    if not body:
        log("  [!] XLS SEKI tidak bisa diunduh. BI Rate dipilih manual.")
        return None
    try:
        recs = baca_biff_records(baca_ole2_workbook(bytes(body)))
    except Exception as e:
        log("  [!] Berkas tidak bisa dibaca sebagai XLS: %s" % e)
        return None

    # Peta nama sheet -> rentang record (segmen 0 = global).
    nama_sheet = []
    for rid, d in recs:
        if rid == 0x0085 and len(d) >= 8:
            nm = d[6:]
            cch, flags = nm[0], nm[1]
            if flags & 0x01:
                nama_sheet.append(nm[2:2 + cch * 2].decode("utf-16-le", "replace"))
            else:
                nama_sheet.append(nm[2:2 + cch].decode("latin1", "replace"))
    seg, batas, mulai = -1, {}, None
    for idx, (rid, _d) in enumerate(recs):
        if rid == 0x0809:
            seg += 1
            mulai = idx
        if rid == 0x000A and seg >= 0:
            batas[seg] = (mulai, idx)

    # Cari baris BI Rate di SEMUA sheet ber-data, lalu pilih seri yang
    # datanya paling baru (berkas memuat beberapa sheet per era: 1990-2003,
    # 2002-2009, 2010-2016, dan 2017-sekarang -- semuanya bisa berisi baris
    # "Policy Rate"/"BI Rate").
    kandidat = []
    for si in sorted(batas):
        if si == 0:
            continue
        a, b = batas[si]
        sel = baca_sheet_biff(recs, a, b)
        baris = None
        for (r, c), v in sel.items():
            if isinstance(v, str) and v.strip().lower() in LABEL_BI_RATE:
                baris = r
                break
        if baris is None:
            continue

        # Baris tahun di atas baris bulan. PEMETAAN BLOK:
        # kolom kosong tambahan kadang disisipkan di antara bulan, jadi blok
        # TIDAK selalu 12 kolom rapat dan sel tahun bisa tidak sejajar dengan
        # label "Jan"-nya. Karena itu blok ditentukan dari urutan kolom label
        # "Jan" (monoton naik), lalu dipasangkan berurutan dengan tahun yang
        # juga terurut naik -- jumlah keduanya selalu sama (satu blok/tahun).
        # Bulan per kolom diambil dari LABEL baris bulannya, bukan offset.
        tahun_kol = {}
        for (r, c), v in sel.items():
            if r == baris - 2 and isinstance(v, (int, float)) and 1990 <= v <= 2100:
                tahun_kol[c] = int(v)
        jans = sorted(c for (r, c), v in sel.items()
                      if r == baris - 1 and isinstance(v, str)
                      and v.strip()[:3].lower() == "jan")
        tahun_urut = sorted(set(int(v) for v in tahun_kol.values()))
        if not jans or len(jans) != len(tahun_urut):
            continue
        blok = list(zip(jans, tahun_urut))
        seri = {}
        for i, (c_awal, th) in enumerate(blok):
            c_akhir = blok[i + 1][0] if i + 1 < len(blok) else c_awal + 13
            for c in range(c_awal, c_akhir):
                lab = sel.get((baris - 1, c))
                if not isinstance(lab, str):
                    continue
                m = BULAN_EN.get(lab.strip()[:3].lower())
                if not m:
                    continue
                v = sel.get((baris, c))
                if isinstance(v, (int, float)) and 0 < v < 50:
                    seri[(th, m)] = round(v, 2)
        if seri:
            nama = nama_sheet[si - 1] if 0 < si <= len(nama_sheet) else str(si)
            kandidat.append((nama, sorted(seri.items())))

    if not kandidat:
        log("  [!] Baris BI Rate tidak ditemukan di XLS (format berubah?). BI Rate manual.")
        return None

    # Pilih kandidat dengan periode terakhir yang paling baru.
    nama, urut = max(kandidat, key=lambda x: x[1][-1][0])
    if len(kandidat) > 1:
        lain = ", ".join("%s s/d %s" % (n, "%04d-%02d" % s[-1][0]) for n, s in kandidat
                         if (n, s) != (nama, urut))
        log("  [i] Beberapa sheet berisi BI Rate; dipakai yang terbaru (%s). Lainnya: %s"
            % (nama, lain))

    (th, bl), nilai = urut[-1]
    # Riwayat: cukup 25 bulan terakhir untuk ditampilkan.
    hist = [{"periode": "%04d-%02d" % k, "nilai": v} for k, v in urut[-25:]]
    return {
        "nilai": nilai,
        "periode": "%04d-%02d" % (th, bl),
        "sheet": nama,
        "jumlah_data": len(urut),
        "rentang": ["%04d-%02d" % urut[0][0], "%04d-%02d" % urut[-1][0]],
        "riwayat": hist,
        "alasan": "data akhir periode %s dari sheet '%s' (%d bulan data, %s s/d %s)"
                  % ("%04d-%02d" % (th, bl), nama, len(urut),
                     "%04d-%02d" % urut[0][0], "%04d-%02d" % urut[-1][0]),
    }


def ambil_pasar(f, args):
    """Kumpulkan seluruh data Langkah 1 dan kembalikan sebagai dict."""
    log("")
    log("Mengambil regime pasar (IHSG + likuiditas + BI Rate)...")
    ch = fetch_chart(f, IHSG_SIMBOL, rng="1y", suffix="")
    regime = None
    if ch and ch.get("close"):
        regime = hitung_regime(ch["close"])
        if regime:
            log("  IHSG %.2f  MA50 %.2f  MA200 %s  -> saran kuadran: %s"
                % (regime["tutup"], regime["ma50"] or 0,
                   ("%.2f" % regime["ma200"]) if regime["ma200"] else "-",
                   regime["saran_kuadran"].upper()))
    else:
        log("  [!] Riwayat IHSG tidak bisa diambil. Kuadran harus dipilih manual.")

    lik = None
    if not args.no_likuiditas:
        log("  Mengambil nilai transaksi harian IDX (%d hari, perlu beberapa detik)..."
            % args.pasar_hari)
        lik = hitung_likuiditas(f, hari=args.pasar_hari, delay=0.35)
        if lik:
            log("  Likuiditas: %s (nilai terakhir %.1f T vs rata-rata %.1f T)"
                % (lik["saran_likuiditas"].upper(), lik["nilai_terakhir"] / 1e12,
                   lik["nilai_rata"] / 1e12))
        else:
            log("  [!] Nilai transaksi IDX tidak terbaca. Likuiditas dipilih manual.")

    # BI Rate: di-scrape dari tabel SEKI resmi BI. Tetap ditimpa manual bila
    # pengguna mengisi --bi-rate.
    bi = None
    if not args.no_birate:
        bi = ambil_birate(f, delay=args.delay)
        if bi:
            log("  BI Rate: %.2f%% (posisi data %s)"
                % (bi["nilai"], bi["periode"]))
            bi.pop("_sebelum", None)
        else:
            log("  [!] BI Rate tidak terbaca. Isi manual dengan --bi-rate.")
    if args.bi_rate is not None:
        bi = {"nilai": args.bi_rate,
              "periode": "manual",
              "sumber_manual": True,
              "alasan": "diisi manual lewat --bi-rate"}
        log("  BI Rate (manual): %.2f%%" % args.bi_rate)

    return {
        "dibuat": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "sumber": ("Yahoo Finance (IHSG) + IDX GetIndexSummary (nilai transaksi) "
                   "+ SEKI Bank Indonesia (BI Rate)"),
        "catatan": ("Kuadran, likuiditas, dan BI Rate dihitung otomatis. "
                    "Toleransi risiko tetap manual. Kekuatan sektor diagregasi dari "
                    "emiten yang ditarik, bukan indeks sektor resmi."),
        "ihsg": regime, "likuiditas": lik,
        "suku_bunga_bi": (bi["nilai"] if bi and "nilai" in bi else None),
        "bi_rate": bi,
    }


# ----------------------------------------------------------------------------
# Laporan keuangan IDX (XBRL dalam bentuk .xlsx)
#
# Ini menutup utang teknis terbesar: laba, ekuitas, arus kas, kas, dan utang
# ASLI dari emiten IDX -- bukan turunan dari Yahoo.
#
# Cara kerja:
#   1. GET  /primary/ListedCompany/GetFinancialReport?kodeEmiten=&year=&periode=audit
#      &pageSize=100&reportType=rdf   -> metadata + daftar lampiran
#   2. Unduh lampiran .xlsx (di dalamnya ada neraca, laba rugi, arus kas)
#   3. Baca sheet berdasarkan JUDUL, bukan kode sheet
#
# PENTING: kode sheet BERBEDA antar template industri (bank 4220000/4322000/
# 4510000, infrastruktur 3210000/3312000/3510000). Karena itu sheet dikenali
# dari judulnya. Jangan pernah menghafal kodenya.
#
# PENTING: setiap sheet memuat kolom tahun berjalan DAN tahun sebelumnya, jadi
# satu berkas memberi dua tahun sekaligus.
#
# PENTING: Cloudflare menolak urllib (HTTP 403) tetapi menerima curl, dan
# mengharuskan cookie __cf_bm dari kunjungan halaman utama. Karena itu ada
# pemanasan() sebelum penarikan, dan unduhan berkas statis perlu jeda.
# ----------------------------------------------------------------------------
IDX_LAPORAN_URL = "https://www.idx.co.id/primary/ListedCompany/GetFinancialReport"
IDX_REF_LAPORAN = ("https://www.idx.co.id/id/perusahaan-tercatat/"
                   "laporan-keuangan-dan-tahunan")

POLA_SHEET_LAP = {
    "neraca": r"Statement of financial position",
    "labarugi": r"Statement of profit or loss",
    "aruskas": r"Statement of cash flows",
}

# Laba yang dipakai HARUS yang dapat diatribusikan ke entitas induk, supaya
# konsisten dengan EPS. "Jumlah laba (rugi)" sudah termasuk kepentingan
# non-pengendali dan bisa jauh berbeda -- contoh TLKM 2024: 30.743 vs 23.649
# (miliar), sedangkan EPS 238,73 x 99,06 miliar saham = 23,65 triliun.
POLA_BARIS_LAP = {
    "aset": r"^jumlah aset$",
    "liabilitas": r"^jumlah liabilitas$",
    "ekuitas": r"^jumlah ekuitas$",
    "laba": r"^laba \(rugi\) yang dapat diatribusikan ke entitas induk$",
    "laba_total": r"^jumlah laba \(rugi\)$",
    "laba_sebelum_pajak": r"^jumlah laba \(rugi\) sebelum pajak penghasilan$",
    "eps": r"laba \(rugi\) per saham dasar dari operasi yang dilanjutkan",
    "pendapatan": r"^(penjualan dan pendapatan usaha|pendapatan bunga bersih)$",
    "kas_operasi": (r"jumlah arus kas bersih yang diperoleh dari "
                    r"\(digunakan untuk\) aktivitas operasi"),
    "kas_akhir": r"^kas dan setara kas arus kas, akhir periode$",
}

# "Pembulatan yang digunakan" -> faktor ke rupiah penuh
SKALA_LAP = [("triliun", 1e12), ("miliar", 1e9), ("juta", 1e6),
             ("ribu", 1e3), ("satuan", 1.0), ("unit", 1.0)]

# Kebalikannya: pangkat skala XBRL -> teks pembulatan (dipakai jalur inlineXBRL)
SKALA_KE_TEKS = {0: "Satuan / In Unit", 3: "Ribuan / In Thousand",
                 6: "Jutaan / In Million", 9: "Miliaran / In Billion",
                 12: "Triliunan / In Trillion"}


def skala_dari(teks):
    """'Jutaan / In Million' -> 1e6. Bawaan 1e6 bila tidak dikenali."""
    t = str(teks or "").lower()
    for kata, faktor in SKALA_LAP:
        if kata in t:
            return faktor
    return 1e6


# Bidang rupiah yang ikut dikalikan skala. EPS sengaja TIDAK termasuk:
# EPS selalu dalam rupiah per saham, tidak pernah disajikan dalam jutaan.
BIDANG_RUPIAH = ("aset", "liabilitas", "ekuitas", "pendapatan", "laba",
                 "laba_total", "laba_sebelum_pajak", "arus_kas_operasi", "kas",
                 "aset_py", "ekuitas_py", "laba_py", "pendapatan_py")


def selaraskan_skala(daftar, log_fn=None):
    """Terapkan skala rupiah tiap tahun, lalu betulkan tahun yang menyimpang.

    Dua tahap, dan urutannya penting:

    1. **Percayai label 'Pembulatan' tiap tahun.** Pada mayoritas kasus label
       itu BENAR. Contoh ANTM: 2021-2024 berlabel "Jutaan" dengan aset mentah
       ~3,3e7, sedangkan 2019-2020 berlabel "Ribuan" dengan aset mentah ~3,0e10
       -- keduanya menghasilkan ~3e13 dan keduanya benar.

    2. **Baru deteksi penyimpangan.** Setelah skala diterapkan, bandingkan total
       aset tiap tahun dengan acuan (kelas besaran terbanyak, lalu median di
       dalam kelas itu). Tahun yang menyimpang sejauh pangkat 1000 digeser.
       Inilah yang menangkap kasus BBCA 2023: berlabel "Jutaan" padahal datanya
       rupiah penuh, sehingga hasilnya 1000x terlalu besar.

    Tahap 1 saja tidak cukup (BBCA 2023 salah). Tahap 2 saja juga tidak cukup:
    menyelaraskan mentah-mentah sebelum label diterapkan akan salah kelas pada
    tahun yang besaran mentahnya berada tepat di batas pembulatan -- persis yang
    terjadi pada ANTM 2020 (mentah 3,17e10, batas kelas 3,5).
    """
    if not daftar:
        return daftar

    # -- tahap 1: skala yang dideklarasikan --------------------------------
    for x in daftar:
        x["skala"] = skala_dari(x.get("pembulatan"))
        for b in BIDANG_RUPIAH:
            if x.get(b) is not None:
                x[b] = x[b] * x["skala"]

    # -- tahap 2: acuan dari kelas besaran terbanyak -----------------------
    bernilai = [x for x in daftar if x.get("aset") and x["aset"] > 0]
    if len(bernilai) < 3:
        return daftar
    kelas = Counter(int(round(math.log10(x["aset"]) / 3.0)) for x in bernilai)
    eksp_acuan = kelas.most_common(1)[0][0]
    isi = sorted(x["aset"] for x in bernilai
                 if int(round(math.log10(x["aset"]) / 3.0)) == eksp_acuan)
    acuan = isi[len(isi) // 2]

    for x in bernilai:
        rasio = acuan / x["aset"]
        if rasio <= 0:
            continue
        eksp = round(math.log10(rasio) / 3.0) * 3
        if abs(eksp) < 3:
            continue  # perbedaan wajar antar tahun, bukan salah skala
        faktor = 10.0 ** eksp
        x["skala"] *= faktor
        for b in BIDANG_RUPIAH:
            if x.get(b) is not None:
                x[b] *= faktor
        if log_fn:
            log_fn("      [i] %s: skala digeser %gx - label 'Pembulatan' IDX "
                   "keliru untuk tahun ini" % (x.get("tahun"), faktor))

    if log_fn:
        for x in daftar:
            a = x.get("aset")
            if a and not (1e10 <= a <= 1e16):
                log_fn("      [!] %s: total aset tidak wajar (%.3g) - periksa skala"
                       % (x.get("tahun"), a))
    return daftar


class LaporanIDX:
    """Penarik laporan keuangan IDX berbasis XBRL-xlsx."""

    def __init__(self, delay=1.5, cache_dir="cache-laporan"):
        self.delay = delay
        self.cache_dir = cache_dir
        self.jar = os.path.join(cache_dir, "cookies.txt")
        self.siap = False
        if not os.path.isdir(cache_dir):
            os.makedirs(cache_dir, exist_ok=True)

    def _curl(self, url, out=None, timeout=90):
        if not CURL:
            return None
        cmd = [CURL, "-s", "-L", "-m", str(timeout), "-A", UA,
               "-b", self.jar, "-c", self.jar,
               "-H", "Referer: " + IDX_REF_LAPORAN]
        if out:
            cmd += ["-o", out]
        cmd.append(url)
        try:
            p = subprocess.run(cmd, capture_output=True, timeout=timeout + 20)
        except Exception:
            return None
        return None if out else p.stdout

    def ada_cookie_sesi(self):
        """Apakah berkas jar sudah memuat cookie sesi Cloudflare?"""
        try:
            with open(self.jar, "r", encoding="utf-8", errors="replace") as fh:
                isi = fh.read()
        except OSError:
            return False
        return ("__cf_bm" in isi) or ("auth.strategy" in isi)

    def pemanasan(self, log_fn=None, percobaan_maks=3):
        """Kunjungi halaman utama supaya Cloudflare menaruh cookie sesi.

        Langkah ini BUKAN formalitas, melainkan syarat mutlak. Diuji ulang
        2026-09-20 terhadap lampiran XBRL BBCA 2024:
            tanpa cookie  -> HTTP 403, 6.621 byte, header "Cf-Mitigated: challenge"
            ada cookie    -> HTTP 200, 225.497 byte, ZIP sah
        Endpoint API JSON tidak seketat ini, tetapi berkas statis di /Portals/0/
        selalu lewat managed challenge.

        Cookie-nya diperiksa benar-benar ada, bukan diasumsikan: kalau gagal,
        ulangi dengan jeda makin lama lalu laporkan jujur lewat kembalian False.
        """
        for i in range(percobaan_maks):
            self._curl("https://www.idx.co.id/", out=os.devnull, timeout=45)
            if self.ada_cookie_sesi():
                self.siap = True
                return True
            if log_fn and i < percobaan_maks - 1:
                log_fn("      [i] cookie sesi Cloudflare belum didapat, mencoba lagi...")
            time.sleep(2 + 2 * i)
        self.siap = False
        return False

    def daftar(self, kode, tahun):
        url = ("%s?kodeEmiten=%s&year=%d&periode=audit&pageSize=100&reportType=rdf"
               % (IDX_LAPORAN_URL, kode, tahun))
        body = self._curl(url)
        if not body:
            return None
        try:
            return json.loads(body.decode("utf-8", "replace"))
        except json.JSONDecodeError:
            return None

    def xlsx_dari(self, d):
        return self._lampiran(d, ".xlsx")

    @staticmethod
    def _lampiran(d, akhiran):
        for a in (d.get("Results") or [{}])[0].get("Attachments") or []:
            if (a.get("File_Name") or "").lower().endswith(akhiran):
                return a
        return None

    @staticmethod
    def _xlsx_sah(path):
        """Berkas .xlsx adalah arsip ZIP, jadi isinya diawali 'PK'.
        Halaman tantangan Cloudflare berupa HTML -- kecil dan tidak diawali 'PK'.
        Memeriksa isi ini penting: berkas gagal unduh bisa tertulis ke disk dan
        terlihat 'ada', lalu dipakai sebagai laporan palsu."""
        try:
            if os.path.getsize(path) < 50000:
                return False
            with open(path, "rb") as fh:
                return fh.read(2) == b"PK"
        except OSError:
            return False

    def unduh(self, kode, tahun, lampiran, log_fn=None, akhiran="xlsx"):
        """Unduh lampiran (berkas ZIP: .xlsx maupun .zip) dengan cache dan
        percobaan ulang.

        Cloudflare kerap membalas halaman tantangan pada berkas statis walau
        permintaan metadata berhasil. Karena itu tiap percobaan: buang berkas
        rusak, hangatkan ulang sesi, lalu mundur makin lama."""
        tujuan = os.path.join(self.cache_dir, "%s-%d.%s" % (kode, tahun, akhiran))
        if self._xlsx_sah(tujuan):
            return tujuan
        url = "https://www.idx.co.id" + lampiran["File_Path"].replace(" ", "%20")
        for percobaan in range(4):
            if os.path.exists(tujuan):
                try:
                    os.remove(tujuan)
                except OSError:
                    pass
            self._curl(url, out=tujuan, timeout=120)
            if self._xlsx_sah(tujuan):
                return tujuan
            if log_fn and percobaan < 3:
                log_fn("      [i] unduhan %s %d gagal, mencoba lagi..." % (kode, tahun))
            self.pemanasan()  # sesi Cloudflare diduga kedaluwarsa
            time.sleep(5 + percobaan * 6)
        if os.path.exists(tujuan):
            try:
                os.remove(tujuan)
            except OSError:
                pass
        return None

    # -- pembacaan xlsx tanpa dependensi eksternal ---------------------------
    @staticmethod
    def baca_xlsx(path):
        z = zipfile.ZipFile(path)
        ss = [''.join(t.text or '' for t in si.iter(XL_NS + 't'))
              for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall(XL_NS + 'si')]
        wb = z.read('xl/workbook.xml').decode('utf-8', 'replace')
        rels = z.read('xl/_rels/workbook.xml.rels').decode('utf-8', 'replace')
        rid2t = {m.group(1): m.group(2) for m in
                 re.finditer(r'Id="([^"]+)"[^>]*Target="([^"]+)"', rels)}
        daftar_sheet = re.findall(r'<sheet[^>]*name="([^"]+)"[^>]*r:id="([^"]+)"', wb)
        hasil = {}
        for nm, rid in daftar_sheet:
            root = ET.fromstring(z.read('xl/' + rid2t[rid].lstrip('/')))
            baris = []
            for row in root.iter(XL_NS + 'row'):
                vals = []
                for c in row.findall(XL_NS + 'c'):
                    v = c.find(XL_NS + 'v')
                    t = c.get('t')
                    if v is None:
                        continue
                    vals.append(ss[int(v.text)] if t == 's' else v.text)
                if vals:
                    baris.append(vals)
            hasil[nm] = baris
        return hasil

    # -- cadangan: inlineXBRL (HTML) bila .xlsx IDX rusak ---------------------
    @staticmethod
    def _teks_html(s):
        s = re.sub(r"<[^>]+>", " ", s)
        s = (s.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
              .replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " "))
        return re.sub(r"\s+", " ", s).strip()

    @staticmethod
    def baca_inline_xbrl(path):
        """Baca inlineXBRL.zip sebagai cadangan.

        Sebagian berkas .xlsx IDX rusak di sisi mereka -- contoh nyata ANTM 2024:
        server membalas HTTP 200 dengan content-type xlsx, tetapi isinya hanya
        kata 'Administrator' berulang (165 byte). Untuk kasus itu, lampiran
        inlineXBRL.zip memuat HTML per bagian laporan dengan struktur setara
        (label di kolom kiri, nilai di kolom kanan).

        Keunggulannya: setiap nilai membawa atribut scale (mis. scale="6" berarti
        jutaan), sehingga skala terbaca pasti -- bukan dari label yang bisa keliru.

        Hasilnya dibuat berbentuk sama dengan baca_xlsx(), termasuk sheet
        '1000000' buatan yang memuat baris 'Pembulatan' agar ekstrak() bisa
        dipakai tanpa perubahan.
        """
        z = zipfile.ZipFile(path)
        hasil = {}
        hitung_skala = Counter()
        for nm in z.namelist():
            if not nm.endswith(".html"):
                continue
            h = z.read(nm).decode("utf-8", "replace")
            judul = None
            for pola in POLA_SHEET_LAP.values():
                m = re.search(pola + r"[^<]{0,90}", h)
                if m:
                    judul = m.group(0)
                    break
            if not judul:
                continue
            baris = [[judul]]
            for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", h, re.S):
                tds = re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)
                if len(tds) < 2:
                    continue
                label = LaporanIDX._teks_html(tds[0])
                if not label:
                    continue
                # nilai kolom 1 (tahun berjalan) dan 2 (tahun sebelumnya)
                nilai = []
                for td in tds[1:]:
                    t = LaporanIDX._teks_html(td)
                    nilai.append(t if re.match(r"^-?[\d.,]+$", t) else "")
                if not nilai or not nilai[0]:
                    continue
                sk = re.search(r'<ix:nonFraction[^>]*\bscale="(-?\d+)"', tds[1], re.I)
                if sk:
                    hitung_skala[int(sk.group(1))] += 1
                baris.append([label] + nilai[:2])
            hasil[nm] = baris

        # Skala = yang paling banyak muncul di seluruh berkas
        if hitung_skala:
            eksp = hitung_skala.most_common(1)[0][0]
        else:
            eksp = 0
        teks = SKALA_KE_TEKS.get(eksp, "Satuan / In Unit")
        hasil["1000000"] = [
            ["General information"],
            ["Pembulatan yang digunakan dalam penyajian jumlah dalam laporan keuangan",
             teks, "Level of rounding used in financial statements"],
        ]
        return hasil

    @staticmethod
    def cari(baris, pola, kolom=1):
        for v in baris:
            if len(v) > kolom and re.search(pola, str(v[0]), re.I):
                n = LaporanIDX._angka(v[kolom])
                if n is not None:
                    return n
        return None

    @staticmethod
    def _angka(v):
        """Baca angka dari sel: '44,522,645' -> 44522645.0 ; '238.73' -> 238.73.

        Pada laporan IDX angkanya bulat (atribut decimals membulatkan ke
        jutaan/miliaran), jadi koma di sini selalu pemisah ribuan.
        """
        if v is None:
            return None
        t = str(v).strip()
        if not t:
            return None
        negatif = t.startswith("-") or (t.startswith("(") and t.endswith(")"))
        t = t.strip("()").replace(" ", "").replace("\u00a0", "")
        if "," in t and "." in t:
            if t.rfind(",") > t.rfind("."):     # 1.234,5  gaya Indonesia
                t = t.replace(".", "").replace(",", ".")
            else:                               # 1,234.5  gaya mesin
                t = t.replace(",", "")
        elif "," in t:
            t = t.replace(",", "")
        try:
            n = float(t)
        except ValueError:
            return None
        return -n if negatif else n

    @staticmethod
    def _teks(baris, pola, kolom=1):
        for v in baris:
            if len(v) > kolom and re.search(pola, str(v[0]), re.I):
                return v[kolom]
        return None

    def ekstrak(self, sh):
        """Ambil angka kunci MENTAH dari satu berkas xlsx (belum dikalikan
        skala). kolom=1 -> tahun berjalan, kolom=2 -> tahun sebelumnya.

        Skala TIDAK diterapkan di sini karena label 'Pembulatan' IDX tidak
        dapat dipercaya antar tahun -- lihat selaraskan_skala().
        """
        peta = {}
        for nm, baris in sh.items():
            if not baris:
                continue
            judul = str(baris[0][0]) if baris[0] else ""
            if "Prior Year" in judul:
                continue
            for kunci, pola in POLA_SHEET_LAP.items():
                if kunci not in peta and re.search(pola, judul, re.I):
                    peta[kunci] = baris
        if "neraca" not in peta or "labarugi" not in peta:
            return None

        umum = sh.get("1000000", [])

        def amb(kunci_sheet, kunci_baris, kolom=1):
            b = peta.get(kunci_sheet)
            if not b:
                return None
            return self.cari(b, POLA_BARIS_LAP[kunci_baris], kolom)

        out = {
            "sektor_idx": self._teks(umum, r"^sektor$", 1),
            "industri_idx": self._teks(umum, r"^industri$", 1),
            "subsektor_idx": self._teks(umum, r"^subsektor$", 1),
            "mata_uang": self._teks(umum, r"^mata uang pelaporan$", 1),
            "pembulatan": self._teks(umum, r"^pembulatan", 1),
            "opini": self._teks(umum, r"^jenis opini auditor$", 1),
            "awal_periode": self._teks(umum, r"^tanggal awal periode berjalan$", 1),
            "akhir_periode": self._teks(umum, r"^tanggal akhir periode berjalan$", 1),
        }
        # Neraca (titik waktu)
        out["aset"] = amb("neraca", "aset")
        out["liabilitas"] = amb("neraca", "liabilitas")
        out["ekuitas"] = amb("neraca", "ekuitas")
        # Laba rugi (periode) -- EPS tidak pernah diskalakan (sudah per saham)
        out["pendapatan"] = amb("labarugi", "pendapatan")
        out["laba"] = amb("labarugi", "laba")
        out["laba_total"] = amb("labarugi", "laba_total")
        out["laba_sebelum_pajak"] = amb("labarugi", "laba_sebelum_pajak")
        out["eps"] = amb("labarugi", "eps")
        # Arus kas (periode)
        if "aruskas" in peta:
            out["arus_kas_operasi"] = amb("aruskas", "kas_operasi")
            out["kas"] = amb("aruskas", "kas_akhir")
        else:
            out["arus_kas_operasi"] = None
            out["kas"] = None
        # Baris tahun sebelumnya (kolom 2) -- untuk verifikasi & tren
        out["aset_py"] = amb("neraca", "aset", 2)
        out["ekuitas_py"] = amb("neraca", "ekuitas", 2)
        out["laba_py"] = amb("labarugi", "laba", 2)
        out["pendapatan_py"] = amb("labarugi", "pendapatan", 2)
        return out

    def satu_tahun(self, kode, tahun, log_fn=None):
        d = self.daftar(kode, tahun)
        if not d or not d.get("Results"):
            return None
        r = d["Results"][0]
        sh, berkas = None, None

        # Jalur utama: .xlsx XBRL
        lamp = self._lampiran(d, ".xlsx")
        if lamp:
            path = self.unduh(kode, tahun, lamp, log_fn=log_fn)
            if path:
                try:
                    sh = self.baca_xlsx(path)
                    berkas = lamp.get("File_Name")
                except Exception as e:
                    if log_fn:
                        log_fn("      [!] %s %d: .xlsx tidak terbaca (%s)" % (kode, tahun, e))
            elif log_fn:
                log_fn("      [i] %s %d: .xlsx tidak bisa diunduh" % (kode, tahun))

        # Cadangan: inlineXBRL (HTML). Sebagian .xlsx IDX rusak di sisi mereka
        # sendiri (mis. ANTM 2024 hanya berisi kata 'Administrator').
        if sh is None:
            lamp2 = self._lampiran(d, "inlinexbrl.zip")
            if lamp2:
                if log_fn:
                    log_fn("      [i] %s %d: beralih ke cadangan inlineXBRL" % (kode, tahun))
                path2 = self.unduh(kode, tahun, lamp2, log_fn=log_fn, akhiran="inline.zip")
                if path2:
                    try:
                        sh = self.baca_inline_xbrl(path2)
                        berkas = lamp2.get("File_Name")
                    except Exception as e:
                        if log_fn:
                            log_fn("      [!] %s %d: inlineXBRL tidak terbaca (%s)"
                                   % (kode, tahun, e))

        if sh is None:
            if log_fn:
                log_fn("      [!] %s %d: tidak ada berkas laporan yang bisa dibaca"
                       % (kode, tahun))
            return None

        out = self.ekstrak(sh)
        if not out:
            if log_fn:
                log_fn("      [!] %s %d: pola neraca/laba rugi tidak dikenali"
                       % (kode, tahun))
            return None
        out["kode"] = kode
        out["tahun"] = tahun
        out["nama"] = r.get("NamaEmiten")
        out["berkas"] = berkas
        return out

    def histori(self, kode, tahun_awal, tahun_akhir, log_fn=None):
        """Tarik laporan tiap tahun, selaraskan skalanya, lalu kembalikan
        daftar terbaru-lebih-dulu."""
        mentah = []
        for th in range(tahun_akhir, tahun_awal - 1, -1):
            rec = self.satu_tahun(kode, th, log_fn=log_fn)
            if rec:
                mentah.append(rec)
            time.sleep(self.delay)
        if not mentah:
            return []
        selaraskan_skala(mentah, log_fn=log_fn)
        if log_fn:
            for x in mentah:
                log_fn("    %-6s %d  laba %-12s aset %-12s ekuitas %s" % (
                    kode, x["tahun"], fmt_ringkas(x.get("laba")),
                    fmt_ringkas(x.get("aset")), fmt_ringkas(x.get("ekuitas"))))
        return mentah


def fmt_ringkas(v):
    """Angka rupiah -> bentuk pendek untuk log (mis. 54,9 T)."""
    if v is None:
        return "-"
    for batas, suf in ((1e12, " T"), (1e9, " M"), (1e6, " jt")):
        if abs(v) >= batas:
            return ("%.2f" % (v / batas)).replace(".", ",") + suf
    return "%.0f" % v


# Ambang tren laba: 5% dari laba tipikal per tahun.
# Dipakai untuk menghitung ULANG eps_trend dari riwayat laba IDX yang asli.
# Kolom ini berbobot paling besar di peringkat screener (tier 1/200/1000 poin),
# sementara sebelumnya diisi dari Yahoo atau tempelan manual yang bisa basi --
# akibatnya emiten yang labanya jelas tumbuh bisa tertulis "down trend".
AMBANG_TREN = 0.05


def tren_laba(hist):
    """Tentukan tren laba dari riwayat tahunan -> 'up' | 'fluktuatif' | 'down'.

    hist: daftar (tahun, nilai_miliar). Urutan bebas.

    Memakai regresi linear pada laba yang sudah dinormalkan terhadap laba
    tipikal (rata-rata nilai absolut), sehingga kemiringannya terbaca sebagai
    "berapa persen dari laba tipikal per tahun" dan tidak bergantung skala.
    Cara ini tetap bekerja walau ada tahun merugi -- beda dengan regresi
    log-linear yang tidak terdefinisi untuk laba <= 0.

    Minimal 4 titik; kalau kurang kembalikan None supaya pemanggil tidak menebak.
    """
    titik = sorted((t, v) for t, v in hist if v is not None)
    if len(titik) < 4:
        return None
    n = len(titik)
    skala = sum(abs(v) for _, v in titik) / n
    if skala <= 0:
        return None
    xs = [float(t) for t, _ in titik]
    ys = [v / skala for _, v in titik]
    mx, my = sum(xs) / n, sum(ys) / n
    bawah = sum((x - mx) ** 2 for x in xs)
    if bawah <= 0:
        return None
    lereng = sum((xs[i] - mx) * (ys[i] - my) for i in range(n)) / bawah
    if lereng >= AMBANG_TREN:
        return "up"
    if lereng <= -AMBANG_TREN:
        return "down"
    return "fluktuatif"


def gabung_laporan(rec, lap_tahun):
    """Timpa nilai turunan Yahoo dengan angka ASLI dari laporan IDX.

    lap_tahun: daftar record tahunan (terbaru lebih dulu).
    Mengembalikan (rec, catatan) -- catatan berisi hal yang perlu diketahui.

    Satuan hist_laba = MILIAR rupiah, sesuai yang diharapkan screener
    (chartLaba memakai satuan 'miliar rupiah').
    """
    if not lap_tahun:
        return rec, []
    catatan = []
    kini = lap_tahun[0]
    th = kini.get("tahun")

    if kini.get("ekuitas"):
        rec["ekuitas"] = clean(kini["ekuitas"])
    if kini.get("laba") is not None:
        rec["laba"] = clean(kini["laba"])
    if kini.get("eps"):
        rec["eps"] = clean(kini["eps"])
        rec["kuartal"] = 4  # laporan tahunan = sudah setahun penuh
    if kini.get("arus_kas_operasi") is not None:
        rec["fcf"] = clean(kini["arus_kas_operasi"])
    if kini.get("kas") is not None:
        rec["kas"] = clean(kini["kas"])
    if kini.get("liabilitas") is not None:
        rec["utang"] = clean(kini["liabilitas"])

    # Catatan lama dari Yahoo bisa jadi tidak berlaku lagi begitu angka asli
    # dari IDX masuk -- mis. "arus kas operasi negatif" padahal laporan IDX
    # menunjukkan arus kas operasi positif.
    if kini.get("arus_kas_operasi") is not None and kini["arus_kas_operasi"] > 0:
        lama = rec.get("_catatan") or []
        rec["_catatan"] = [c for c in lama if "arus kas operasi negatif" not in c]
        if len(rec["_catatan"]) != len(lama):
            catatan.append("catatan arus kas Yahoo dibatalkan oleh laporan IDX")

    # Sektor dari IDX lebih otoritatif daripada tebakan Yahoo.
    sek = normalisasi_sektor(kini.get("sektor_idx"))
    if sek:
        if rec.get("sektor") and rec["sektor"] != sek:
            catatan.append("sektor dikoreksi IDX: %s -> %s" % (rec["sektor"], sek))
        rec["sektor"] = sek
        rec["cyclical"] = 1 if sek in SEKTOR_CYCLICAL else 0

    # DER gaya Indonesia = total liabilitas / ekuitas
    if rec["ekuitas"] > 0 and rec.get("utang") is not None:
        rec["der"] = clean(rec["utang"] / rec["ekuitas"])

    # Riwayat laba tahunan -> hist_laba (MILIAR rupiah)
    hist = [(x["tahun"], x["laba"] / 1e9)
            for x in lap_tahun if x.get("laba") is not None]
    hist.sort(key=lambda p: p[0])
    if hist:
        rec["hist_laba"] = "|".join(
            "%d:%s" % (t, ("%.1f" % v).rstrip("0").rstrip(".")) for t, v in hist)
        rec["_tahun_laporan"] = [t for t, _ in hist]

        # eps_trend dihitung ULANG dari riwayat asli. Membiarkannya dari Yahoo
        # membuat peringkat screener bertentangan dengan datanya sendiri:
        # mis. ASII labanya naik 21,7 -> 34,1 T tetapi tertulis "down trend",
        # lalu tertinggal di peringkat terakhir meski lolos semua kriteria.
        tren = tren_laba(hist)
        if tren:
            lama_tren = rec.get("eps_trend")
            if lama_tren and lama_tren != tren:
                catatan.append("tren laba dikoreksi IDX: %s -> %s (dari %d tahun riwayat)"
                               % (lama_tren, tren, len(hist)))
            rec["eps_trend"] = tren

    # Verifikasi silang: EPS x saham vs laba induk
    if rec["eps"] and rec["saham"] and rec["laba"]:
        selisih = abs(rec["eps"] * rec["saham"] - rec["laba"]) / abs(rec["laba"])
        if selisih > 0.15:
            catatan.append("EPS x saham tidak sinkron dengan laba IDX (selisih %.0f%%)"
                           % (selisih * 100))

    # Kualitas kas Thowilz dari angka IDX yang asli (lebih otoritatif dari Yahoo)
    hist_cf = [(x["tahun"], x.get("laba"), x.get("arus_kas_operasi"))
               for x in lap_tahun if x.get("laba") is not None and x.get("arus_kas_operasi") is not None]
    if len(hist_cf) >= 3:
        aset_ttm = kini.get("aset") or 0
        q = compute_cash_quality(hist_cf, aset_ttm, rec.get("sektor") or "")
        rec["cfo3"] = q["cfo3"]
        rec["sloan"] = q["sloan"]
        rec["cash_badge"] = q["badge"]
        if q["badge"] == "Kill":
            catatan.append("kas: %s" % q["alasan"])
    # hitung ulang EV/CFO dengan CFO IDX bila EV Yahoo ada
    try:
        mcap_now = float(rec.get("harga") or 0) * float(rec.get("saham") or 0)
    except (TypeError, ValueError):
        mcap_now = 0
    ev_now = compute_ev(mcap_now, rec.get("utang") or 0, rec.get("kas") or 0)
    cfo_now = kini.get("arus_kas_operasi")
    if ev_now is not None and cfo_now is not None and cfo_now > 0:
        rec["ev_cfo"] = round(ev_now / float(cfo_now), 2)
    cagr_cf = compute_cfo_cagr(hist_cf) if len(hist_cf) >= 2 else None
    rec["cfo_cagr"] = round(cagr_cf * 100.0, 1) if cagr_cf is not None else None
    rec["peg_cfo"] = compute_peg_cfo(rec.get("ev_cfo"), cagr_cf)
    laba_hist = [(x["tahun"], x.get("laba")) for x in lap_tahun if x.get("laba") is not None]
    try:
        mcap2 = float(rec.get("harga") or 0) * float(rec.get("saham") or 0)
    except (TypeError, ValueError):
        mcap2 = 0
    ncm = ((float(rec.get("kas") or 0) - float(rec.get("utang") or 0)) / mcap2) if mcap2 > 0 else None
    rec["klasifikasi"] = compute_klasifikasi(rec.get("sektor") or "", rec.get("cagr") if rec.get("cagr") else None,
                                             rec.get("dividen") or 0, rec.get("der") or 0, laba_hist, ncm)
    tw2 = compute_thowilz(rec.get("ev_cfo"), rec.get("peg_cfo"), rec.get("cash_badge") or "-",
                          rec.get("margin_stabil") or 0, rec.get("klasifikasi"), len(lap_tahun),
                          rec.get("s_spring") or 0, rec.get("s_sideways") or 0)
    rec["thowilz"] = tw2["thowilz"]

    # Catatan mutu dari laporan itu sendiri
    if kini.get("opini") and "Unqualified" not in str(kini["opini"]):
        catatan.append("opini auditor: %s" % str(kini["opini"]).split("/")[0].strip())
    if len(lap_tahun) < 3:
        catatan.append("riwayat laporan hanya %d tahun" % len(lap_tahun))

    rec["sumber"] = ("IDX Laporan Keuangan %s + Yahoo Finance - %s"
                     % (th, ("; ".join(catatan) if catatan else "kualitas baik")))
    return rec, catatan


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def bidang_csv(v):
    """Satu bidang CSV, dikutip bila memuat koma, titik koma, kutip, atau baris baru.

    Titik koma WAJIB dikutip meski pemisahnya koma. Catatan di kolom "sumber"
    bisa memuat titik koma, dan pembaca di screener memilih satu pemisah saja
    dari baris judul. Tanpa kutip, seluruh kolom sesudahnya bergeser satu dan
    hist_laba ikut hilang tanpa peringatan.

    Sengaja tidak memakai csv.writer: QUOTE_MINIMAL hanya mengutip koma, bukan
    titik koma. Fungsi ini kembar dengan csvLine() di screener-saham-indonesia.html.
    """
    t = "" if v is None else str(v)
    if any(c in t for c in ',;"\r\n'):
        return '"' + t.replace('"', '""') + '"'
    return t


def tulis_csv(path, records):
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        fh.write(",".join(bidang_csv(h) for h in CSV_HEADER) + "\r\n")
        for r in records:
            fh.write(",".join(bidang_csv(r.get(k, "")) for k in CSV_HEADER) + "\r\n")


def main():
    setup_stdout()
    ap = argparse.ArgumentParser(
        description="Tarik data saham IDX otomatis untuk screener (Yahoo Finance + IDX).")
    ap.add_argument("--tickers", help="Daftar kode dipisah koma, mis. BBCA,BBRI,TLKM")
    ap.add_argument("--file", help="Berkas berisi kode saham, satu per baris")
    ap.add_argument("--all", action="store_true", help="Ambil seluruh emiten IDX (lama)")
    ap.add_argument("--out", default="data-idx", help="Nama berkas keluaran (tanpa ekstensi)")
    ap.add_argument("--delay", type=float, default=1.5,
                    help="Jeda antar permintaan Yahoo dalam detik (bawaan 1.5)")
    ap.add_argument("--no-idx", action="store_true",
                    help="Lewati pengambilan profil IDX (nama & sektor dikosongkan)")
    ap.add_argument("--no-cache", action="store_true", help="Abaikan cache profil IDX")
    ap.add_argument("--ringkas", action="store_true", help="Hanya cetak ringkasan akhir")
    ap.add_argument("--pasar", action="store_true",
                    help="HANYA ambil regime pasar (IHSG + likuiditas), tanpa data emiten")
    ap.add_argument("--harian", action="store_true",
                    help="HANYA ambil Stock Summary harian seluruh pasar (Volume/Value/Freq)")
    ap.add_argument("--harian-tanggal", default=None, metavar="YYYYMMDD",
                    help="Tanggal perdagangan, mis. 20261006 (bawaan: hari ini)")
    ap.add_argument("--no-pasar", action="store_true",
                    help="Lewati pengambilan regime pasar")
    ap.add_argument("--pasar-hari", type=int, default=30,
                    help="Jumlah hari untuk rata-rata nilai transaksi IDX (bawaan 30)")
    ap.add_argument("--no-likuiditas", action="store_true",
                    help="Lewati nilai transaksi IDX (lebih cepat, likuiditas jadi manual)")
    ap.add_argument("--no-birate", action="store_true",
                    help="Lewati scraping BI Rate dari SEKI BI (tetap manual)")
    ap.add_argument("--bi-rate", type=float, default=None, metavar="PERSEN",
                    help="Timpa BI Rate secara manual, mis. --bi-rate 5.75")
    ap.add_argument("--laporan", action="store_true",
                    help="Ambil juga laporan keuangan IDX (XBRL xlsx): laba, ekuitas, "
                         "arus kas, kas, dan riwayat laba tahunan yang ASLI")
    ap.add_argument("--laporan-saja", action="store_true",
                    help="HANYA laporan keuangan IDX, lewati Yahoo (jauh lebih cepat)")
    ap.add_argument("--laporan-tahun", default=None,
                    help="Rentang tahun laporan, mis. 2015-2024 (bawaan: 10 tahun terakhir)")
    ap.add_argument("--laporan-delay", type=float, default=1.5,
                    help="Jeda antar permintaan laporan IDX dalam detik (bawaan 1.5)")
    args = ap.parse_args()

    log("=" * 72)
    log(" Penarik data screener saham Indonesia")
    log(" Sumber: IDX (profil/sektor) + Yahoo Finance (harga & fundamental)")
    log("=" * 72)

    f = Fetcher(delay=args.delay)

    # -- daftar emiten -------------------------------------------------------
    prof_all = {}
    if not args.no_idx:
        prof_all = load_idx_profiles(f, use_cache=not args.no_cache)

    if args.all:
        if not prof_all:
            log("[!] --all butuh profil IDX. Jalankan tanpa --no-idx.")
            return 1
        tickers = sorted(prof_all.keys())
    elif args.file:
        with open(args.file, "r", encoding="utf-8") as fh:
            tickers = [x.strip().upper() for x in fh if x.strip() and not x.startswith("#")]
    elif args.tickers:
        tickers = [x.strip().upper() for x in args.tickers.split(",") if x.strip()]
    else:
        tickers = ["BBCA", "BBRI", "TLKM", "ASII", "ANTM", "ADRO", "ICBP", "PTBA"]
        log("[i] Tidak ada --tickers/--file, memakai daftar contoh: %s" % ", ".join(tickers))

    tickers = [t.replace(".JK", "").replace(".jk", "") for t in tickers]
    log("")
    log("Jumlah emiten: %d   |   jeda antar permintaan: %.1fs   |   perkiraan waktu: %.0f menit"
        % (len(tickers), args.delay, len(tickers) * (args.delay + 1.2) / 60.0))
    log("-" * 72)

    # -- laporan keuangan IDX (XBRL) -----------------------------------------
    # Rentang tahun bawaan: 10 tahun terakhir yang sudah diaudit.
    th_akhir = datetime.now().year - 1
    th_awal = th_akhir - 9
    if args.laporan_tahun:
        mt = re.match(r"^(\d{4})\s*-\s*(\d{4})$", args.laporan_tahun.strip())
        if mt:
            th_awal, th_akhir = int(mt.group(1)), int(mt.group(2))
        else:
            th_awal = th_akhir = int(args.laporan_tahun.strip())

    lap_all = {}
    if args.laporan or args.laporan_saja:
        log("")
        log("Laporan keuangan IDX: tahun %d-%d (%d tahun/emiten)"
            % (th_awal, th_akhir, th_akhir - th_awal + 1))
        lap = LaporanIDX(delay=args.laporan_delay)
        if not lap.pemanasan(log_fn=log):
            log("  [!] Cookie sesi Cloudflare tidak didapat.")
            log("      Berkas statis /Portals/0/ kemungkinan dibalas halaman tantangan")
            log("      (HTTP 403). Coba jalankan lagi, atau jeda beberapa menit dulu.")
        for i, kode in enumerate(tickers, 1):
            log("  [%d/%d] %s" % (i, len(tickers), kode))
            lap_all[kode] = lap.histori(kode, th_awal, th_akhir, log_fn=log)
            ada = len(lap_all[kode])
            if not ada:
                log("      [!] tidak ada laporan yang berhasil dibaca")
        log("-" * 72)

        if args.laporan_saja:
            ringkas = {}
            for kode, thn in lap_all.items():
                if not thn:
                    continue
                kini = thn[0]
                ringkas[kode] = {
                    "nama": kini.get("nama"),
                    "sektor_idx": kini.get("sektor_idx"),
                    "tahun": [x["tahun"] for x in thn],
                    "laba": {str(x["tahun"]): x.get("laba") for x in thn},
                    "pendapatan": {str(x["tahun"]): x.get("pendapatan") for x in thn},
                    "ekuitas": {str(x["tahun"]): x.get("ekuitas") for x in thn},
                    "arus_kas_operasi": {str(x["tahun"]): x.get("arus_kas_operasi") for x in thn},
                }
            path = "laporan-idx.json"
            with open(path, "w", encoding="utf-8") as fh:
                json.dump({
                    "dibuat": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
                    "sumber": "IDX GetFinancialReport (reportType=rdf, periode=audit) - XBRL xlsx",
                    "catatan": ("Angka laba = laba yang dapat diatribusikan ke entitas induk, "
                                "konsisten dengan EPS. Satuan asli rupiah penuh."),
                    "tahun": [th_awal, th_akhir],
                    "jumlah": len(ringkas),
                    "emiten": ringkas,
                    "mentah": lap_all,
                }, fh, ensure_ascii=False, indent=2)
            log("")
            log("SELESAI. %d emiten, laporan tersimpan: %s"
                % (len(ringkas), os.path.abspath(path)))
            log("")
            log("Langkah berikutnya: jalankan tanpa --laporan-saja, mis.")
            log("  python fetch-data-idx.py --tickers %s --laporan" % ",".join(tickers[:4]))
            return 0

    # -- login Yahoo ---------------------------------------------------------
    crumb = f._login()
    if not crumb:
        log("[!] Gagal mendapatkan crumb Yahoo. Coba lagi beberapa menit kemudian.")
        return 1
    log("Sesi Yahoo siap.")

    # -- mode harian saja: Stock Summary seluruh pasar -----------------------
    if args.harian:
        from datetime import datetime as _dt
        tgl = args.harian_tanggal or _dt.now().strftime("%Y%m%d")
        data = fetch_stock_summary(f, tgl)
        if not data:
            log("[!] Stock Summary %s kosong/gagal (IDX 403 atau libur). File lama tidak diubah." % tgl)
            return 2
        path = "harian-%s.json" % tgl
        tulis_harian(path, tgl, data)
        log("Harian tersimpan: %s (%d emiten)" % (os.path.abspath(path), len(data)))
        return 0

    # -- mode pasar saja: tidak perlu menarik data emiten --------------------
    if args.pasar:
        pasar = ambil_pasar(f, args)
        pasar["sektor"] = []
        with open("pasar.json", "w", encoding="utf-8") as fh:
            json.dump(pasar, fh, ensure_ascii=False, indent=2)
        log("")
        log("Regime pasar disimpan: %s" % os.path.abspath("pasar.json"))
        log("Langkah berikutnya: buka screener-saham-indonesia.html, buka Langkah 1,")
        log("lalu klik 'Muat regime pasar' dan pilih pasar.json")
        return 0

    # -- tarik per emiten ----------------------------------------------------
    records, gagal, meragukan = [], [], []
    t0 = time.time()
    for i, kode in enumerate(tickers, 1):
        prof = prof_all.get(kode)
        fund = fetch_fundamental(f, kode)
        time.sleep(args.delay * 0.5)
        ch = fetch_chart(f, kode)

        if not fund and not ch:
            gagal.append(kode)
            log("[%3d/%3d] %-6s TIDAK ADA DATA" % (i, len(tickers), kode))
            time.sleep(args.delay)
            continue

        rec = build_record(kode, prof, fund, ch, args)

        # Timpa angka turunan Yahoo dengan laporan keuangan IDX yang asli.
        if lap_all.get(kode):
            rec, catatan_lap = gabung_laporan(rec, lap_all[kode])
            rec["_catatan"] = (rec["_catatan"] or []) + catatan_lap

        # Return 6 bulan dipakai untuk menghitung kekuatan sektor (Langkah 1).
        rec["_ret6"] = None
        if ch and ch.get("close") and len(ch["close"]) > 21:
            c = ch["close"]
            n = min(126, len(c) - 1)
            if c[-n - 1]:
                rec["_ret6"] = round((c[-1] / c[-n - 1] - 1) * 100.0, 2)
        records.append(rec)
        if rec["_catatan"]:
            meragukan.append(rec)
        if not args.ringkas:
            log("[%3d/%3d] %-6s %-26s harga %-9s EPS %-9s PBV %-6s %s"
                % (i, len(tickers), kode, rec["nama"][:26], rec["harga"], rec["eps"],
                   ("%.2f" % (rec["harga"] * rec["saham"] / rec["ekuitas"]))
                   if rec["ekuitas"] > 0 else "-",
                   ("!" + rec["_catatan"][0]) if rec["_catatan"] else "ok"))
        time.sleep(args.delay)

    # -- regime pasar (Langkah 1) --------------------------------------------
    pasar = None
    if not args.no_pasar:
        pasar = ambil_pasar(f, args)
        pasar["sektor"] = hitung_sektor(records)
        with open("pasar.json", "w", encoding="utf-8") as fh:
            json.dump(pasar, fh, ensure_ascii=False, indent=2)
        if pasar["sektor"]:
            log("  Kekuatan sektor (dari %d emiten yang ditarik):" % len(records))
            for s in pasar["sektor"][:6]:
                log("    %-24s %+7.2f%%  (%d emiten)"
                    % (s["sektor"], s["rata_return"], s["jumlah"]))

    # -- tulis keluaran ------------------------------------------------------
    log("-" * 72)
    if not records:
        log("[!] Tidak ada data yang berhasil ditarik.")
        return 1

    csv_path = args.out + ".csv"
    tulis_csv(csv_path, records)


    json_path = args.out + ".json"
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump({
            "dibuat": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            "sumber": "IDX GetCompanyProfiles + Yahoo Finance (chart & quoteSummary)",
            "catatan": ("Ekuitas diturunkan dari BVPS x saham beredar. "
                        "s_topbuyer tidak tersedia di sumber gratis, isi manual."),
            "jumlah": len(records),
            "saham": [{k: v for k, v in r.items() if not k.startswith("_")} for r in records],
        }, fh, ensure_ascii=False, indent=2)

    log("")
    log("SELESAI dalam %.1f menit. %d emiten berhasil, %d gagal."
        % ((time.time() - t0) / 60.0, len(records), len(gagal)))
    log("  CSV  : %s" % os.path.abspath(csv_path))
    log("  JSON : %s" % os.path.abspath(json_path))
    if pasar:
        log("  PASAR: %s" % os.path.abspath("pasar.json"))
    if gagal:
        log("  Gagal: %s" % ", ".join(gagal))
    if meragukan:
        log("")
        log("  %d emiten perlu dicek manual:" % len(meragukan))
        for r in meragukan[:15]:
            log("    %-6s %s" % (r["kode"], "; ".join(r["_catatan"])))
        if len(meragukan) > 15:
            log("    ... dan %d lainnya (lihat kolom 'sumber' di CSV)"
                % (len(meragukan) - 15))
    log("")
    log("Langkah berikutnya: buka screener-saham-indonesia.html lalu klik")
    log("'Import CSV/JSON' dan pilih %s" % csv_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
