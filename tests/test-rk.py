"""Test RK trap. Jalan tanpa pytest: python tests/test-rk.py"""
import importlib.util
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location(
    "m_idx", os.path.join(_ROOT, "scripts", "fetch-data-idx.py"))
m_idx = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m_idx)


def test_pbv_wajar():
    assert m_idx.compute_pbv_wajar(10.0) == 1.0
    assert m_idx.compute_pbv_wajar(21.8) == 2.18
    assert m_idx.compute_pbv_wajar(0) is None
    assert m_idx.compute_pbv_wajar(None) is None
    assert m_idx.compute_pbv_diskon(1.2, 2.0) == 40.0
    assert m_idx.compute_pbv_diskon(None, 2.0) is None


def test_trap_jebakan():
    out = m_idx.compute_trap(5.0, 0.4, "down", 0, 100.0, "Kill", 1.5, 0.0)
    assert out["trap_badge"] == "Jebakan" and out["trap_skor"] >= 2, out


def test_trap_aman():
    out = m_idx.compute_trap(12.0, 2.5, "up", 1, 100.0, "Lolos", 0.4, 0.5)
    assert out["trap_badge"] == "Aman" and out["trap_skor"] == 0, out


def test_trap_data_kurang():
    out = m_idx.compute_trap(None, None, "fluktuatif", 0, 0, "-", 0, None)
    assert out["trap_badge"] == "-", out


def test_wire_rk():
    fund = {
        "price": {"regularMarketPrice": {"raw": 2000}},
        "summaryDetail": {"payoutRatio": {"raw": 0.5}, "dividendYield": {"raw": 0.02}}, "assetProfile": {},
        "defaultKeyStatistics": {"sharesOutstanding": {"raw": 10}, "bookValue": {"raw": 1000}, "trailingEps": {"raw": 200}, "netIncomeToCommon": {"raw": 2000}},
        "financialData": {"totalDebt": {"raw": 0}, "totalCash": {"raw": 0}, "operatingCashflow": {"raw": 100}, "freeCashflow": {"raw": 90}},
        "incomeStatementHistoryQuarterly": {"incomeStatementHistory": []},
        "incomeStatementHistory": {"incomeStatementHistory": []},
    }
    rec = m_idx.build_record("ZZZ", {"nama": "Z", "sektor": "Energi"}, fund, None, None)
    assert rec["pbv_wajar"] == 2.0 and rec["pbv_diskon"] == 0.0, rec
    assert rec["payout"] == 50.0, rec
    assert rec["trap_badge"] == "Aman", rec


if __name__ == "__main__":
    test_pbv_wajar()
    test_trap_jebakan()
    test_trap_aman()
    test_trap_data_kurang()
    test_wire_rk()
    print("rk OK: 5 passed")
