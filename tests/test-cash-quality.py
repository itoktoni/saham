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


def test_cfo_cagr():
    assert m_idx.compute_cfo_cagr([(2022, 0, 100.0), (2023, 0, 121.0), (2024, 0, 146.4)]) == 0.21
    assert m_idx.compute_cfo_cagr([(2022, 0, 100.0), (2024, 0, -5.0)]) is None
    assert m_idx.compute_cfo_cagr([(2024, 0, 10.0)]) is None


def test_peg_cfo():
    assert m_idx.compute_peg_cfo(10.0, 0.30) == 0.33
    assert m_idx.compute_peg_cfo(None, 0.30) is None
    assert m_idx.compute_peg_cfo(10.0, 0) is None


def test_klasifikasi():
    assert m_idx.compute_klasifikasi("Energi", 5.0, 0, 0.5, [(2023, -10.0), (2024, 20.0)], None) == "Turnaround"
    assert m_idx.compute_klasifikasi("Energi", 25.0, 0, 0.5, [(2023, 10.0), (2024, 20.0)], None) == "FastGrowing"
    assert m_idx.compute_klasifikasi("Energi", 5.0, 0, 0.5, [(2023, 10.0), (2024, 20.0)], None) == "Cyclical"
    assert m_idx.compute_klasifikasi("Konsumer Primer", 5.0, 1, 0.5, [(2023, 10.0), (2024, 20.0)], None) == "Stalwart"
    assert m_idx.compute_klasifikasi("Konsumer Primer", 5.0, 0, 0.5, [(2023, 10.0), (2024, 20.0)], 0.5) == "AssetPlay"
    assert m_idx.compute_klasifikasi("Konsumer Primer", 5.0, 0, 2.0, [(2023, 10.0), (2024, 20.0)], None) == "-"


def test_thowilz():
    out = m_idx.compute_thowilz(8.0, 0.5, "Lolos", 1, "FastGrowing", 5, 1, 0)
    assert out["thowilz"] == 100, out
    out2 = m_idx.compute_thowilz(None, None, "Kill", 0, "-", 1, 0, 0)
    assert out2["thowilz"] < 30, out2


def test_wire_yahoo_thowilz():
    fund = {
        "price": {"regularMarketPrice": {"raw": 1000}},
        "summaryDetail": {}, "assetProfile": {},
        "defaultKeyStatistics": {"sharesOutstanding": {"raw": 10}, "bookValue": {"raw": 500}, "trailingEps": {"raw": 100}, "netIncomeToCommon": {"raw": 1000}},
        "financialData": {"totalDebt": {"raw": 2000}, "totalCash": {"raw": 500}, "operatingCashflow": {"raw": 1500}, "freeCashflow": {"raw": 800}, "earningsGrowth": {"raw": 0.25}},
        "incomeStatementHistoryQuarterly": {"incomeStatementHistory": []},
        "incomeStatementHistory": {"incomeStatementHistory": [
            {"endDate": {"raw": 3}, "totalRevenue": {"raw": 1000}, "grossProfit": {"raw": 450}},
            {"endDate": {"raw": 2}, "totalRevenue": {"raw": 900}, "grossProfit": {"raw": 405}},
            {"endDate": {"raw": 1}, "totalRevenue": {"raw": 800}, "grossProfit": {"raw": 360}}]},
    }
    rec = m_idx.build_record("ZZZ", {"nama": "Z", "sektor": "Energi"}, fund, None, None)
    assert rec["margin_stabil"] == 1 and rec["gross_margin"] == 45.0, rec
    assert rec["capex_inten"] == round((1500-800)/1500, 3), rec
    assert rec["klasifikasi"] == "FastGrowing", rec
    assert rec["thowilz"] >= 50, rec


def test_wire_idx_thowilz():
    rec = {"harga": 1000, "ekuitas": 1, "laba": 0, "eps": 0, "kuartal": 4, "fcf": 0, "kas": 50000.0, "utang": 50000.0, "der": 1.0, "saham": 10, "sektor": "Energi", "cyclical": 1, "cagr": 5.0, "dividen": 0, "ev_cfo": 8.0, "ev_fcf": None, "cfo3": 0, "sloan": None, "cash_badge": "-", "s_sideways": 1, "s_spring": 0, "gross_margin": None, "margin_stabil": 0, "capex_inten": None, "peg_cfo": None, "cfo_cagr": None, "klasifikasi": "-", "thowilz": 0, "_catatan": []}
    lap = [
        {"tahun": 2024, "laba": 120e9, "arus_kas_operasi": 150e9, "aset": 1000e9, "ekuitas": 500e9, "liabilitas": 500e9, "kas": 50e9, "pendapatan": 1e12, "eps": 100, "pembulatan": "Satuan", "skala": 1.0},
        {"tahun": 2023, "laba": 110e9, "arus_kas_operasi": 130e9, "aset": 900e9, "ekuitas": 450e9, "liabilitas": 450e9, "kas": 40e9, "pendapatan": 9e11, "eps": 90, "pembulatan": "Satuan", "skala": 1.0},
        {"tahun": 2022, "laba": 100e9, "arus_kas_operasi": 100e9, "aset": 800e9, "ekuitas": 400e9, "liabilitas": 400e9, "kas": 30e9, "pendapatan": 8e11, "eps": 80, "pembulatan": "Satuan", "skala": 1.0},
    ]
    out, _ = m_idx.gabung_laporan(rec, lap)
    assert out["cfo_cagr"] == round(((150e9/100e9) ** (1/2) - 1) * 100, 1), out
    assert out["peg_cfo"] is not None and out["peg_cfo"] < 1.5, out
    assert out["klasifikasi"] == "Cyclical", out
    assert out["thowilz"] >= 60, out


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
    test_cfo_cagr()
    test_peg_cfo()
    test_klasifikasi()
    test_thowilz()
    test_wire_yahoo_thowilz()
    test_wire_idx_thowilz()
    print("cash-quality OK: 16 passed")
