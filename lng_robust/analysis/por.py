"""Price of robustness (manuscript Eq. 8, unchanged), CVaR change and feasible-fraction change, with bootstrap 95 % intervals.

PoR(z0) = (SEC(x_rob, z0) - SEC(x_nom, z0)) / SEC(x_nom, z0), operation re-optimised at z0 for each design. It is one number.
The bootstrap interval over scenarios is therefore reported for the scenario-mean relative difference (paired by scenario, over
scenarios feasible for both designs), for the change in CVaR and for the change in feasible fraction. Which of these the manuscript
wants beside Eq. 8 is an author decision; all are written with their names."""
from __future__ import annotations

import numpy as np

from lng_robust.opt.common import cvar, price_of_robustness


def bootstrap(fn, n: int, B: int = 5000, seed: int = 1, alpha: float = 0.05):
    rng = np.random.default_rng(seed)
    vals = np.empty(B)
    for b in range(B):
        idx = rng.integers(0, n, n)
        vals[b] = fn(idx)
    vals = vals[np.isfinite(vals)]
    if len(vals) == 0:
        return float("nan"), float("nan")
    return float(np.quantile(vals, alpha / 2)), float(np.quantile(vals, 1 - alpha / 2))


def por_summary(sec_rob, sec_nom, feas_rob, feas_nom, sec_rob_z0, sec_nom_z0, alpha: float, B: int = 5000, seed: int = 1):
    """sec_* are per-scenario SEC with the infeasibility penalty already applied; feas_* boolean masks."""
    sr, sn = np.asarray(sec_rob, float), np.asarray(sec_nom, float)
    fr, fn = np.asarray(feas_rob, bool), np.asarray(feas_nom, bool)
    S = len(sr)
    both = fr & fn

    def mean_rel(idx):
        m = both[idx]
        if m.sum() == 0:
            return float("nan")
        return float(np.mean((sr[idx][m] - sn[idx][m]) / sn[idx][m]))

    def dcvar(idx):
        return (cvar(sr[idx], alpha) - cvar(sn[idx], alpha)) / cvar(sn[idx], alpha)

    def dff(idx):
        return float(fr[idx].mean() - fn[idx].mean())

    out = dict(PoR_z0=price_of_robustness(sec_rob_z0, sec_nom_z0), n_scenarios=S, n_both_feasible=int(both.sum()),
               PoR_scenario_mean=mean_rel(np.arange(S)), dCVaR_rel=dcvar(np.arange(S)), dFeasibleFraction=dff(np.arange(S)))
    for name, fn_ in (("PoR_scenario_mean", mean_rel), ("dCVaR_rel", dcvar), ("dFeasibleFraction", dff)):
        lo, hi = bootstrap(fn_, S, B, seed)
        out[f"{name}_lo95"], out[f"{name}_hi95"] = lo, hi
    out["CVaR_rob"], out["CVaR_nom"] = cvar(sr, alpha), cvar(sn, alpha)
    out["worst_rob"], out["worst_nom"] = float(sr.max()), float(sn.max())
    out["feasible_fraction_rob"], out["feasible_fraction_nom"] = float(fr.mean()), float(fn.mean())
    return out
