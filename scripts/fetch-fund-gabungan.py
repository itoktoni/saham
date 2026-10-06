#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fetch-fund-gabungan.py: fundamental gabungan sesaham + IndoPremier (stdlib)."""
import json
import re
import time
import urllib.request
from datetime import datetime
from html.parser import HTMLParser

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
CACHE_FILE = "fund-gabungan.json"
SS_BASE = "https://sesaham.com"
IP_BASE = "https://www.indopremier.com/module/saham/include/fundamental.php"


def _unduh(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def parse_persen(s):
    s = (s or "").strip()
    if not s or s in ("—", "-", "--"):
        return None
    s = s.replace("%", "").replace(",", ".").strip()
    try:
        return round(float(s), 2)
    except ValueError:
        return None


def parse_rp(s):
    s = (s or "").strip().upper()
    if not s or s in ("—", "-", "--"):
        return None
    m = 1
    if s.endswith(" T"):
        m, s = 1000000000000, s[:-2]
    elif s.endswith(" M"):
        m, s = 1000000, s[:-2]
    elif s.endswith(" JUTA"):
        m, s = 1000000, s.replace(" JUTA", "")
    elif s.endswith(" JT"):
        m, s = 1000000, s[:-3]
    s = s.replace(".", "").replace(",", ".").strip()
    try:
        return int(float(s) * m)
    except ValueError:
        return None


def parse_biasa(s):
    s = (s or "").strip()
    if not s or s in ("—", "-", "--"):
        return None
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def pairs_sesaham(html):
    out = {}
    for a, b in re.findall(r"<span[^>]*>([^<>]{1,80})</span>\s*<span[^>]*>([^<>]{1,40})</span>", html):
        out[a.strip()] = b.strip()
    return out


class _Baris(HTMLParser):
    """Kumpulkan <tr> -> list sel teks (+ href /emiten/ bila ada)."""

    def __init__(self):
        super().__init__()
        self.baris, self._td, self._tr, self._hrefs = [], [], False, []

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._tr, self._td, self._hrefs = True, [], []
        if tag == "td" and self._tr:
            self._td.append("")
        if tag == "a" and self._tr:
            for k, v in attrs:
                if k == "href":
                    self._hrefs.append(v)

    def handle_data(self, data):
        if self._tr and self._td:
            self._td[-1] += data

    def handle_endtag(self, tag):
        if tag == "tr" and self._tr:
            self.baris.append(([t.strip() for t in self._td], list(self._hrefs)))
            self._tr = False


def parse_kas(html):
    """Deret OCF/FCF/dividen: [TTM, 2025, ...] sedapatnya."""
    out = {}
    t = _Baris()
    t.feed(html)
    for sel, _ in t.baris:
        if not sel:
            continue
        nama = sel[0].lower()
        key = None
        if "operasi" in nama:
            key = "ocf"
        elif "bebas" in nama or "(fcf)" in nama:
            key = "fcf"
        elif "dividen dibayar" in nama:
            key = "dividen"
        if key:
            out[key] = [parse_rp(x) for x in sel[1:]]
    return out


def _seksi(html, mulai, berhenti):
    i = html.find(mulai)
    if i < 0:
        return ""
    j = len(html)
    for b in berhenti:
        k = html.find(b, i + len(mulai))
        if k >= 0:
            j = min(j, k)
    return html[i:j]


def parse_klasifikasi(html):
    seg = _seksi(html, "Klasifikasi", ["Info Umum", "Tentang Perusahaan"])
    out = {"sektor": [], "industri": [], "bisnis": [], "komoditas": []}
    for href, teks in re.findall(r'<a[^>]*href="(?:https://sesaham\.com)?(/sektor/[^"]+|/peta-industri/[^"]+|/peta-lini-bisnis/[^"]+|/peta-produk-komoditas/[^"]+)"[^>]*>([^<>]+)</a>', seg):
        if href.startswith("/sektor/"):
            out["sektor"].append(teks.strip())
        elif href.startswith("/peta-industri/"):
            out["industri"].append(teks.strip())
        elif href.startswith("/peta-lini-bisnis/"):
            out["bisnis"].append(teks.strip())
        else:
            out["komoditas"].append(teks.strip())
    for k in out:
        unik, lihat = [], set()
        for x in out[k]:
            if x not in lihat:
                lihat.add(x)
                unik.append(x)
        out[k] = unik
    return out


def parse_sejenis(html, kode):
    seg = _seksi(html, "Emiten Sejenis", ["Rasio", "Valuasi", "Navigasi", "<footer"])
    out = []
    for m in re.finditer(r"/emiten/([A-Za-z0-9]{3,5})", seg):
        kk = m.group(1).upper()
        if kk != kode and kk not in out:
            out.append(kk)
    return out


def parse_ip(html):
    """Tabel fundamental IP -> {label: [...]}. IP pakai desimal TITIK
    ("582.59", "2.47 %") dan koma ribuan ("58,700") — kebalikan sesaham."""
    t = _Baris()
    t.feed(html)
    out = {}
    for sel, _ in t.baris:
        if not sel:
            continue
        vals = []
        for x in sel[1:]:
            x = (x or "").strip().rstrip("x").strip()
            if not x or x in ("—", "-", "--"):
                vals.append(None)
            else:
                try:
                    vals.append(float(x.replace(",", "")))
                except ValueError:
                    vals.append(None)
        if vals:
            out[sel[0]] = vals
    return out


def tren_ip(seri):
    s = [x for x in (seri or []) if x is not None]
    if len(s) < 6:
        return None
    gerak = [1 if b > a else (-1 if b < a else 0) for a, b in zip(s, s[1:])]
    if sum(1 for g in gerak[-7:] if g > 0) >= 5:
        return "naik"
    if sum(1 for g in gerak[-7:] if g < 0) >= 5:
        return "turun"
    return "datar"


def ambil_fund(kode, timeout=30):
    kode = str(kode).strip().upper()
    ent = {"nilai": {}, "sumber": {}, "flag": [], "tren": {}, "kas": {},
           "fv_graham": 0, "klasifikasi": {}, "sejenis": []}
    try:
        hss = _unduh("%s/emiten/%s" % (SS_BASE, kode), timeout=timeout)
    except Exception as e:  # noqa: BLE001
        return ent, ["sesaham: %s" % str(e)[:80]]
    gagal = []
    p = pairs_sesaham(hss)
    for label, kunci, fn in (("ROE (TTM)", "roe", parse_persen),
                             ("EPS (TTM)", "eps", parse_biasa),
                             ("Debt to Equity Ratio (DER)", "der", parse_persen),
                             ("Current Price to Book Value", "pbv", parse_biasa),
                             ("Book Value per Share", "bvps", parse_biasa)):
        v = fn(p.get(label, ""))
        if v is not None:
            ent["nilai"][kunci] = v
            ent["sumber"][kunci] = "SS"
    ent["fv_graham"] = parse_biasa(p.get("Fair Value (Graham Number)", "")) or 0
    ent["kas"] = parse_kas(hss)
    ent["klasifikasi"] = parse_klasifikasi(hss)
    ent["sejenis"] = parse_sejenis(hss, kode)
    try:
        hip = _unduh("%s?code=%s&quarter=5" % (IP_BASE, kode), timeout=timeout)
        tab = parse_ip(hip)
        for label, kunci, skala in (("ROE", "roe", 1), ("EPS", "eps", 1),
                                    ("Debt/Equity", "der", 100)):
            seri = tab.get(label)
            if seri and seri[0] is not None:
                ent["nilai"][kunci] = round(seri[0] * skala, 2)
                ent["sumber"][kunci] = "IP"
                t = tren_ip(seri)
                if t:
                    ent["tren"][kunci] = t
    except Exception as e:  # noqa: BLE001
        gagal.append("ip: %s" % str(e)[:80])
    return ent, gagal


def ambil_semua(kodes, log_fn=None, delay=2.0, tulis_cache=True):
    log = log_fn or (lambda m: None)
    emiten, gagal = {}, []
    for kode in (kodes or []):
        try:
            ent, g = ambil_fund(kode)
            emiten[kode] = ent
            gagal.extend(["%s %s" % (kode, x) for x in g])
            log("%s ok" % kode)
        except Exception as e:  # noqa: BLE001
            gagal.append("%s: %s" % (kode, str(e)[:80]))
        time.sleep(delay)
    if tulis_cache:
        try:
            lama = {}
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as fh:
                    lama = json.load(fh) or {}
            except (OSError, json.JSONDecodeError):
                lama = {}
            gab = dict((lama.get("emiten") or {}))
            gab.update(emiten)
            hasil = {"diambil": datetime.now().astimezone().isoformat(timespec="seconds"),
                     "emiten": gab, "gagal": gagal}
            with open(CACHE_FILE, "w", encoding="utf-8") as fh:
                json.dump(hasil, fh, ensure_ascii=False)
        except OSError:
            pass
    hasil = {"diambil": datetime.now().astimezone().isoformat(timespec="seconds"),
             "emiten": emiten, "gagal": gagal}
    return hasil


if __name__ == "__main__":
    import sys
    out = ambil_semua([a.strip().upper() for a in sys.argv[1:] if a.strip()] or ["BBCA"])
    print("emiten: %d, gagal: %d" % (len(out["emiten"]), len(out["gagal"])))
