import math

import numpy as np

from lng_robust.units.mshe import Stream, mshe


def _lin(cp, T0=100.0, T1=500.0):
    T = np.linspace(T0, T1, 5)
    return (T, cp * (T - T0), cp * np.log(T / T0))   # molar H, S with n = 1 mol/s


def test_balanced_counterflow_matches_analytic():
    # hot 300->200 K, cold 190->290 K, both C = 2 W/K: dT = 10 K everywhere, Q = 200 W, UA = 20 W/K
    hot = Stream("h", "hot", None, None, 1.0, 300.0, 200.0, 1, 1, table=_lin(2.0))
    cold = Stream("c", "cold", None, None, 1.0, 190.0, 290.0, 1, 1, table=_lin(2.0))
    r = mshe([hot, cold], N=50)
    assert abs(r.mita - 10.0) < 1e-6
    assert abs(r.ua - 20.0) < 1e-6
    assert not r.temp_cross


def test_unbalanced_counterflow_matches_analytic_lmtd():
    # hot C=1: 400->300 (Q=100). cold C=2: 250->300. dT_cold_end=50, dT_warm_end=100, LMTD=50/ln2
    hot = Stream("h", "hot", None, None, 1.0, 400.0, 300.0, 1, 1, table=_lin(1.0))
    cold = Stream("c", "cold", None, None, 1.0, 250.0, 300.0, 1, 1, table=_lin(2.0))
    r = mshe([hot, cold], N=200)
    lmtd = 50.0 / math.log(2.0)
    assert abs(r.mita - 50.0) < 1e-6
    assert abs(r.ua - 100.0 / lmtd) / (100.0 / lmtd) < 1e-6


def test_temperature_cross_detected():
    hot = Stream("h", "hot", None, None, 1.0, 300.0, 250.0, 1, 1, table=_lin(2.0))
    cold = Stream("c", "cold", None, None, 1.0, 260.0, 310.0, 1, 1, table=_lin(2.0))   # cold exits hotter than hot enters
    r = mshe([hot, cold], N=20)
    assert r.temp_cross and r.mita < 0


def test_multi_stream_energy_balance_and_exergy_nonnegative():
    h1 = Stream("h1", "hot", None, None, 1.0, 320.0, 200.0, 1, 1, table=_lin(1.0))
    h2 = Stream("h2", "hot", None, None, 1.0, 320.0, 200.0, 1, 1, table=_lin(1.0))
    c = Stream("c", "cold", None, None, 1.0, 190.0, 310.0, 1, 1, table=_lin(2.0))
    r = mshe([h1, h2, c], N=100)
    assert r.balance_error < 1e-9
    assert r.exergy_destruction > 0
