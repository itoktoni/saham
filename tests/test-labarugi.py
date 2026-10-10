"""Test deret laba-rugi. Jalan tanpa pytest: python tests/test-labarugi.py"""
import importlib.util
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location(
    "m_idx", os.path.join(_ROOT, "scripts", "fetch-data-idx.py"))
m_idx = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m_idx)


def _fund():
    def e(dt, rev, ni):
        return {"endDate": {"raw": int(dt.replace("-", "")), "fmt": dt},
                "totalRevenue": {"raw": rev} if rev is not None else None,
                "netIncome": {"raw": ni} if ni is not None else None}
    return {
        "incomeStatementHistoryQuarterly": {"incomeStatementHistory": [
            e("2026-06-30", 10.0, 1.0), e("2026-03-31", 9.0, -0.5),
            e("2025-12-31", 8.0, 0.8), e("2025-09-30", 7.0, 0.7),
            e("2025-06-30", 6.0, 0.6)]},
        "incomeStatementHistory": {"incomeStatementHistory": [
            e("2025-12-31", 30.0, 2.0), e("2024-12-31", 28.0, 1.5)]},
    }


def test_kuartal_4_terbaru_urut():
    s = m_idx.labarugi_series(_fund())
    assert [p["t"] for p in s["q"]] == ["2025-09-30", "2025-12-31", "2026-03-31", "2026-06-30"], s
    assert s["q"][-1] == {"t": "2026-06-30", "rev": 10.0, "ni": 1.0}, s


def test_tahunan_dan_rugi_negatif():
    s = m_idx.labarugi_series(_fund())
    assert s["y"] == [{"t": "2024-12-31", "rev": 28.0, "ni": 1.5},
                      {"t": "2025-12-31", "rev": 30.0, "ni": 2.0}], s
    assert s["q"][2]["ni"] == -0.5, s


def test_kosong_aman():
    assert m_idx.labarugi_series({}) == {"q": [], "y": []}
    assert m_idx.labarugi_series(None) == {"q": [], "y": []}


def test_respons_memuat_labarugi():
    src = open(os.path.join(_ROOT, "app", "app-screener.py"), encoding="utf-8").read()
    assert "labarugi" in src and "labarugi.json" in src


def test_merge_mempertahankan_entri_lama():
    src = open(os.path.join(_ROOT, "app", "app-screener.py"), encoding="utf-8").read()
    assert "gabung.update(labarugi)" in src


def test_labarugi_untuk_subset():
    spec = importlib.util.spec_from_file_location(
        "app_lr", os.path.join(_ROOT, "app", "app-screener.py"))
    app = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(app)
    app.muat_labarugi = lambda: {"AAA": {"q": [], "y": []},
                                 "BBB": {"q": [{"t": "2026-06-30", "rev": 1.0, "ni": 0.1}],
                                         "y": []}}
    out = app.labarugi_untuk(["BBB", "CCC"])
    assert set(out.keys()) == {"BBB"}, out
    assert out["BBB"]["q"][0]["rev"] == 1.0, out


def _ts_payload():
    def part(tipe, titik):
        rows = [{"dataId": 1, "asOfDate": t, "periodType": "3M",
                 "currencyCode": "IDR", "reportedValue": {"raw": v}} for t, v in titik]
        return {"meta": {"symbol": ["X.JK"], "type": [tipe]},
                "timestamp": [0] * len(rows), tipe: rows}
    return {"timeseries": {"error": None, "result": [
        part("quarterlyTotalRevenue", [("2025-12-31", 8.0), ("2026-03-31", 9.0)]),
        part("quarterlyNetIncome", [("2025-12-31", 0.8), ("2026-03-31", -0.5)]),
        part("annualTotalRevenue", [("2025-12-31", 30.0)]),
        part("annualNetIncome", [("2025-12-31", 2.0)]),
    ]}}


def test_parser_timeseries():
    s = m_idx.labarugi_dari_timeseries(_ts_payload())
    assert s["q"] == [{"t": "2025-12-31", "rev": 8.0, "ni": 0.8},
                      {"t": "2026-03-31", "rev": 9.0, "ni": -0.5}], s
    assert s["y"] == [{"t": "2025-12-31", "rev": 30.0, "ni": 2.0}], s
    assert m_idx.labarugi_dari_timeseries({}) == {"q": [], "y": []}
    assert m_idx.labarugi_dari_timeseries(None) == {"q": [], "y": []}


def test_penuh_pakai_quote_bila_lengkap():
    def bom(*a, **k):
        raise AssertionError("timeseries tak boleh dipanggil bila quoteSummary lengkap")
    dulu = m_idx.labarugi_timeseries
    m_idx.labarugi_timeseries = bom
    try:
        out = m_idx.labarugi_penuh(None, "X", fund=_fund())
        assert out["q"] and out["y"], out
    finally:
        m_idx.labarugi_timeseries = dulu


def test_penuh_fallback_timeseries():
    dulu = m_idx.labarugi_timeseries
    m_idx.labarugi_timeseries = lambda f, k: m_idx.labarugi_dari_timeseries(_ts_payload())
    try:
        out = m_idx.labarugi_penuh(None, "AYAM", fund={})
        assert out["q"] == [{"t": "2025-12-31", "rev": 8.0, "ni": 0.8},
                            {"t": "2026-03-31", "rev": 9.0, "ni": -0.5}], out
        assert out["y"][0]["rev"] == 30.0, out
    finally:
        m_idx.labarugi_timeseries = dulu


def test_penuh_gabung_sebagian():
    fund_y = {"incomeStatementHistory": _fund()["incomeStatementHistory"]}
    dulu = m_idx.labarugi_timeseries
    m_idx.labarugi_timeseries = lambda f, k: m_idx.labarugi_dari_timeseries(_ts_payload())
    try:
        out = m_idx.labarugi_penuh(None, "BKSL", fund=fund_y)
        assert out["q"][0]["rev"] == 8.0, out
        assert out["y"] == [{"t": "2024-12-31", "rev": 28.0, "ni": 1.5},
                            {"t": "2025-12-31", "rev": 30.0, "ni": 2.0}], out
    finally:
        m_idx.labarugi_timeseries = dulu


if __name__ == "__main__":
    test_kuartal_4_terbaru_urut()
    test_tahunan_dan_rugi_negatif()
    test_kosong_aman()
    test_respons_memuat_labarugi()
    test_merge_mempertahankan_entri_lama()
    test_labarugi_untuk_subset()
    test_parser_timeseries()
    test_penuh_pakai_quote_bila_lengkap()
    test_penuh_fallback_timeseries()
    test_penuh_gabung_sebagian()
    print("labarugi OK: 10 passed")
