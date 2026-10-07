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


if __name__ == "__main__":
    test_compute_ev()
    test_cfo3_lolos()
    test_sloan_kill()
    test_bank_tidak_dikill()
    test_data_kurang()
    print("cash-quality OK: 5 passed")
