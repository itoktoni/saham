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


if __name__ == "__main__":
    test_kuartal_4_terbaru_urut()
    test_tahunan_dan_rugi_negatif()
    test_kosong_aman()
    test_respons_memuat_labarugi()
    print("labarugi OK: 4 passed")
