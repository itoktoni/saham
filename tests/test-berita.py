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
    # jendela bertingkat: 7 -> 30 -> 90 -> 1 tahun -> riwayat (tanpa batas)
    assert [w[0] for w in fb.JENDELA] == [7, 30, 90, 365, None]
    assert [w[1] for w in fb.JENDELA] == [
        "7 hari", "30 hari", "90 hari", "1 tahun", "riwayat"]


def test_jendela_bertingkat():
    """Berita lama TIDAK membuang story — hanya melebarkan jendela hitung."""
    segar = [{"umur": 2}, {"umur": 5}]
    bulan = [{"umur": 12}, {"umur": 20}]
    q3 = [{"umur": 80}]
    tahun = [{"umur": 400}]
    tua = [{"umur": 900}, {"umur": 1300}]
    # jendela 7 hari terisi -> tetap pakai (buzz = "ramai sekarang")
    pilih, nama = fb.pilih_jendela(segar + bulan + q3 + tahun + tua)
    assert nama == "7 hari" and len(pilih) == 2, (nama, pilih)
    # 7 hari kosong -> 30 hari
    pilih, nama = fb.pilih_jendela(bulan + q3 + tahun)
    assert nama == "30 hari" and len(pilih) == 2, (nama, pilih)
    # lalu 90 hari, lalu 1 tahun
    assert fb.pilih_jendela(q3 + tahun)[1] == "90 hari"
    pilih, nama = fb.pilih_jendela([{"umur": 300}] + tua)
    assert nama == "1 tahun" and len(pilih) == 1, (nama, pilih)
    # berita ratusan hari pun tetap dipakai -> riwayat (inti: tetap ada nilai)
    pilih, nama = fb.pilih_jendela(tua)
    assert nama == "riwayat" and len(pilih) == 2, (nama, pilih)
    # tanpa tanggal sama sekali -> riwayat (ikut dihitung)
    pilih, nama = fb.pilih_jendela([{"umur": None}])
    assert nama == "riwayat" and pilih == [{"umur": None}]
    assert fb.pilih_jendela([]) == ([], "riwayat")


def _rss(feed):
    """RSS sintetis: feed = [(judul, umur_hari), ...] untuk kode yang diuji."""
    it = []
    for judul, u in feed:
        tgl = (datetime.now(timezone.utc) - timedelta(days=u)).strftime(
            "%a, %d %b %Y %H:%M:%S +0000")
        it.append("<item><title>%s</title><link>http://x</link>"
                  "<pubDate>%s</pubDate><description>d</description></item>"
                  % (judul, tgl))
    return ("<rss version=\"2.0\"><channel>" + "".join(it) +
            "</channel></rss>").encode("utf-8")


def test_fetch_jendela():
    """Uji ujung-ke-ujung ambil_berita dengan RSS palsu:
    saham berita segar + saham berita TUA tetap dapat nilai."""
    asli = fb._unduh

    def palsu(url, timeout=25):  # noqa: ANN001
        if "news.google.com" in url:
            if "TEST1" in url:
                return _rss([("TEST1 raih kontrak baru", 1),
                             ("TEST1 rugi besar semester ini", 3),
                             ("TEST1 saham digoreng spekulan", 200)])
            return _rss([("TEST2 laba merosot", 40), ("TEST2 PHK massal", 45),
                         ("TEST2 utang bermasalah", 50),
                         ("TEST2 dijual investasi asing", 60)])
        return _rss([])                      # RSS umum: kosong

    fb._unduh = palsu
    try:
        hasil = fb.ambil_berita(["TEST1", "TEST2"], tulis_cache=False, delay=0)
    finally:
        fb._unduh = asli
    em = hasil["emiten"]
    t1, t2 = em["TEST1"], em["TEST2"]
    # TEST1: ada berita segar -> jendela 7 hari
    assert t1["jendela"] == "7 hari" and t1["n"] == 2 and t1["nSegar"] == 2, t1
    assert t1["usia"] is not None and 0 <= t1["usia"] <= 2, t1
    assert t1["buzz"] == "Sepi"              # 2 berita = Sepi
    # TEST2: TANPA berita segar, semua umur 40-60 hari -> TETAP punya nilai
    assert t2["jendela"] == "90 hari" and t2["n"] == 4 and t2["nSegar"] == 0, t2
    assert t2["buzz"] == "Normal" and t2["sentimen"] < 40, t2
    assert t2["usia"] is not None and 38 <= t2["usia"] <= 42, t2


if __name__ == "__main__":
    test_skor_kata_batas()
    test_sentimen_rentang()
    test_buzz_ambang()
    test_umur_pubdate()
    test_konstanta_skor()
    test_jendela_bertingkat()
    test_fetch_jendela()
    print("berita OK: 7 passed")
