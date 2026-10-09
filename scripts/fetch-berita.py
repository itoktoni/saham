#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fetch-berita.py: berita + sentimen per emiten (gratis, tanpa API key).

Sumber: RSS Google News (query "<KODE> saham Indonesia") + RSS umum
CNBC Indonesia (Kontan dibuang — gagal SSL handshake). Semua via stdlib saja.

Keluaran (berita.json):
{
  "diambil": "...",
  "emiten": {
    "BBCA": {"n": 12, "sentimen": 68, "label": "Positif",
              "buzz": "Ramai", "top": [{"judul":..,"link":..,"tgl":..,"sumber":..,"skor":..}]},
    ...
  },
  "umum": [ ... berita pasar umum ... ],
  "gagal": [...]
}

Sentimen: leksikon Indonesia sederhana (positif/negatif) di judul (+ ringkasan
bila judul netral). Polarisasi per berita (positif/negatif/netral) lalu
dirangkum dengan sentimen = 100 * (pos + 0,5) / (pos + neg + 1) — rentang
penuh 0..100, netral 50, tanpa bias ke salah satu kutub.

Buzz = jumlah berita SEGAR (<= HARI_SEGAR hari) yang menyebut kode di judul:
Ramai (>=10) / Normal (3-9) / Sepi (1-2) / Tanpa berita (0) -> n=0.
Pool RSS berisi +/-100 item campur usia, jadi tanpa filter usia SEMUA saham
kelihatan "Ramai" dan sentimen semua saham mendekati 50 (tidak membedakan).
"""

import email.utils
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from xml.etree import ElementTree as ET

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
CACHE_FILE = "berita.json"   # arsip saja; aplikasi selalu fetch segar (tanpa baca cache)
HARI_SEGAR = 7      # berita lebih tua dari ini dianggap basi (tidak ikut skor)
BUZZ_RAMAI = 10     # >=10 berita segar = Ramai
BUZZ_NORMAL = 3     # 3-9 = Normal, 1-2 = Sepi, 0 = tanpa story (nilai 0)

RSS_UMUM = [
    ("CNBC-Market", "https://www.cnbcindonesia.com/market/rss"),
]

POSITIF = ["naik", "menguat", "melonjak", "rekor", "tertinggi", "untung", "laba naik",
           "tumbuh", "ekspansi", "akuisisi", "dividen", "buyback", "positif",
           "bullish", "cuan", "top", "kinerja solid", "prospek cerah", "target naik",
           "rekomendasi beli", "overweight", "upgrade", "kontrak baru", "rupiah menguat",
           "ihsg naik", "ihsg menguat", "kinclong", "meroket", "melambung", "jackpot",
           "membaik", "meningkat", "surplus", "merekor", "tertinggi sepanjang"]
NEGATIF = ["turun", "melemah", "anjlok", "ambles", "rugi", "merugi", "gagal",
           "skandal", "fraud", "korupsi", "denda", "suspend", "suspensi", "bearish",
           "jual", "downgrade", "underweight", "rekomendasi jual", "koreksi",
           "phk", "utang bermasalah", "gagal bayar", "waspada", "risiko",
           "ihsg turun", "ihsg melemah", "longsor", "terjun", "boncos", "nyangkut",
           "menurun", "penurunan", "pelemahan", "merosot", "terpuruk", "pailit",
           "bangkrut", "defisit", "gugatan", "menjual", "dijual"]


def _unduh(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _umur_hari(tgl):
    """Umur pubDate (RFC 822) dalam hari, atau None bila tak terbaca."""
    try:
        d = email.utils.parsedate_to_datetime(tgl)
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return max(0, (datetime.now(timezone.utc) - d).total_seconds() / 86400.0)
    except (TypeError, ValueError, OverflowError):
        return None


def _parse_rss(raw):
    """Kembalikan [(judul, link, tgl, sumber, ringkasan)]. Tahan banting."""
    out = []
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return out
    for item in root.iter("item"):
        def txt(tag):
            el = item.find(tag)
            return (el.text or "").strip() if el is not None and el.text else ""
        judul = txt("title")
        if not judul:
            continue
        link = txt("link")
        tgl = txt("pubDate")
        desc = re.sub(r"<[^>]+>", " ", txt("description"))
        desc = re.sub(r"\s+", " ", desc).strip()[:400]
        sumber = ""
        src = item.find("source")
        if src is not None and src.text:
            sumber = src.text.strip()[:60]
        out.append({"judul": judul, "link": link, "tgl": tgl,
                    "sumber": sumber, "ringkas": desc})
    return out


def _selang(kalimat):
    """Pola kata-batas per leksikon — cegah 'penjualan' kena 'jual',
    'menopang' kena 'top', dsb."""
    return re.sub(r"[^a-z0-9 ]+", " ", (kalimat or "").lower())


_POS_RE = None
_NEG_RE = None


def _pola():
    global _POS_RE, _NEG_RE
    if _POS_RE is None:
        def buat(lst):
            return re.compile(r"\b(?:" + "|".join(re.escape(w) for w in sorted(lst, key=len, reverse=True)) + r")\b")
        _POS_RE, _NEG_RE = buat(POSITIF), buat(NEGATIF)
    return _POS_RE, _NEG_RE


def skor_berita(teks):
    """Skor -100..+100: jumlah kata positif vs negatif, cap +-100."""
    t = _selang(teks)
    rp, rn = _pola()
    pos = len(rp.findall(t))
    neg = len(rn.findall(t))
    # bobot: tiap kata +-25, cap +-100
    return max(-100, min(100, (pos - neg) * 25))


def buzz_dari(n):
    """Ramai >=10 berita segar · Normal 3-9 · Sepi 1-2 · 0 = tanpa story."""
    if n >= BUZZ_RAMAI:
        return "Ramai"
    return "Normal" if n >= BUZZ_NORMAL else "Sepi"


def sentimen_rangkum(pakai):
    """Gabung polaritas per berita -> 0..100 (50 = netral).

    Pembobotan Laplace (pos+0,5)/(pos+neg+1) supaya 1 berita positif tunggal
    tidak langsung memuncak 100 dan berita netral tetap 50.
    """
    pos = sum(1 for it in pakai if (it.get("skor") or 0) > 0)
    neg = sum(1 for it in pakai if (it.get("skor") or 0) < 0)
    if not pos and not neg:
        return 50
    return round(100.0 * (pos + 0.5) / (pos + neg + 1))


def _gn_url(kode):
    q = urllib.parse.quote("%s saham Indonesia" % kode)
    return ("https://news.google.com/rss/search?q=%s"
            "&hl=id&gl=ID&ceid=ID:id" % q)


def ambil_berita(kodes, log_fn=None, delay=1.0, tulis_cache=True):
    log = log_fn or (lambda m: None)
    kodes = [str(k).strip().upper().replace(".JK", "") for k in (kodes or []) if str(k).strip()]
    emiten, gagal, umum = {}, [], []
    # 1. RSS umum (konteks pasar, 1x saja)
    for nama, url in RSS_UMUM:
        try:
            items = _parse_rss(_unduh(url))[:15]
            for it in items:
                it["sumber"] = it["sumber"] or nama
                it["skor"] = skor_berita(it["judul"] + " " + it["ringkas"])
            umum.extend(items)
            log("%s: %d berita" % (nama, len(items)))
        except Exception as e:  # noqa: BLE001
            gagal.append("%s: %s" % (nama, str(e)[:80]))
        time.sleep(0.5)
    # 2. Per emiten via Google News RSS (pool +/-100 item campur usia)
    for kode in kodes:
        try:
            items = _parse_rss(_unduh(_gn_url(kode)))
            # Hanya berita SEGAR (<= HARI_SEGAR hari) yang menyebut kode di judul:
            # itu yang membentuk story. Sisanya dianggap basi/noise.
            segar, pool = [], []
            for it in items:
                u = _umur_hari(it["tgl"])
                it["umur"] = u
                if u is None or u > HARI_SEGAR:
                    continue
                segar.append(it)
                if kode in it["judul"].upper():
                    pool.append(it)
            pool.sort(key=lambda i: i["umur"])
            pakai = pool[:15]
            n = len(pool)
            if not n:
                # Tidak ada berita segar tentang kode ini -> tanpa story (0).
                emiten[kode] = {"n": 0, "sentimen": 50, "label": "Netral",
                                "buzz": "Sepi", "top": []}
                log("%s: 0 berita segar (%d berita segar tanpa sebutan kode)"
                    % (kode, len(segar)))
            else:
                for it in pakai:
                    # Judul dulu (lebih satu arah); judul+ringkas bila judul netral.
                    it["skor"] = skor_berita(it["judul"]) or skor_berita(
                        it["judul"] + " " + it["ringkas"])
                sent = sentimen_rangkum(pakai)
                label = "Positif" if sent >= 60 else ("Negatif" if sent < 40 else "Netral")
                buzz = buzz_dari(n)
                emiten[kode] = {
                    "n": n, "sentimen": sent, "label": label, "buzz": buzz,
                    "top": [{k2: it[k2] for k2 in ("judul", "link", "tgl", "sumber", "skor")}
                            for it in pakai[:5]]}
                log("%s: %d berita segar, sentimen %d (%s), buzz %s"
                    % (kode, n, sent, label, buzz))
        except Exception as e:  # noqa: BLE001
            gagal.append("%s: %s" % (kode, str(e)[:80]))
            emiten[kode] = {"n": 0, "sentimen": 50, "label": "Netral", "buzz": "Sepi", "top": []}
        time.sleep(delay)
    hasil = {"diambil": datetime.now().astimezone().isoformat(timespec="seconds"),
             "emiten": emiten, "umum": umum[:30], "gagal": gagal}
    if tulis_cache:
        # Arsip saja (tidak pernah dibaca aplikasi — tiap aksi selalu fetch segar).
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as fh:
                json.dump(hasil, fh, ensure_ascii=False)
        except OSError:
            pass
    return hasil


if __name__ == "__main__":
    import sys
    out = ambil_berita([a.upper() for a in sys.argv[1:]] or ["BBCA", "TLKM"])
    print("emiten: %d, umum: %d, gagal: %d" % (len(out["emiten"]), len(out["umum"]), len(out["gagal"])))
