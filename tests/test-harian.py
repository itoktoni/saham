"""Test harian otomatis (Task 1-3). Jalan tanpa pytest: python tests/test-harian.py"""
import importlib.util
import json
import tempfile
import os

_spec = importlib.util.spec_from_file_location("m_idx", "scripts/fetch-data-idx.py")
m_idx = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m_idx)
normalkan_baris_stock = m_idx.normalkan_baris_stock


def test_normalkan_baris_stock():
    r = {"StockCode": "GOTO", "High": "33", "Low": "30", "Close": "32",
         "Volume": "157390000", "Value": "487060000000", "Frequency": "38180"}
    out = normalkan_baris_stock(r)
    assert out == {"kode": "GOTO", "high": 33, "low": 30, "close": 32,
                   "volume": 157390000, "value": 487060000000, "freq": 38180}, out


def test_baris_tanpa_kode_dibuang():
    assert normalkan_baris_stock({"Volume": "1"}) is None


def test_tulis_harian_atomik():
    import tempfile
    tulis_harian = m_idx.tulis_harian
    with tempfile.TemporaryDirectory() as td:
        tujuan = os.path.join(td, "harian-20261006.json")
        out = tulis_harian(tujuan, "20261006", [{"kode": "GOTO", "high": 33, "low": 30,
            "close": 32, "volume": 157390000, "value": 487060000000, "freq": 38180}])
        assert out == tujuan
        d = json.load(open(tujuan, encoding="utf-8"))
        assert d["tanggal"] == "20261006" and d["jumlah"] == 1
        assert d["saham"][0]["kode"] == "GOTO"


if __name__ == "__main__":
    test_normalkan_baris_stock()
    test_baris_tanpa_kode_dibuang()
    test_tulis_harian_atomik()
    print("Task2 OK: 3 passed")
