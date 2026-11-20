"""Fixed evaluation cases used to prove that speed-ups do not change results.

`make_cases()` is deterministic: 20 cases (7 SMR, 7 single N2, 6 dual N2) built from fixed seeds over the design-basis bounds,
on three different treated feeds. Reference outputs were produced by the code BEFORE any optimisation and are stored in
tests/data/golden_eval.csv; the test suite compares every numeric output at 1e-9 relative tolerance."""
from __future__ import annotations

import numpy as np

from lng_robust.config import load_basis
from lng_robust.doe.envelope import envelope_definitions
from lng_robust.opt.common import nominal_var_names
from lng_robust.opt.space import bounds, clean, decode

CASE_COUNTS = {"smr": 7, "n2_single": 7, "n2_dual": 6}
M_LNG = 100.0 * 1000.0 / 86400.0
NUMERIC = ["sec", "exergy_eff", "mita", "ua", "w_comp_kw", "w_exp_kw", "m_feed", "n_feed", "n_ref", "end_flash_fraction",
           "lng_mass_frac", "violation", "tear_residual", "balance_error", "exergy_closure_error", "lng_N2_mol_pct"]


def _feasible_start(cycle):
    """A hand-set design near a feasible region so the case list contains both feasible and infeasible points."""
    return {
        "smr": dict(P_high_bar=22.0, P_low_bar=4.844, flow_ratio=4.145, T_lng_C=-144.0,     # hand-set design of analysis/mshe_convergence_smr.py
                    ref={"N2": 0.078, "C1": 0.262, "C2": 0.414, "C3": 0.016, "nC4": 0.178, "iC5": 0.053}),
        "n2_single": dict(P_high_bar=70.21188348676853, P_low_bar=9.800692042801586, flow_ratio=8.772728960622349,
                          T_exp_in_C=-69.10238140572024, T_lng_C=-143.0419683390787),     # found by a seeded random search (feasible on A4)
        "n2_dual": dict(P_high_bar=60.0, P_low_bar=10.0, flow_ratio=8.0, T_exp_in_warm_C=-30.0, T_exp_in_cold_C=-100.0,
                        split=0.5, T_lng_C=-150.0),
    }[cycle]


def make_cases(basis=None):
    basis = basis or load_basis()
    feeds = envelope_definitions(basis)["main"]
    cases = []
    for ci, cycle in enumerate(CASE_COUNTS):
        names = nominal_var_names(cycle)
        lo, hi = bounds(cycle, names, basis)
        rng = np.random.default_rng(1000 + ci)
        for k in range(CASE_COUNTS[cycle]):
            feed = feeds[(k + ci) % len(feeds)]
            if k == 0:
                x = _feasible_start(cycle)
            else:
                base = _feasible_start(cycle)
                v = lo + rng.random(len(names)) * (hi - lo)
                x = clean(decode(cycle, names, v, M_LNG))
                if k % 2 == 1:           # perturb the hand-set design for half the cases (near-feasible points)
                    for n in names:
                        if n.startswith("w_"):
                            continue
                        x[n] = base[n] * (1.0 + 0.15 * (rng.random() - 0.5))
                    if cycle == "smr":
                        x["ref"] = dict(base["ref"])
            cases.append(dict(case=f"{cycle}-{k}", cycle=cycle, feed_id=feed.id, feed=feed.treated, x=x))
    return cases


def evaluate(cases, basis=None, solve_fn=None):
    from lng_robust.cycles import solve
    basis = basis or load_basis()
    solve_fn = solve_fn or solve
    rows = []
    for c in cases:
        r = solve_fn(c["cycle"], c["feed"], basis.feed_T, basis.feed_P, M_LNG, c["x"], basis)
        d = r.as_row()
        rows.append(dict(case=c["case"], feed_id=c["feed_id"], feasible=bool(r.feasible), failure_code=r.failure_code,
                         **{k: d.get(k, float("nan")) for k in NUMERIC}))
    return rows
