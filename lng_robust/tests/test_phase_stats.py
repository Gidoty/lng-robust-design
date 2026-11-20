import numpy as np
import pandas as pd
import pytest

from lng_robust.analysis.por import bootstrap, por_summary
from lng_robust.analysis.reversal import assign_cells, preferred, reversal_table
from lng_robust.opt import ga
from lng_robust.surrogate.stats import ffr_counts, ffr_report, wilson


def test_wilson_matches_known_values():
    p, lo, hi = wilson(0, 10)
    assert p == 0 and lo == 0 and abs(hi - 0.2775) < 1e-3          # standard Wilson upper bound for 0/10
    p, lo, hi = wilson(5, 10)
    assert abs(lo - 0.2366) < 1e-3 and abs(hi - 0.7634) < 1e-3
    assert all(np.isnan(v) for v in wilson(0, 0))


def test_ffr_counts_and_near_limit_subset():
    yt = np.array([1, 1, 0, 0, 0, 0, 1, 0], bool)
    yp = np.array([1, 0, 1, 0, 0, 1, 1, 0], bool)
    c = ffr_counts(yt, yp)
    assert (c["FP"], c["TN"], c["TP"], c["FN"]) == (2, 3, 2, 1) and abs(c["FFR"] - 0.4) < 1e-12 and c["n_infeasible"] == 5
    mita = np.array([3.1, 2.0, 3.5, 9.0, 3.0, 3.9, 4.0, -1.0])
    r = ffr_report(yt, yp, mita, 3.0, 1.0)
    assert r["n_near"] == 6 and r["near_FP"] == 2 and r["near_TN"] == 1      # near = |mita-3| <= 1 : idx 0,1,2,4,5,6
    assert r["overall_FP"] == 2


def test_bootstrap_interval_contains_the_mean_of_a_simple_statistic():
    x = np.arange(100.0)
    lo, hi = bootstrap(lambda idx: x[idx].mean(), 100, B=2000, seed=3)
    assert lo < 49.5 < hi and hi - lo < 15


def test_por_uses_eq8_at_z0_and_pairs_by_scenario():
    nom = np.array([0.50, 0.52, 0.60, 2.0])
    rob = np.array([0.51, 0.53, 0.58, 0.9])
    out = por_summary(rob, nom, [1, 1, 1, 1], [1, 1, 1, 0], sec_rob_z0=0.51, sec_nom_z0=0.50, alpha=0.9, B=500)
    assert abs(out["PoR_z0"] - 0.02) < 1e-12                          # (0.51-0.50)/0.50
    assert out["n_both_feasible"] == 3 and out["dFeasibleFraction"] == 0.25
    exp = np.mean([(0.51 - 0.50) / 0.50, (0.53 - 0.52) / 0.52, (0.58 - 0.60) / 0.60])
    assert abs(out["PoR_scenario_mean"] - exp) < 1e-12 and out["PoR_scenario_mean_lo95"] <= out["PoR_scenario_mean"] + 0.1


def test_preferred_cycle_rules():
    assert preferred({"a": (0.5, 1.0), "b": (0.6, 1.0)}, 0.95, 5.0)[0] == "a"
    assert preferred({"a": (0.50, 1.0), "b": (0.51, 1.0)}, 0.95, 5.0)[0] == "TIE"            # inside the validation uncertainty
    assert preferred({"a": (0.5, 0.80), "b": (0.6, 1.0)}, 0.95, 5.0)[0] == "b"                # a fails the chance constraint
    assert preferred({"a": (0.5, 0.80)}, 0.95, 5.0)[0] == "NONE"


def test_reversal_flags_only_real_preference_changes():
    rng = np.random.default_rng(0)
    rows = []
    for i in range(32):
        n2, c2 = rng.random() * 10, 2 + rng.random() * 8
        for cyc, nom, rob in (("a", 0.50, 0.60), ("b", 0.60, 0.50)):
            rows.append(dict(scen=i, N2_pct=n2, C2plus_pct=c2, cycle=cyc, design="nominal", sec=nom, feasible=True))
            rows.append(dict(scen=i, N2_pct=n2, C2plus_pct=c2, cycle=cyc, design="robust", sec=rob, feasible=True))
    df = pd.DataFrame(rows)
    cells = assign_cells(df.drop_duplicates("scen")[["scen", "N2_pct", "C2plus_pct"]], 2, 2)[["scen", "cell_x", "cell_y", "cell"]]
    t = reversal_table(df.merge(cells, on="scen"), 0.95, 5.0)
    assert len(t) == 4 and t.reversal.all() and (t.preferred_nominal == "a").all() and (t.preferred_robust == "b").all()


def test_ga_is_deterministic_resumable_and_respects_feasibility_rules():
    lo, hi = np.zeros(3), np.ones(3)
    target = np.array([0.3, 0.6, 0.2])

    def ev(X):
        F = ((X - target) ** 2).sum(1)
        CV = np.maximum(0.0, 0.25 - X[:, 0])         # constraint x0 >= 0.25
        return F, CV

    def run(n_gen, st=None):
        st = st or ga.init_state([[0.9, 0.9, 0.9]], lo, hi, 10, seed=4)
        for _ in range(n_gen):
            st = ga.advance(st, ev)
        return st
    full = run(8)
    half = run(4)
    resumed = ga.GAState.from_json(half.to_json())
    for _ in range(4):
        resumed = ga.advance(resumed, ev)
    assert np.allclose(full.X, resumed.X) and np.allclose(full.F, resumed.F) and full.gen == resumed.gen == 7        # generation 0 is the initial population
    i = ga.best(full)
    assert full.CV[i] <= 0 and full.F[i] < 0.2
    assert full.history[-1]["best_feasible_F"] <= full.history[0]["best_feasible_F"]
    assert ga.better(1.0, 0.0, 0.1, 0.5) and not ga.better(0.1, 0.5, 1.0, 0.0) and ga.better(5.0, 0.1, 0.1, 0.2)
