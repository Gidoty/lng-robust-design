"""CVaR convergence with the number of scenarios S = 25, 50, 100 on one cycle (decision D5 asks for this check).

The scenario sets are nested (the synthetic draws of each anchor use a fixed per-anchor seed and are taken in order), so one evaluation of
S = 100 gives S = 25 and S = 50 as subsets. Two fixed designs are used so the check does not depend on a robust optimum: the nominal
design, and the same design with 25 % more conductance and rated flow (more scenarios feasible). Rule from the task: use the smallest S whose
CVaR is within 1 % of S = 100 for both designs; otherwise keep S = 50. D5 fixes S = 50 for the main run; this file records the evidence.
Writes runs/cvar_convergence.csv and runs/cvar_convergence_verdict.json."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from lng_robust.config import RUNS_DIR, load_basis
from lng_robust.opt.common import cvar
from lng_robust.opt.robust import stage1_vec_of_design, x1_from_vec
from lng_robust.study.common import M_LNG, nominal_design_dict, scenario_set
from lng_robust.study.config import Ctx, get_preset
from lng_robust.study.store import EvalSink
from lng_robust.study import units


def run(cycle="n2_dual", out_dir=RUNS_DIR, workers=4, nominal=dict(pop=40, gen=20), kw=None, alpha_list=(0.9,)):
    basis = load_basis()
    with tempfile.TemporaryDirectory() as tmp:
        p = get_preset("full")
        p["nominal"] = nominal
        p["S"] = 100
        ctx = Ctx("nominal", cycle, None, None, "full", p, Path(tmp), workers=workers, seed=basis.random_seed)
        nom = units.unit_nominal(ctx)
        if not nom.get("feasible_found"):
            raise SystemExit("no feasible nominal design; cannot run the convergence check")
        scen100, nom_feed, meta = scenario_set(ctx, basis, "main", 100)
        ids = {S: {f.id for f in scenario_set(ctx, basis, "main", S)[0]} for S in (25, 50, 100)}
        assert ids[25] <= ids[50] <= ids[100], "scenario sets are not nested"
        x_nom = x1_from_vec(cycle, stage1_vec_of_design(cycle, nominal_design_dict(nom), M_LNG), M_LNG)
        x_marg = dict(x_nom)
        x_marg["ua_installed_kw_per_K"] = x_nom["ua_installed_kw_per_K"] * 1.25
        x_marg["n_ref_rated_mol_s"] = x_nom["n_ref_rated_mol_s"] * 1.25
        sink = EvalSink(Path(tmp) / "evals", "evals")
        kw = kw or dict(method="hybrid", max_evals=40, n_restarts=0)
        res = units.eval_designs_on_set(ctx, cycle, {"nominal": x_nom, "nominal_ua_x1.25": x_marg}, scen100, basis, nom, kw, "cvar_convergence", sink)
        sink.close()
    rows = []
    rng = np.random.default_rng(1)
    for name, de in res.items():
        idx = {sid: i for i, sid in enumerate(de.ids)}
        c100 = {a: cvar(de.sec, a) for a in alpha_list}
        for S in (25, 50, 100):
            sub = [idx[s] for s in sorted(ids[S])]
            for a in alpha_list:
                c = cvar(de.sec[sub], a)
                rows.append(dict(cycle=cycle, design=name, S=S, alpha=a, CVaR=c, rel_diff_vs_S100_pct=100 * (c - c100[a]) / c100[a],
                                 feasible_fraction=float(de.feasible[sub].mean()), kind="nested_subset"))
        for S in (25, 50):                       # spread over random subsets of the 100 scenarios (does the particular subset matter?)
            vals = [cvar(de.sec[rng.choice(100, S, replace=False)], 0.9) for _ in range(200)]
            rows.append(dict(cycle=cycle, design=name, S=S, alpha=0.9, CVaR=float(np.mean(vals)), rel_diff_vs_S100_pct=100 * (np.mean(vals) - c100[0.9]) / c100[0.9],
                             feasible_fraction=float("nan"), kind=f"random_subsets_mean (sd {np.std(vals):.4f}, p5 {np.percentile(vals, 5):.4f}, p95 {np.percentile(vals, 95):.4f})"))
    df = pd.DataFrame(rows)
    df.to_csv(Path(out_dir) / "cvar_convergence.csv", index=False)
    nested = df[(df.kind == "nested_subset") & (df.alpha == 0.9)]
    ok = {S: bool((nested[nested.S == S].rel_diff_vs_S100_pct.abs() <= 1.0).all()) for S in (25, 50)}
    chosen = 25 if ok[25] else (50 if ok[50] else 50)
    verdict = dict(cycle=cycle, within_1pct_of_S100=ok, smallest_S_meeting_rule=(25 if ok[25] else 50 if ok[50] else None), S_used_in_study=50,
                   note=("D5 (decided by the authors) fixes S = 50 for the main run. The rule 'use the smallest S within 1 % of S = 100, else keep S = 50' "
                         + ("selects S = 25 on this evidence, which would change D5; S = 50 is kept and the question is passed to the authors." if ok[25] else "keeps S = 50.")),
                   inner_solver=kw)
    (Path(out_dir) / "cvar_convergence_verdict.json").write_text(json.dumps(verdict, indent=2))
    return df, verdict


if __name__ == "__main__":
    d, v = run(sys.argv[1] if len(sys.argv) > 1 else "n2_dual")
    print(d.round(4).to_string())
    print(json.dumps(v, indent=2))
