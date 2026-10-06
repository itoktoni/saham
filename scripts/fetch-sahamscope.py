#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fetch-sahamscope.py: broker/insider SahamScope (gratis, tanpa kunci)."""
import json
import time
import urllib.request
from datetime import datetime, timedelta

BASE = "https://www.sahamscope.web.id"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
CACHE_FILE = "sahamscope.json"


def _get(path, timeout=30):
    req = urllib.request.Request(BASE + path, headers={
        "User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def ringkas_pulse(d):
    d = d or {}
    return {
        "tgl": d.get("trade_date", ""),
        "top_net_buy": [{"kode": b.get("stock_code", ""), "broker": b.get("broker_code", ""),
                         "nval": b.get("nval") or 0}
                        for b in (d.get("top_net_buy") or [])[:5]],
        "highlight_insiders": [{"kode": b.get("stock_code", ""), "nama": b.get("name", ""),
                                "tgl": b.get("date", ""), "aksi": b.get("action_type", "")}
                               for b in (d.get("highlight_insiders") or [])[:10]],
    }


def ringkas_acc(acc):
    acc = acc or {}
    out = {"top_buyers": [], "top_sellers": [], "series": {}}
    for b in (acc.get("top_buyers") or [])[:5]:
        out["top_buyers"].append({"broker": b.get("broker_code", ""), "nval": b.get("total_nval") or 0})
    for b in (acc.get("top_sellers") or [])[:5]:
        out["top_sellers"].append({"broker": b.get("broker_code", ""), "nval": b.get("total_nval") or 0})
    for br in (acc.get("series") or []):
        pts = br.get("points") or []
        out["series"][br.get("broker_code", "")] = [
            [p.get("nval") or 0, p.get("cum_nval") or 0,
             p.get("bavg"), p.get("savg")] for p in pts[-30:]]
    return out


def ambil_scope(kodes, log_fn=None, delay=1.0, hari=30, tulis_cache=True):
    log = log_fn or (lambda m: None)
    mulai = (datetime.now() - timedelta(days=hari)).strftime("%Y-%m-%d")
    gagal, emiten = [], {}
    try:
        pulse = ringkas_pulse(_get("/api/market/dashboard-summary"))
    except Exception as e:  # noqa: BLE001
        pulse = {"tgl": "", "top_net_buy": [], "highlight_insiders": []}
        gagal.append("pulse: %s" % str(e)[:80])
    for kode in (kodes or []):
        try:
            acc = ringkas_acc(_get("/api/broker-accumulation/%s?top=5&start_date=%s" % (kode, mulai)))
            time.sleep(delay)
            ins = _get("/api/insiders/%s?page_size=10" % kode)
            emiten[kode] = {"acc": acc, "insider": (ins or {}).get("items", [])[:10]}
            log("%s ok" % kode)
        except Exception as e:  # noqa: BLE001
            gagal.append("%s: %s" % (kode, str(e)[:80]))
    if not pulse["top_net_buy"] and not emiten:
        raise RuntimeError("SahamScope gagal total (%s)" % ("; ".join(gagal)[:160]))
    hasil = {"v": 2, "diambil": datetime.now().astimezone().isoformat(timespec="seconds"),
             "pulse": pulse, "emiten": emiten, "gagal": gagal}
    if tulis_cache:
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as fh:
                json.dump(hasil, fh, ensure_ascii=False)
        except OSError:
            pass
    return hasil


if __name__ == "__main__":
    import sys
    out = ambil_scope([a.upper() for a in sys.argv[1:]] or ["BBCA"])
    print("emiten: %d, gagal: %d" % (len(out["emiten"]), len(out["gagal"])))
