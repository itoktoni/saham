#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fetch-tema.py: peta tema dari sesaham.com (scrape sopan + cache lama)."""
import json
import time
import urllib.request
from datetime import datetime
from html.parser import HTMLParser

BASE = "https://sesaham.com"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
CACHE_FILE = "tema.json"

HALAMAN = [
    ("Oil & Coal", ["peta-produk-komoditas/coal", "peta-produk-komoditas/crude-oil",
                    "peta-produk-komoditas/lignite", "peta-industri/minyak-gas"],
     "Energi fosil: batu bara, minyak, gas."),
    ("Gold", ["peta-produk-komoditas/gold", "peta-produk-komoditas/gold-ore"],
     "Emas dan bijih emas."),
    ("Nickel", ["peta-produk-komoditas/nickel-ore", "peta-produk-komoditas/nickel-matte"],
     "Nikel dan turunannya untuk baterai/EV."),
    ("Data Center & AI", ["peta-produk-komoditas/data-center",
                           "peta-industri/aplikasi-jasa-internet"],
     "Infrastruktur digital: data center, layanan internet/TI."),
]


class _Tabel(HTMLParser):
    def __init__(self):
        super().__init__()
        self.baris, self._td, self._href, self._tr = [], [], None, False

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._tr, self._td, self._href = True, [], None
        if tag == "td" and self._tr:
            self._td.append("")
        if tag == "a" and self._tr:
            for k, v in attrs:
                if k == "href" and v.startswith("/emiten/"):
                    self._href = v.split("/")[-1].strip().upper()

    def handle_data(self, data):
        if self._tr and self._td:
            self._td[-1] += data

    def handle_endtag(self, tag):
        if tag == "tr" and self._tr:
            if self._href and self._td:
                self.baris.append((self._href, [t.strip() for t in self._td]))
            self._tr = False


def parse_id(s):
    s = (s or "").strip()
    if not s or s in ("—", "-", "--"):
        return 0
    s = s.replace(".", "").replace(",", ".")
    try:
        return int(float(s))
    except ValueError:
        return 0


def _unduh(slug, timeout=30):
    req = urllib.request.Request(BASE + "/" + slug, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def ambil_tema(log_fn=None, delay=2.0):
    log = log_fn or (lambda m: None)
    gab, gagal = {}, []
    for nama, slugs, desk in HALAMAN:
        emiten, wajar = [], {}
        for slug in slugs:
            try:
                t = _Tabel()
                t.feed(_unduh(slug))
                for kode, sel in t.baris:
                    if kode not in emiten:
                        emiten.append(kode)
                    w = parse_id(sel[-1]) if sel else 0
                    if w > 0:
                        wajar[kode] = w
                log("%s: %d baris" % (slug, len(t.baris)))
            except Exception as e:  # noqa: BLE001
                gagal.append("%s: %s" % (slug, str(e)[:80]))
            time.sleep(delay)
        gab[nama] = {"nama": nama, "deskripsi": desk, "sumber": slugs,
                     "emiten": emiten, "wajar": wajar}
    hasil = {"diambil": datetime.now().astimezone().isoformat(timespec="seconds"),
             "tema": list(gab.values()), "gagal": gagal}
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as fh:
            json.dump(hasil, fh, ensure_ascii=False)
    except OSError:
        pass
    return hasil


if __name__ == "__main__":
    out = ambil_tema()
    print("tema: %d, gagal: %d" % (len(out["tema"]), len(out["gagal"])))
