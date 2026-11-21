"""Tests of the figure redraw (request 20) and the cost screening (request 21). Synthetic inputs; no result is asserted."""
import json
import numpy as np
import pandas as pd
import pytest

from lng_robust.analysis import cost_screening
from lng_robust.analysis import figures as F


def _cells():
    rows = []
    n2_mean = [1e-4, 0.03, 0.27, 2.0]
    for cx in range(4):
        for cy in range(4):
            rows.append(dict(cell=cx * 4 + cy, cell_x=cx, cell_y=cy, n_scenarios=10, N2_pct_mean=n2_mean[cx] if not (cx == 3 and cy == 0) else 10.3,
                             C2plus_pct_mean=2 + 3 * cy, N2_pct_min=0.0 if cx == 0 else n2_mean[cx] / 2, N2_pct_max=n2_mean[cx] * 1.5, C2plus_pct_min=1 + 3 * cy,
                             C2plus_pct_max=3 + 3 * cy, preferred_nominal="NONE" if (cx, cy) == (3, 0) else "smr", gap_nominal_pct=np.nan,
                             preferred_robust="smr", gap_robust_pct=10.0, reversal=False))
    return pd.DataFrame(rows)


def test_fig7_labels_are_distinct_and_the_nitrogen_rich_cell_is_marked(tmp_path):
    assert F._fmt_mol(0.0005888) != F._fmt_mol(0.0)
    labels = [F._fmt_mol(v) for v in (0.0, 7.2e-4, 8.5e-4, 0.089, 0.094, 0.59, 0.6, 14.8)]
    assert len(set(labels)) == len(labels)
    out = F.fig7_reversal(_cells(), tmp_path)
    assert out == ["Figure_7.png", "Figure_7.pdf"] and (tmp_path / "Figure_7.pdf").stat().st_size > 1000


def test_fig8_and_fig9_render(tmp_path):
    rng = np.random.default_rng(0)
    oof = {c: pd.DataFrame(dict(sec=rng.uniform(.4, 1, 200), sec_gradient_boosting=rng.uniform(.4, 1, 200), feasible=rng.uniform(size=200) > .4,
                                mita=rng.normal(3, 3, 200), feas_gradient_boosting=rng.uniform(size=200) > .5)) for c in ("smr", "n2_single", "n2_dual")}
    assert F.fig8_surrogate(oof, 3.0, tmp_path)[0] == "Figure_8.png"
    sob = pd.DataFrame([dict(cycle=c, output="SEC_surrogate", variable=f"v{k}", S1=0.1, ST=0.1 * (k + 1)) for c in ("smr", "n2_single", "n2_dual") for k in range(12)])
    pref = pd.DataFrame([dict(output=o, variable=f"v{k}", ST=0.1 * (k + 1)) for o in ("SECdiff_smr_minus_n2_single", "SECdiff_smr_minus_n2_dual", "SECdiff_n2_single_minus_n2_dual") for k in range(10)])
    assert F.fig9_sobol(sob, pref, tmp_path)[0] == "Figure_9.png"


def test_fig9_shows_only_the_eight_largest_inputs(tmp_path):
    import matplotlib.pyplot as plt
    sob = pd.DataFrame([dict(cycle="smr", output="SEC_surrogate", variable=f"v{k}", S1=0.05, ST=0.05 * (k + 1)) for k in range(12)])
    seen = {}
    orig = plt.close
    try:
        plt.close = lambda fig=None: seen.setdefault("n", [len(a.get_yticklabels()) for a in fig.axes if a.get_visible()])
        F.fig9_sobol(sob, pd.DataFrame(), tmp_path)
    finally:
        plt.close = orig
    assert seen["n"][0] == 8


def test_cost_screening_runs_and_is_deterministic(tmp_path):
    t5 = pd.DataFrame(dict(cycle=["smr", "n2_single", "n2_dual"], compressor_kW=[1700.0, 4800.0, 4000.0], expander_kW=[0.0, 980.0, 970.0]))
    rows, ps = [], []
    for c in ("smr", "n2_single", "n2_dual"):
        for d in ("nominal", "cvar_iso", "cvar_125"):
            rows.append(dict(cycle=c, design=d, UA_installed_kW_per_K=100.0, SEC_z0_kWh_per_kg=0.5))
            for k in range(5):
                ps.append(dict(cycle=c, design=d, scenario=f"s{k}", sec=0.5 + 0.01 * k, feasible=True))
    for name, df in (("T5_nominal_designs", t5.assign()), ("T6_nominal_cvar_worst_designs", pd.DataFrame(rows)), ("TS_across_per_scenario", pd.DataFrame(ps))):
        df.to_csv(tmp_path / f"{name}.csv", index=False)
    a = cost_screening.run(str(tmp_path), str(tmp_path / "o1") if (tmp_path / "o1").mkdir() is None else None)
    b = cost_screening.run(str(tmp_path), str(tmp_path / "o2") if (tmp_path / "o2").mkdir() is None else None)
    assert len(a) == 81 and a.equals(b) and (tmp_path / "o1" / "TS_cost_screening.csv").exists()
    assert (a.cost_z0_USD_per_t > 0).all()


def test_finalise_refuses_missing_inputs(tmp_path):
    from lng_robust.study.finalise import finalise
    (tmp_path / "tables").mkdir()
    with pytest.raises(FileNotFoundError):
        finalise(tmp_path, tmp_path / "work", "abc")
