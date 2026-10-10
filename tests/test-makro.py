"""Test modul makro komoditas (app/app-screener.py). Jalan tanpa pytest:
python tests/test-makro.py"""
import importlib.util
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location(
    "app_screener", os.path.join(_ROOT, "app", "app-screener.py"))
app = importlib.util.module_from_spec(_spec)
sys.modules["app_screener"] = app
_spec.loader.exec_module(app)


def _js(closes, harga=None):
    """Respon Yahoo chart API versi minimal (6 hari penutupan)."""
    return {"chart": {"result": [{
        "meta": {"regularMarketPrice": harga},
        "indicators": {"quote": [{"close": closes}]},
    }]}}


def test_parse_makro():
    closes = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0]
    harga, chg, chg5 = app._parse_makro(_js(closes, 105.5))
    assert round(harga, 1) == 105.5                      # pakai harga live
    assert round(chg, 2) == 0.96                         # (105-104)/104
    assert round(chg5, 2) == 5.0                         # (105-100)/100 (5 hari)
    # tanpa harga live -> pakai penutupan terakhir
    _, chg2, _ = app._parse_makro(_js(closes, None))
    assert round(chg2, 2) == 0.96
    # None di tengah dilewati
    _, chg3, chg53 = app._parse_makro(_js([100.0, None, 104.0]))
    assert round(chg3, 2) == 4.0 and round(chg53, 2) == 4.0
    assert app._parse_makro(_js([])) is None             # tanpa penutupan
    assert app._parse_makro({"chart": {"result": []}}) is None
    assert app._parse_makro({}) is None
    assert app._parse_makro(None) is None


def test_tabel_makro():
    assert len(app.MAKRO_SYM) >= 10
    kode = [m[0] for m in app.MAKRO_SYM]
    assert len(kode) == len(set(kode)), "kode Yahoo duplikat"
    nama = [m[1] for m in app.MAKRO_SYM]
    for w in ["Emas", "Perak", "Tembaga", "Minyak", "Batu bara", "Sawit (CPO)", "IHSG",
              "Platinum", "Uranium", "Baja", "Nikel", "Litium & baterai", "Indeks komoditas"]:
        assert w in nama, w
    by = {m[1]: m for m in app.MAKRO_SYM}
    # proxy ETF (harga mentah tidak tersedia gratis di Yahoo)
    assert by["Nikel"][0] == "NIKL" and "nikel" in by["Nikel"][3]
    assert by["Litium & baterai"][0] == "LIT"
    assert by["Baja"][0] == "SLX"
    assert by["Platinum"][0] == "PL=F"
    assert by["Uranium"][0] == "URA"
    assert by["Indeks komoditas"][0] == "DBC" and by["Indeks komoditas"][3] == []
    # produsen makanan/rokok (Consumer Non-Durables) tidak boleh kena bonus
    # komoditas perkebunan — CPO itu biaya buat mereka, bukan pendapatan.
    for n in ["Sawit (CPO)", "Kopi", "Kakao", "Gula"]:
        assert "consumer non-durables" not in by[n][3], n
        assert "perkebunan" in by[n][3], n
    konteks = 0
    for m in app.MAKRO_SYM:
        assert len(m) == 4 and m[1] and m[2], m
        assert isinstance(m[3], list), m
        if not m[3]:
            konteks += 1                      # konteks: tidak menambah skor
        else:
            assert all(k == k.lower() for k in m[3]), "kata kunci harus huruf kecil"
    assert konteks >= 4, "IHSG/Rupiah/Dolar/Indeks komoditas harus konteks (kata kosong)"


def test_narasi():
    items = [
        {"nama": "Emas", "sektor": "Logam mulia", "kata": ["emas"], "chg": 1.3},
        {"nama": "Minyak", "sektor": "Energi", "kata": ["energi"], "chg": -1.2},
        {"nama": "IHSG", "sektor": "Pasar (konteks)", "kata": [], "chg": 2.5},
    ]
    n = app.narasi_makro(items)
    assert "NAIK" in n and "Emas +1,3%" in n, n        # desimal koma gaya Indonesia
    assert "TURUN" in n and "Minyak -1,2%" in n, n
    assert n.count("\n") == 2, "narasi harus 3 baris: NAIK / TURUN / catatan, dapat: " + repr(n)
    assert "Logam mulia" not in n, "sektor tak diulang (sudah ada di chip), dapat: " + repr(n)
    kuat = app.narasi_makro([
        {"nama": "Emas", "sektor": "x", "kata": ["emas"], "chg": 0.5},
        {"nama": "Perak", "sektor": "x", "kata": ["perak"], "chg": 3.0},
    ])
    assert kuat.index("Perak +3,0%") < kuat.index("Emas +0,5%"), "yang terkuat harus di depan: " + kuat
    # konteks (kata kosong) tidak ikut narasi walaupun naik besar
    assert app.narasi_makro([items[2]]).startswith("Komoditas datar")
    assert "IHSG" not in app.narasi_makro([items[2]])
    assert app.narasi_makro([]).startswith("Komoditas datar")


def test_live():
    """Ambil sungguhan. Kalau jaringan mati, lompati tanpa menjatuhkan tes."""
    try:
        data = app.ambil_makro(force=True)
    except Exception as e:  # pragma: no cover
        print("live dilewati:", e)
        return
    assert data.get("items"), data
    kunci = {"kode", "nama", "sektor", "kata", "harga", "chg", "chg5"}
    for it in data["items"]:
        assert kunci <= set(it), it
        assert isinstance(it["chg"], float)
        assert it["kata"] == [] or all(k == k.lower() for k in it["kata"])
    assert data.get("narasi")
    urut = {m[0]: i for i, m in enumerate(app.MAKRO_SYM)}
    idx = [urut[i["kode"]] for i in data["items"]]
    assert idx == sorted(idx), "urut item harus sesuai tabel MAKRO_SYM"
    # cache 5 menit: panggilan kedua memakai data yang sama
    assert app.ambil_makro() is data


if __name__ == "__main__":
    test_parse_makro()
    test_tabel_makro()
    test_narasi()
    test_live()
    print("makro OK: 4 passed")
