"""Test cashflow Thowilz. Jalan tanpa pytest: python tests/test-cash-quality.py"""
import importlib.util
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location(
    "m_idx", os.path.join(_ROOT, "scripts", "fetch-data-idx.py"))
m_idx = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m_idx)


def test_compute_ev():
    assert m_idx.compute_ev(100.0, 20.0, 30.0) == 90.0
    assert m_idx.compute_ev(0, 20.0, 5.0) is None
    assert m_idx.compute_ev(100.0, 0, 0) == 100.0


def test_cfo3_lolos():
    hist = [(2022, 100.0, 120.0), (2023, 110.0, 130.0), (2024, 120.0, 150.0)]
    out = m_idx.compute_cash_quality(hist, 1000.0, "Energi")
    assert out["cfo3"] == 1, out
    assert out["badge"] == "Lolos", out


def test_sloan_kill():
    hist = [(2022, 200.0, 190.0), (2023, 210.0, 50.0), (2024, 220.0, 40.0)]
    out = m_idx.compute_cash_quality(hist, 1000.0, "Energi")
    assert out["badge"] == "Kill", out
    assert out["sloan"] is not None and out["sloan"] > 0.10


def test_bank_tidak_dikill():
    hist = [(2022, 200.0, 190.0), (2023, 210.0, 50.0), (2024, 220.0, 40.0)]
    out = m_idx.compute_cash_quality(hist, 1000.0, "Keuangan")
    assert out["badge"] != "Kill", out


def test_data_kurang():
    out = m_idx.compute_cash_quality([(2024, 10.0, 12.0)], 100.0, "Energi")
    assert out["badge"] == "-", out
    assert out["cfo3"] == 0


def test_build_record_ev():
    fund = {
        "price": {"regularMarketPrice": {"raw": 1000}},
        "summaryDetail": {}, "assetProfile": {},
        "defaultKeyStatistics": {"sharesOutstanding": {"raw": 10}, "bookValue": {"raw": 500}, "trailingEps": {"raw": 100}, "netIncomeToCommon": {"raw": 1000}},
        "financialData": {"totalDebt": {"raw": 2000}, "totalCash": {"raw": 500}, "operatingCashflow": {"raw": 1500}, "freeCashflow": {"raw": 800}},
        "incomeStatementHistoryQuarterly": {"incomeStatementHistory": []},
    }
    rec = m_idx.build_record("ZZZ", {"nama": "Z", "sektor": "Energi"}, fund, None, None)
    assert rec["ev_cfo"] == round((1000*10+2000-500)/1500, 2), rec
    assert rec["ev_fcf"] == round((1000*10+2000-500)/800, 2), rec
    assert rec["cash_badge"] in ("Lolos", "Watchlist", "Kill", "-")


def test_gabung_laporan_cash():
    rec = {"harga": 1000, "ekuitas": 1, "laba": 0, "eps": 0, "kuartal": 4, "fcf": 0, "kas": 0, "utang": 0, "der": 0, "saham": 10, "sektor": "Energi", "cyclical": 0, "ev_cfo": None, "ev_fcf": None, "cfo3": 0, "sloan": None, "cash_badge": "-", "_catatan": []}
    lap = [
        {"tahun": 2024, "laba": 120e9, "arus_kas_operasi": 150e9, "aset": 1000e9, "ekuitas": 500e9, "liabilitas": 500e9, "kas": 50e9, "pendapatan": 1e12, "eps": 100, "pembulatan": "Satuan", "skala": 1.0},
        {"tahun": 2023, "laba": 110e9, "arus_kas_operasi": 130e9, "aset": 900e9, "ekuitas": 450e9, "liabilitas": 450e9, "kas": 40e9, "pendapatan": 9e11, "eps": 90, "pembulatan": "Satuan", "skala": 1.0},
        {"tahun": 2022, "laba": 100e9, "arus_kas_operasi": 120e9, "aset": 800e9, "ekuitas": 400e9, "liabilitas": 400e9, "kas": 30e9, "pendapatan": 8e11, "eps": 80, "pembulatan": "Satuan", "skala": 1.0},
    ]
    out, _ = m_idx.gabung_laporan(rec, lap)
    assert out["cfo3"] == 1, out
    assert out["cash_badge"] == "Lolos", out
    assert "ev_cfo" in out and "ev_fcf" in out


def test_margin_stabil():
    out = m_idx.compute_margin_quality([0.44, 0.45, 0.46, 0.45])
    assert out["margin_stabil"] == 1, out
    assert out["gross_margin"] == 45.0, out


def test_margin_longor():
    out = m_idx.compute_margin_quality([0.45, 0.30, 0.15])
    assert out["margin_stabil"] == 0, out


def test_margin_kurang():
    out = m_idx.compute_margin_quality([0.45, 0.46])
    assert out["margin_stabil"] == 0 and out["gross_margin"] == 46.0, out


if __name__ == "__main__":
    test_compute_ev()
    test_cfo3_lolos()
    test_sloan_kill()
    test_bank_tidak_dikill()
    test_data_kurang()
    test_build_record_ev()
    test_gabung_laporan_cash()
    test_margin_stabil()
    test_margin_longor()
    test_margin_kurang()
    print("cash-quality OK: 10 passed")
