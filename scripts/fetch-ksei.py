#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch-ksei.py
=============
Penarik KEPEMILIKAN EFEK KSEI (Lokal vs Asing) per emiten -> ksei.json

Sumber gratis resmi (tanpa login, tanpa Cloudflare):
    https://web.ksei.co.id/archive_download/holding_composition
    file:  /Download/BalanceposEfekYYYYMMDD.zip  ->  BalanceposYYYYMMDD.txt
    format pipe-delimited: tanggal|kode|tipe|jumlah_saham|harga|lokal...|total|lokal...|total

Keluaran ksei.json memuat, per emiten:
  - saham, harga (dari KSEI, harga akhir bulan)
  - asing_pct, lokal_pct, ritel_pct, institusi_pct
  - asing_pct_prev, dksei_asing_1m, dksei_institusi_1m   (perubahan bulan lalu)

Tanpa pustaka tambahan (hanya standard library). KSEI mengirim teks biasa,
jadi urllib cukup; curl dipakai sebagai cadangan.
"""

import calendar
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile
from datetime import datetime, timedelta

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
ARCHIVE_URL = "https://web.ksei.co.id/archive_download/holding_composition"
CURL = shutil.which("curl") or shutil.which("curl.exe")
CACHE_DIR = "cache-ksei"

# Bila dijalankan langsung, taruh keluaran di folder data/ proyek (bukan cwd).
_BASE = os.path.dirname(os.path.abspath(__file__))
_DATA = os.path.join(os.path.dirname(_BASE), "data")
if os.path.isdir(_DATA):
    os.chdir(_DATA)


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


def _get(url, biner=False, timeout=60):
    """GET via urllib; cadangan curl bila urllib ditolak."""
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "*/*",
        "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read()
        return data if biner else data.decode("utf-8", "replace")
    except Exception as e:
        log("    [i] urllib gagal (%s), coba curl..." % str(e)[:80])
    if not CURL:
        return None
    cmd = [CURL, "-s", "-L", "-m", str(timeout), "-A", UA, url]
    try:
        p = subprocess.run(cmd, capture_output=True, timeout=timeout + 20)
    except Exception:
        return None
    if p.returncode != 0 or not p.stdout:
        return None
    return p.stdout if biner else p.stdout.decode("utf-8", "replace")


def daftar_zip(html):
    """Ambil daftar (tanggal, url) dari halaman arsip, urut terbaru dulu."""
    pola = re.compile(r"/Download/BalanceposEfek(\d{8})\.zip")
    out = {}
    for m in pola.finditer(html or ""):
        tgl = m.group(1)
        out[tgl] = "/Download/BalanceposEfek%s.zip" % tgl
    return [(t, u) for t, u in sorted(out.items(), reverse=True)]


def _coba_unduh(rel_url):
    """Unduh satu URL; kembalikan bytes bila benar-benar ZIP (PK), selain itu None."""
    data = _get("https://web.ksei.co.id" + rel_url, biner=True, timeout=120)
    return data if (data and data[:2] == b"PK") else None


def _resolve_bulan(yy, mm, log_fn=None):
    """Cari tanggal hari bursa terakhir bulan (yy,mm) yang berkas KSEI-nya ada.

    Berkas KSEI dinamai tanggal hari bursa terakhir bulan (bisa mundur karena
    akhir pekan/libur), jadi coba beberapa hari ke belakang.
    """
    last = calendar.monthrange(yy, mm)[1]
    d = datetime(yy, mm, last)
    while d.weekday() >= 5:          # Sabtu/Minggu -> mundur
        d -= timedelta(days=1)
    for _ in range(7):
        tgl = d.strftime("%Y%m%d")
        rel = "/Download/BalanceposEfek%s.zip" % tgl
        tujuan = os.path.join(CACHE_DIR, "BalanceposEfek%s.zip" % tgl)
        if os.path.exists(tujuan) and os.path.getsize(tujuan) > 50000:
            return tgl, rel
        data = _coba_unduh(rel)
        if data:
            if not os.path.isdir(CACHE_DIR):
                os.makedirs(CACHE_DIR, exist_ok=True)
            with open(tujuan, "wb") as fh:
                fh.write(data)
            return tgl, rel
        d -= timedelta(days=1)
    if log_fn:
        log_fn("  [!] berkas %02d/%d tidak ditemukan" % (mm, yy))
    return None


def daftar_bulan(n=24, log_fn=None):
    """Daftar berkas KSEI `n` bulan terakhir (mulai bulan lalu), terbaru dulu."""
    y, m = datetime.now().year, datetime.now().month
    m -= 1
    if m == 0:
        m, y = 12, y - 1
    out = []
    for _ in range(max(1, n)):
        got = _resolve_bulan(y, m, log_fn)
        if got:
            out.append(got)
        m -= 1
        if m == 0:
            m, y = 12, y - 1
    out.sort(reverse=True)
    return out


def unduh_zip(rel_url, log_fn=None):
    """Unduh (dengan cache) satu berkas zip KSEI, kembalikan path lokal."""
    if not os.path.isdir(CACHE_DIR):
        os.makedirs(CACHE_DIR, exist_ok=True)
    nama = os.path.basename(rel_url)
    tujuan = os.path.join(CACHE_DIR, nama)
    if os.path.exists(tujuan) and os.path.getsize(tujuan) > 50000:
        return tujuan
    url = "https://web.ksei.co.id" + rel_url
    data = _get(url, biner=True, timeout=120)
    if not data or data[:2] != b"PK":
        return None
    with open(tujuan, "wb") as fh:
        fh.write(data)
    return tujuan


def parse_zip(path):
    """Baca BalanceposYYYYMMDD.txt di dalam zip -> {kode: {...}}."""
    z = zipfile.ZipFile(path)
    nama = None
    for n in z.namelist():
        if n.lower().endswith(".txt"):
            nama = n
            break
    if not nama:
        return {}
    teks = z.read(nama).decode("utf-8", "replace")
    baris = teks.splitlines()
    if not baris:
        return {}
    hasil = {}
    for ln in baris[1:]:
        p = ln.split("|")
        if len(p) < 25:
            continue
        tipe = p[2].strip().upper()
        if tipe and tipe != "EQUITY":
            continue
        kode = p[1].strip().upper()
        if not kode:
            continue

        def ang(v):
            try:
                return float(v)
            except (TypeError, ValueError):
                return 0.0

        saham = ang(p[3])
        harga = ang(p[4])
        lokal_total = ang(p[14])
        asing_total = ang(p[24])
        ritel = ang(p[9])  # Local ID = individu domestik
        total = lokal_total + asing_total
        if total <= 0:
            total = saham
        if total <= 0:
            continue
        hasil[kode] = {
            "saham": int(round(saham)) if saham else 0,
            "harga_ksei": harga,
            "asing_pct": round(asing_total / total * 100.0, 3),
            "lokal_pct": round(lokal_total / total * 100.0, 3),
            "ritel_pct": round(ritel / total * 100.0, 3),
            "institusi_pct": round((lokal_total - ritel) / total * 100.0, 3),
            "asing_saham": int(round(asing_total)),
            "lokal_saham": int(round(lokal_total)),
        }
    return hasil


def ambil_ksei(log_fn=None, bulan=24):
    """Ambil kepemilikan KSEI beberapa bulan terakhir + estimasi harga rata-rata asing.

    - `emiten[kode]["asing_avg_price"]`: estimasi biaya rata-rata asing, dihitung
      dari perubahan jumlah lembar asing antar bulan x harga akhir bulan KSEI
      (metode biaya rata-rata). Kasar, tetapi gratis dan untuk seluruh pasar.
    - `dksei_*`: perubahan 1 bulan terakhir (dari dua periode terakhir).

    Mengembalikan dict format ksei.json, atau None bila gagal.
    """
    def say(m=""):
        if log_fn:
            log_fn(m)

    daftar = daftar_bulan(bulan, log_fn)
    if len(daftar) < 2:
        say("[!] Berkas KSEI tidak ditemukan.")
        return None

    ambil = daftar
    tgl_now, tgl_prev = ambil[0][0], ambil[1][0]
    say("  Periode terbaru : %s" % tgl_now)
    say("  Periode sebelumnya: %s" % tgl_prev)
    say("  Menyusun seri %d bulan untuk estimasi harga rata-rata asing..." % len(ambil))

    seri = {}   # kode -> [ (tgl, dict), ... ] urut menaik (tertua -> terbaru)
    for tgl, url in reversed(ambil):
        p = unduh_zip(url, log_fn)
        if not p:
            say("  [!] lewat %s (gagal unduh)" % tgl)
            continue
        d = parse_zip(p)
        for kode, row in d.items():
            seri.setdefault(kode, []).append((tgl, row))
    if not seri:
        say("[!] Tidak ada berkas KSEI yang berhasil dibaca.")
        return None

    now = {k: v[-1][1] for k, v in seri.items()}
    prev = {k: v[-2][1] for k, v in seri.items() if len(v) >= 2}
    say("  Terbaca %d emiten EQUITY; seri %d bulan" % (len(now), len(ambil)))

    for kode, rows in seri.items():
        d = now[kode]
        # Rata-rata harga PEMBELIAN asing: hanya bulan yang lembar asingnya naik.
        buy_sh = 0.0
        buy_cost = 0.0
        prev_fs = None
        for (_tgl, row) in rows:
            fs = float(row.get("asing_saham") or 0)
            pr = float(row.get("harga_ksei") or 0)
            if prev_fs is not None and fs > prev_fs:
                add = fs - prev_fs
                buy_sh += add
                buy_cost += add * pr
            prev_fs = fs
        d["asing_avg_price"] = round(buy_cost / buy_sh, 2) if buy_sh > 0 else None
        d["asing_beli_saham"] = int(round(buy_sh))
        try:
            d["asing_net_saham"] = int(round(float(rows[-1][1].get("asing_saham") or 0)
                                             - float(rows[0][1].get("asing_saham") or 0)))
        except (IndexError, TypeError):
            d["asing_net_saham"] = None
        d["seri_bulan"] = len(rows)
        pv = prev.get(kode)
        if pv:
            d["asing_pct_prev"] = pv["asing_pct"]
            d["dksei_asing_1m"] = round(d["asing_pct"] - pv["asing_pct"], 3)
            d["dksei_institusi_1m"] = round(d["institusi_pct"] - pv["institusi_pct"], 3)
            d["dksei_ritel_1m"] = round(d["ritel_pct"] - pv["ritel_pct"], 3)
        else:
            d["asing_pct_prev"] = None
            d["dksei_asing_1m"] = None
            d["dksei_institusi_1m"] = None
            d["dksei_ritel_1m"] = None

    fmt = lambda t: "%s-%s-%s" % (t[0:4], t[4:6], t[6:8])
    return {
        "dibuat": datetime.now().astimezone().isoformat(timespec="seconds"),
        "sumber": "KSEI Komposisi Kepemilikan Efek (Lokal-Asing)",
        "catatan": ("Persen dari total lembar lokal+asing. ritel = individu domestik (Local ID). "
                    "asing_avg_price = rata-rata harga pembelian asing selama seri %d bulan "
                    "(harga akhir bulan x kenaikan lembar asing)." % len(ambil)),
        "periode": fmt(tgl_now),
        "sebelumnya": fmt(tgl_prev),
        "seri_bulan": len(ambil),
        "jumlah": len(now),
        "emiten": now,
    }


def main():
    setup_stdout()
    log("=" * 68)
    log(" Penarik kepemilikan efek KSEI (Lokal vs Asing)")
    log(" Sumber: web.ksei.co.id (arsip terbuka, tanpa login)")
    log("=" * 68)

    keluaran = ambil_ksei(log_fn=log)
    if not keluaran:
        return 1
    with open("ksei.json", "w", encoding="utf-8") as fh:
        json.dump(keluaran, fh, ensure_ascii=False, indent=2)
    now = keluaran["emiten"]
    log("")
    log("SELESAI. %d emiten -> %s" % (len(now), os.path.abspath("ksei.json")))
    for k in ["BBCA", "TLKM", "ANTM", "BBRI"]:
        if k in now:
            d = now[k]
            log("  %-5s asing %5.2f%%  (%+.2f pp)  ritel %5.2f%%  institusi %5.2f%%"
                % (k, d["asing_pct"], d.get("dksei_asing_1m") or 0.0,
                   d["ritel_pct"], d["institusi_pct"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
