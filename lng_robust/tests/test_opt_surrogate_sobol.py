import numpy as np
import pandas as pd
import pytest
from scipy.optimize import minimize_scalar

from lng_robust.analysis.sobol import alr, alr_inv, sobol_indices
from lng_robust.opt.common import cvar, knee_point, price_of_robustness
from lng_robust.surrogate import classify
from lng_robust.surrogate.train import grouped_cv


def test_cvar_matches_brute_force_minimisation_and_tail_mean():
    rng = np.random.default_rng(0)
    v = rng.random(40) + 0.3
    a = 0.9
    f = lambda t: t + np.maximum(0, v - t).sum() / ((1 - a) * len(v))
    brute = minimize_scalar(f, bounds=(v.min(), v.max()), method="bounded", options=dict(xatol=1e-10)).fun
    assert abs(cvar(v, a) - brute) < 1e-6
    tail = np.sort(v)[-int(round((1 - a) * len(v))):]          # 4 largest of 40 = the 10 % tail
    assert abs(cvar(v, a) - tail.mean()) < 1e-9
    assert abs(cvar(v, 0.0) - v.mean()) < 1e-9 and cvar(v, a) >= v.mean()


def test_cvar_with_penalised_infeasible_scenarios_exceeds_feasible_mean():
    v = np.array([0.5] * 18 + [2.0, 2.0])      # two infeasible scenarios at SEC_pen
    assert cvar(v, 0.9) == pytest.approx(2.0)


def test_price_of_robustness_formula():
    assert price_of_robustness(0.55, 0.50) == pytest.approx(0.10)
    assert price_of_robustness(0.50, 0.50) == 0.0


def test_knee_point_picks_balanced_design():
    F = np.array([[0.0, 10.0], [1.0, 1.0], [10.0, 0.0]])
    assert knee_point(F) == 1


def test_ffr_formula_and_near_limit_subset():
    yt = np.array([0, 0, 0, 0, 1, 1], bool)
    yp = np.array([1, 0, 0, 1, 1, 1], bool)
    assert classify.confusion(yt, yp) == dict(TP=2, TN=2, FP=2, FN=0)
    assert classify.ffr(yt, yp) == pytest.approx(0.5)
    mita = np.array([2.6, 1.0, 20.0, 3.4, 5.0, 3.2])
    rep = classify.report(yt, yp, mita, 3.0, 1.0)
    assert rep["n_near"] == 3 and rep["FFR_near"] == pytest.approx(1.0)       # near-limit negatives: idx0 (FP), idx3 (FP)


def test_grouped_cv_never_trains_on_the_withheld_composition():
    rng = np.random.default_rng(1)
    n = 90
    df = pd.DataFrame({"x0": rng.normal(size=n), "x1": rng.normal(size=n), "group": np.repeat(["a", "b", "c"], 30)})
    df["feed_id"] = df["group"]
    df["sec"] = df["group"].map({"a": 0.0, "b": 5.0, "c": 10.0})          # target is a pure group label
    df["mita"] = 5.0
    df["feasible"] = True
    df["failure_code"] = ""
    df["numerical_failure"] = False
    met, oof = grouped_cv(df, 3.0, seed=1)
    gb = oof["sec_gradient_boosting"]
    err = (gb - df["sec"]).abs()
    assert err.mean() > 2.0        # a model that saw the group would be near 0; unseen groups cannot be recovered


def test_alr_roundtrip_and_ishigami_sobol():
    z = np.array([[0.6, 0.3, 0.1], [0.2, 0.5, 0.3]])
    assert np.allclose(alr_inv(alr(z)), z)
    model = lambda X: np.sin(X[:, 0]) + 7 * np.sin(X[:, 1]) ** 2 + 0.1 * X[:, 2] ** 4 * np.sin(X[:, 0])
    r = sobol_indices(model, ["x1", "x2", "x3"], [[-np.pi, np.pi]] * 3, N=2048, seed=2)
    assert np.allclose(r["S1"], [0.3139, 0.4424, 0.0], atol=0.06)
    assert np.allclose(r["ST"], [0.5576, 0.4424, 0.2437], atol=0.06)
