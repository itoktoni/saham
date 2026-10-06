#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fetch-brokersum.py: broker summary IndoPremier -> SQLite + respons scope-shape."""
import json
import re
import sqlite3
import sys
import time
import urllib.request
from datetime import datetime, timedelta
from html.parser import HTMLParser

BASE = "https://www.indopremier.com/module/saham/include/data-brokersummary.php"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
DB_FILE = "saham.db"

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
    c.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in c.execute(
            "SELECT broker,sisi,lot,val_rp AS val,avg FROM broker_summary WHERE kode=? AND tgl_awal=? AND tgl_akhir=?", (kode, awal, akhir)).fetchall()]
    except Exception:
        return []
    finally:
        try:
            c.close()
        except Exception:
            pass


def parse_nom(s):
    s = (s or "").strip().upper().replace("RP", "").strip()
    if not s or s in ("—", "-", "--"):
        return 0
    m = 1
    if s.endswith("B"):
        m, s = 1000000000, s[:-1]
    elif s.endswith("M"):
        m, s = 1000000, s[:-1]
    elif s.endswith("K"):
        m, s = 1000, s[:-1]
    s = s.replace(",", "")
    try:
        return int(float(s) * m)
    except ValueError:
        return 0


def parse_int(s):
    if s and re.search(r"[BMK]$", (s or "").strip().upper()):
        return parse_nom(s)
    try:
        return int((s or "0").replace(",", "").strip() or 0)
    except ValueError:
        return 0


class _Sum(HTMLParser):
    def __init__(self):
        super().__init__()
        self.baris, self._td, self._tr = [], [], False

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._tr, self._td = True, []
        if tag == "td" and self._tr:
            self._td.append("")

    def handle_data(self, data):
        if self._tr and self._td:
            self._td[-1] += data

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
        t = _Sum()
        t.feed(r.read().decode("utf-8", "replace"))
    buy, sell = [], []
    for c in t.baris:
        try:
            buy.append({"broker": c[0], "lot": parse_int(c[1]), "val": parse_nom(c[2]), "avg": parse_int(c[3])})
            sell.append({"broker": c[5], "lot": parse_int(c[6]), "val": parse_nom(c[7]), "avg": parse_int(c[8])})
        except (IndexError, ValueError):
            continue
    return {"kode": kode, "tgl_awal": awal, "tgl_akhir": akhir, "buyers": buy, "sellers": sell}


def _fmt_us(dt):
    return dt.strftime("%m/%d/%Y")


if __name__ == "__main__":
    kodes = [a.strip().upper() for a in sys.argv[1:] if a.strip()] or ["BBCA"]
    akhir = datetime.now()
    awal = akhir - timedelta(days=30)
    awal_iso, akhir_iso = awal.strftime("%Y-%m-%d"), akhir.strftime("%Y-%m-%d")
    for kode in kodes:
        if db_ada(DB_FILE, kode, awal_iso, akhir_iso):
            print("%s: skip (DB)" % kode)
            continue
        try:
            snap = ambil_satu(kode, _fmt_us(awal), _fmt_us(akhir))
            snap["tgl_awal"], snap["tgl_akhir"] = awal_iso, akhir_iso
            n = db_simpan(DB_FILE, snap)
            print("%s: %d buyer, %d seller, %d baris DB" % (kode, len(snap["buyers"]), len(snap["sellers"]), n))
        except Exception as e:  # noqa: BLE001
            print("%s: gagal %s" % (kode, str(e)[:100]))
        time.sleep(2.0)
