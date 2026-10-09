"""Test modul berita/sentimen (fetch-berita.py). Jalan tanpa pytest:
python tests/test-berita.py"""
import importlib.util
import os
from datetime import datetime, timedelta, timezone

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location(
    "fb", os.path.join(_ROOT, "scripts", "fetch-berita.py"))
fb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fb)


def test_skor_kata_batas():
    # "penjualan" tidak boleh kena leksikon "jual"
    assert fb.skor_berita("Penjualan naik 20%") > 0, fb.skor_berita("Penjualan naik 20%")
    # "stop" tidak boleh kena leksikon "top"
    assert fb.skor_berita("Stop loss di pasar") == 0, fb.skor_berita("Stop loss di pasar")
    assert fb.skor_berita("Laba anjlok, saham rugi") < 0
    assert fb.skor_berita("") == 0


def test_sentimen_rentang():
    pos = [{"skor": 25}, {"skor": 50}, {"skor": 0}]
    neg = [{"skor": -25}, {"skor": -50}]
    netral = [{"skor": 0}, {"skor": 0}]
    kosong = []
    assert fb.sentimen_rangkum(pos) >= 60, fb.sentimen_rangkum(pos)
    assert fb.sentimen_rangkum(neg) < 40, fb.sentimen_rangkum(neg)
    assert fb.sentimen_rangkum(netral) == 50
    assert fb.sentimen_rangkum(kosong) == 50
    # campuran yang sedikit dominan positif: di 50..100, tidak memuncak (Laplace)
    campur = [{"skor": 25}, {"skor": 25}, {"skor": -25}]
    assert 50 < fb.sentimen_rangkum(campur) < 100, fb.sentimen_rangkum(campur)


def test_buzz_ambang():
    assert fb.buzz_dari(0) == "Sepi"      # n=0 -> tanpa story, tetap sepi
    assert fb.buzz_dari(2) == "Sepi"
    assert fb.buzz_dari(3) == "Normal"
    assert fb.buzz_dari(fb.BUZZ_RAMAI - 1) == "Normal"
    assert fb.buzz_dari(fb.BUZZ_RAMAI) == "Ramai"
    assert fb.buzz_dari(41) == "Ramai"


def test_umur_pubdate():
    segar = (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%a, %d %b %Y %H:%M:%S +0000")
    basi = (datetime.now(timezone.utc) - timedelta(days=40)).strftime("%a, %d %b %Y %H:%M:%S +0000")
    assert 1 <= fb._umur_hari(segar) <= 3, fb._umur_hari(segar)
    assert fb._umur_hari(basi) > fb.HARI_SEGAR
    assert fb._umur_hari("bukan tanggal") is None


def test_konstanta_skor():
    # ambang label Story (frontend: Positif >=60, Negatif <40) dan ambang buzz
    assert fb.HARI_SEGAR == 7 and fb.BUZZ_RAMAI == 10 and fb.BUZZ_NORMAL == 3
    for n, buzz in [(0, "Sepi"), (2, "Sepi"), (3, "Normal"), (10, "Ramai")]:
        assert fb.buzz_dari(n) == buzz


if __name__ == "__main__":
    test_skor_kata_batas()
    test_sentimen_rentang()
    test_buzz_ambang()
    test_umur_pubdate()
    test_konstanta_skor()
    print("berita OK: 5 passed")
