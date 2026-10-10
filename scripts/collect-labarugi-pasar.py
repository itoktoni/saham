#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
collect-labarugi-pasar.py — Isi data/labarugi.json untuk SELURUH pasar.

Sumber kode: TradingView scan (seluruh pasar IDX, ~900-1200 emiten).
Per emiten: fetch_fundamental (Yahoo) -> labarugi_series -> {q x4, y x5}.
Simpan progresif tiap 25 kode (gabung dengan isi lama), bisa dilanjut
(resume: kode yang sudah ada dilewati, kecuali --refresh).

Pakai:
  python scripts/collect-labarugi-pasar.py [--limit N] [--only AADI,BBCA] [--refresh]

Jalan background (Windows):
  Start-Process python -ArgumentList "scripts/collect-labarugi-pasar.py" ...
Log: logs/labarugi-pasar.log. Setelah selesai: klik Download di aplikasi
agar S.labarugi termuat, lalu drawer tiap emiten menampilkan grafik.
"""

import argparse
import datetime
import importlib.util
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
FILE_LR = os.path.join(DATA, "labarugi.json")
FILE_LOG = os.path.join(ROOT, "logs", "labarugi-pasar.log")
SAVE_EVERY = 25


def log(msg=""):
    baris = "[%s] %s" % (datetime.datetime.now().strftime("%H:%M:%S"), msg)
    print(baris, flush=True)
    try:
        os.makedirs(os.path.dirname(FILE_LOG), exist_ok=True)
        with open(FILE_LOG, "a", encoding="utf-8") as fh:
            fh.write(baris + "\n")
    except OSError:
        pass


def load_mod(nama, path):
    spec = importlib.util.spec_from_file_location(nama, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def muat_lama():
    try:
        with open(FILE_LR, encoding="utf-8") as fh:
            return (json.load(fh) or {}).get("emiten") or {}
    except (OSError, ValueError):
        return {}


def simpan(emiten):
    tmp = FILE_LR + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump({"diambil": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
                   "emiten": emiten}, fh, ensure_ascii=False)
    os.replace(tmp, FILE_LR)


def daftar_pasar(fd, f):
    """Seluruh kode pasar: TradingView dulu, fallback profil IDX."""
    try:
        app = load_mod("app_screener_lr", os.path.join(ROOT, "app", "app-screener.py"))
        rows = app.ambil_tv()
        kodes = [r.get("kode") for r in (rows or []) if r.get("kode")]
        if kodes:
            log("daftar pasar via TradingView: %d kode" % len(kodes))
            return kodes
    except Exception as e:  # noqa: BLE001
        log("TV gagal (%s), fallback profil IDX" % str(e)[:100])
    try:
        prof = fd.load_idx_profiles(f, use_cache=True)
        kodes = sorted(prof.keys())
        log("daftar pasar via profil IDX: %d kode" % len(kodes))
        return kodes
    except Exception as e:  # noqa: BLE001
        log("profil IDX gagal: %s" % str(e)[:120])
    return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--only", default="")
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--repair", action="store_true",
                    help="isi ulang entri yang q atau y kosong (fallback timeseries)")
    args = ap.parse_args()

    fd = load_mod("fetch_idx_lr", os.path.join(ROOT, "scripts", "fetch-data-idx.py"))
    f = fd.Fetcher(delay=1.0)
    if not f._login():
        log("[!] gagal sesi Yahoo — berhenti")
        return 1

    kodes = daftar_pasar(fd, f)
    if args.only:
        mau = [k.strip().upper() for k in args.only.split(",") if k.strip()]
        kodes = [k for k in kodes if k in mau] or mau
    if args.limit > 0:
        kodes = kodes[:args.limit]
    if not kodes:
        log("[!] daftar kode kosong — berhenti")
        return 1

    lama = muat_lama()
    log("cache lama: %d emiten; target: %d kode" % (len(lama), len(kodes)))
    emiten = dict(lama)
    baru = gagal = 0
    t0 = time.time()
    for i, kode in enumerate(kodes, 1):
        ada = emiten.get(kode)
        if ada and not args.refresh:
            kurang = not (ada.get("q") and ada.get("y"))
            if not (args.repair and kurang):
                continue
        try:
            fund = fd.fetch_fundamental(f, kode)
            seri = fd.labarugi_penuh(f, kode, fund)
            if seri.get("q") or seri.get("y"):
                emiten[kode] = seri
                baru += 1
            else:
                gagal += 1
                log("  %s: kosong (Yahoo tanpa income statement)" % kode)
            time.sleep(0.5)
        except Exception as e:  # noqa: BLE001
            gagal += 1
            log("  %s: error %s" % (kode, str(e)[:100]))
        if i % 10 == 0:
            log("[%d/%d] baru=%d gagal/leer=%d (%.0f dtk)" % (i, len(kodes), baru, gagal, time.time() - t0))
        if (baru + gagal) % SAVE_EVERY == 0 and (baru + gagal) > 0:
            try:
                simpan(emiten)
            except OSError as e:
                log("  [!] simpan gagal: %s" % e)
    try:
        simpan(emiten)
    except OSError as e:
        log("[!] simpan akhir gagal: %s" % e)
        return 1
    log("SELESAI: %d emiten berderet (baru=%d, gagal=%d, %.0f dtk) -> %s"
        % (len(emiten), baru, gagal, time.time() - t0, FILE_LR))
    return 0


if __name__ == "__main__":
    sys.exit(main())
