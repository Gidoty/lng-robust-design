"""Efficiency comparison of the second-stage solvers on 10 scenarios per cycle (equipment fixed).

Equipment x1 is built from a hand-set design (analysis/golden.py start) with 15 % margin on its required UA and flow.
Scenarios: the first 10 of the main envelope (6 anchors, then 4 synthetic). Compared: penalised Nelder-Mead (old, budgets 16 and 40)
against SLSQP (warm start from the nearest solved scenario, 0 and 3 random restarts). Rigorous evaluations and wall time are counted.
Output: runs/inner_solver_comparison.csv. This is a method-efficiency test; the SEC values are not study results."""
from __future__ import annotations

import sys
import time

import numpy as np
import pandas as pd
from concurrent.futures import ProcessPoolExecutor

from lng_robust.analysis.golden import M_LNG, _feasible_start
from lng_robust.config import RUNS_DIR, load_basis
from lng_robust.cycles import solve
from lng_robust.doe.envelope import build_envelope, envelope_definitions
from lng_robust.opt.inner import solve_hybrid, solve_nelder_mead, solve_slsqp
from lng_robust.opt.nominal import nominal_var_names
from lng_robust.opt.space import STAGE2, bounds

N_SCEN = 10


def equipment(cycle, feed, basis):
    base = _feasible_start(cycle)
    r = solve(cycle, feed, basis.feed_T, basis.feed_P, M_LNG, dict(base), basis)
    x1 = {}
    if cycle == "smr":
        x1["ref"] = dict(base["ref"])
    x1["ua_installed_kw_per_K"] = 1.15 * r.ua * 1e0 if r.ua == r.ua else 1e9
    x1["n_ref_rated_mol_s"] = 1.15 * r.n_ref
    return x1, base, r


def _job(args):
    method, cycle, feed, x1, y0, basis, kw = args
    lo, hi = bounds(cycle, STAGE2[cycle], basis)
    t = time.perf_counter()
    if method == "nm":
        out = solve_nelder_mead(cycle, feed, M_LNG, x1, y0, lo, hi, basis, maxfev=kw["maxfev"])
    elif method == "hybrid":
        out = solve_hybrid(cycle, feed, M_LNG, x1, y0, lo, hi, basis, max_evals=kw["max_evals"], n_restarts=kw["n_restarts"], seed=1,
                           box=kw.get("box", 0.20), feas_max=kw.get("feas_max", 24), maxiter=kw.get("maxiter", 12))
    else:
        out = solve_slsqp(cycle, feed, M_LNG, x1, y0, lo, hi, basis, max_evals=kw["max_evals"], n_restarts=kw["n_restarts"], seed=1)
    wall = time.perf_counter() - t
    return out.best_res.sec if out.best_res is not None else float("nan"), out.n_evals, wall, (out.best_y if out.best_y is not None else None)


def run(cycles=("n2_dual", "n2_single", "smr"), out=RUNS_DIR / "inner_solver_comparison.csv", workers=4, cfgs=None):
    basis = load_basis()
    anchors = envelope_definitions(basis)["main"]
    scen, nom, meta = build_envelope("main", anchors, basis, 50, basis.random_seed)
    scen = scen[:N_SCEN]
    rows = []
    with ProcessPoolExecutor(workers) as pool:
        for cycle in cycles:
            x1, base, r0 = equipment(cycle, nom.treated, basis)
            y0 = np.array([base[n] for n in STAGE2[cycle]])
            cfgs_ = cfgs or [("nm16", ("nm", dict(maxfev=16))), ("nm40", ("nm", dict(maxfev=40))),
                             ("slsqp_nores", ("slsqp", dict(max_evals=40, n_restarts=0))),
                             ("slsqp_r3", ("slsqp", dict(max_evals=80, n_restarts=3)))]
            for label, (m, kw) in cfgs_:
                if m in ("slsqp", "hybrid"):
                    # wave 1: anchors from the nominal y0; wave 2: synthetic scenarios warm-started from the parent anchor's solution
                    first = [f for f in scen if not f.synthetic]
                    res1 = list(pool.map(_job, [(m, cycle, f.treated, x1, y0, basis, kw) for f in first]))
                    ybest = {f.id: (r[3] if r[3] is not None else y0) for f, r in zip(first, res1)}
                    rest = [f for f in scen if f.synthetic]
                    res2 = list(pool.map(_job, [(m, cycle, f.treated, x1, ybest.get(f.parent_id, y0), basis, kw) for f in rest]))
                    res = res1 + res2
                    order = first + rest
                else:
                    res = list(pool.map(_job, [(m, cycle, f.treated, x1, y0, basis, kw) for f in scen]))
                    order = scen
                for f, (sec, n, wall, _) in zip(order, res):
                    rows.append(dict(cycle=cycle, method=label, scenario=f.id, synthetic=f.synthetic, sec_kwh_per_kg=sec,
                                     rigorous_evals=n, wall_s=wall, found_feasible=sec == sec))
    df = pd.DataFrame(rows)
    df.to_csv(out, index=False)
    return df


def summarise(df):
    # compare on scenarios where the old method (nm40) found a feasible point and where both found one
    piv = df.pivot_table(index=["cycle", "scenario"], columns="method", values="sec_kwh_per_kg")
    ev = df.pivot_table(index=["cycle", "scenario"], columns="method", values="rigorous_evals")
    wl = df.pivot_table(index=["cycle", "scenario"], columns="method", values="wall_s")
    out = []
    for cyc in df.cycle.unique():
        p, e, w = piv.loc[cyc], ev.loc[cyc], wl.loc[cyc]
        for m in [c for c in p.columns if not c.startswith("nm")]:
            for base in ("nm16", "nm40"):
                both = p[[m, base]].dropna()
                out.append(dict(cycle=cyc, method=m, baseline=base, n_feasible_method=int(p[m].notna().sum()),
                                n_feasible_baseline=int(p[base].notna().sum()), n_both=len(both),
                                n_equal_or_lower=int((both[m] <= both[base] * (1 + 1e-6)).sum()),
                                evals_method=int(e[m].sum()), evals_baseline=int(e[base].sum()),
                                wall_method_s=float(w[m].sum()), wall_baseline_s=float(w[base].sum()),
                                mean_sec_diff_pct=float(100 * ((both[m] - both[base]) / both[base]).mean()) if len(both) else float("nan")))
    return pd.DataFrame(out)


if __name__ == "__main__":
    d = run()
    s = summarise(d)
    s.to_csv(RUNS_DIR / "inner_solver_summary.csv", index=False)
    print(s.to_string())
